import io
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, date
from zoneinfo import ZoneInfo
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.services.firestore_service import FirestoreService
from app.routers.attendance import is_checkin_late
from app.services.attendance_service import get_attendance_today

IST = ZoneInfo("Asia/Kolkata")


def make_test_jpeg(width: int = 60, height: int = 60, color=(10, 50, 40)) -> bytes:
    """Helper to generate valid JPEG image bytes."""
    buf = io.BytesIO()
    img = Image.new("RGB", (width, height), color=color)
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestAttendanceStatusAndLateReason(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        # Login employee
        login_res = cls.client.post("/api/auth/login", json={"email": "employee@arshith.com", "password": "Employee@123"})
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        cls.token = login_res.json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}
        user = login_res.json().get("user", {})
        cls.emp_id = user.get("employee_id") or user.get("employeeId") or "EMP-1001"
        cls.emp_uid = str(user.get("uid") or user.get("id") or cls.emp_id)
        cls.today = get_attendance_today()
        cls.today_iso = cls.today.isoformat()
        cls.rec_id = f"{cls.emp_id}_{cls.today_iso}"

    def clean_records(self):
        from app.db.session import SessionLocal
        from app.models.attendance import Attendance
        FirestoreService.delete("attendance", self.rec_id)
        FirestoreService.delete("attendances", self.rec_id)
        if hasattr(self, "emp_uid") and self.emp_uid:
            FirestoreService.delete_subdocument("attendance", self.emp_uid, "records", self.today_iso)
        FirestoreService.delete_subdocument("attendance", self.emp_id, "records", self.today_iso)
        try:
            with SessionLocal() as db:
                db.query(Attendance).filter(
                    Attendance.employee_id == self.emp_id,
                    Attendance.date == self.today,
                ).delete()
                db.commit()
        except Exception:
            pass

    def setUp(self):
        self.clean_records()

    def tearDown(self):
        self.clean_records()

    def test_scenario_1_and_2_cutoff_times(self):
        """
        Verify cutoff time validation:
        - 9:20 AM IST -> Not late (is_checkin_late is False)
        - 9:30 AM IST (exact cutoff) -> Not late (is_checkin_late is False)
        - 9:31 AM IST -> Late (is_checkin_late is True)
        """
        dt_920 = datetime(2026, 10, 27, 9, 20, 0, tzinfo=IST)
        self.assertFalse(is_checkin_late(dt_920))

        dt_930 = datetime(2026, 10, 27, 9, 30, 0, tzinfo=IST)
        self.assertFalse(is_checkin_late(dt_930))

        dt_931 = datetime(2026, 10, 27, 9, 31, 0, tzinfo=IST)
        self.assertTrue(is_checkin_late(dt_931))

    def test_scenario_1_on_time_checkin_succeeds_without_late_reason(self):
        """
        Scenario 1: Employee checking in on time (<= 9:30 AM IST) does not require a late reason,
        attendance is created, and isLate is False.
        """
        dt_on_time = datetime(2026, 10, 27, 9, 15, 0, tzinfo=IST)
        photo_bytes = make_test_jpeg()

        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.generate_signed_url.return_value = "https://storage.googleapis.com/test-bucket/attendancePhotos/UID/2026-10-27.jpg"
        mock_bucket.blob.return_value = mock_blob

        with patch("app.routers.attendance.get_attendance_now", return_value=dt_on_time), \
             patch("app.core.firebase.is_firebase_live", return_value=True), \
             patch("app.core.firebase.get_storage_bucket", return_value=mock_bucket):

            res = self.client.post(
                "/api/attendance/check-in",
                headers=self.headers,
                files={"photo": ("selfie.jpg", photo_bytes, "image/jpeg")},
                data={"workMode": "WFH"},  # WFH to test without physical geofence dependency
            )

            self.assertEqual(res.status_code, 200, res.text)
            data = res.json()
            self.assertTrue(data["success"])
            self.assertFalse(data["isLate"])
            self.assertIsNone(data["lateReason"])
            self.assertEqual(data["lateReasonStatus"], "NOT_REQUIRED")

            # Verify saved record in Firestore
            saved = FirestoreService.get_by_id("attendance", self.rec_id)
            self.assertIsNotNone(saved)
            self.assertFalse(saved.get("is_late"))
            self.assertIsNone(saved.get("late_reason"))
            self.assertEqual(saved.get("late_reason_status"), "NOT_REQUIRED")

    def test_scenario_3_and_4_late_checkin_rejects_missing_or_whitespace_reason(self):
        """
        Scenario 3 & 4: Employee checking in after 9:30 AM IST without a late reason or with
        whitespace-only reason is rejected with 400 Bad Request (LATE_REASON_REQUIRED).
        No attendance record is created in the database.
        """
        dt_late = datetime(2026, 10, 27, 10, 15, 0, tzinfo=IST)
        photo_bytes = make_test_jpeg()

        with patch("app.routers.attendance.get_attendance_now", return_value=dt_late):
            # A. Completely missing lateReason
            res_missing = self.client.post(
                "/api/attendance/check-in",
                headers=self.headers,
                files={"photo": ("selfie.jpg", photo_bytes, "image/jpeg")},
                data={"workMode": "WFH"},
            )
            self.assertEqual(res_missing.status_code, 400)
            self.assertIn("late check-in reason is mandatory", res_missing.text)
            self.assertIn("LATE_REASON_REQUIRED", res_missing.text)

            # Check that database has NO attendance record
            saved = FirestoreService.get_by_id("attendance", self.rec_id)
            self.assertIsNone(saved, "No record should be created when late reason is missing")

            # B. Whitespace-only lateReason
            res_whitespace = self.client.post(
                "/api/attendance/check-in",
                headers=self.headers,
                files={"photo": ("selfie.jpg", photo_bytes, "image/jpeg")},
                data={"workMode": "WFH", "lateReason": "    \t\n   "},
            )
            self.assertEqual(res_whitespace.status_code, 400)
            self.assertIn("late check-in reason is mandatory", res_whitespace.text)

            saved = FirestoreService.get_by_id("attendance", self.rec_id)
            self.assertIsNone(saved, "No record should be created when late reason is only whitespace")

    def test_scenario_6_7_8_late_checkin_succeeds_with_reason_and_today_status(self):
        """
        Scenario 6, 7 & 8: Employee checking in after 9:30 AM IST with a valid late reason:
        - Check-in succeeds.
        - isLate is True, lateReason is saved as 'Traffic delay on highway', lateReasonStatus is 'SUBMITTED'.
        - Today-status API reflects isCheckedIn=True, isLate=True, lateReason='Traffic delay on highway'.
        """
        dt_late = datetime(2026, 10, 27, 11, 0, 0, tzinfo=IST)
        photo_bytes = make_test_jpeg()

        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.generate_signed_url.return_value = "https://storage.googleapis.com/test-bucket/attendancePhotos/UID/2026-10-27.jpg"
        mock_bucket.blob.return_value = mock_blob

        with patch("app.routers.attendance.get_attendance_now", return_value=dt_late), \
             patch("app.core.firebase.is_firebase_live", return_value=True), \
             patch("app.core.firebase.get_storage_bucket", return_value=mock_bucket):

            # Check in with valid reason
            res = self.client.post(
                "/api/attendance/check-in",
                headers=self.headers,
                files={"photo": ("selfie.jpg", photo_bytes, "image/jpeg")},
                data={"workMode": "WFH", "lateReason": "Traffic delay on highway"},
            )

            self.assertEqual(res.status_code, 200, res.text)
            data = res.json()
            self.assertTrue(data["success"])
            self.assertTrue(data["isLate"])
            self.assertEqual(data["lateReason"], "Traffic delay on highway")
            self.assertEqual(data["lateReasonStatus"], "SUBMITTED")
            self.assertIsNotNone(data["lateReasonSubmittedAt"])

            # Verify saved record in Firestore
            saved = FirestoreService.get_by_id("attendance", self.rec_id)
            self.assertIsNotNone(saved)
            self.assertTrue(saved.get("is_late"))
            self.assertEqual(saved.get("late_reason"), "Traffic delay on highway")
            self.assertEqual(saved.get("late_reason_status"), "SUBMITTED")

            # Check today-status endpoint (Dashboard refresh)
            today_res = self.client.get("/api/attendance/today-status", headers=self.headers)
            self.assertEqual(today_res.status_code, 200)
            today_data = today_res.json()
            self.assertTrue(today_data["isCheckedIn"])
            self.assertFalse(today_data["isCompleted"])
            self.assertTrue(today_data["isLate"])
            self.assertEqual(today_data["lateReason"], "Traffic delay on highway")
            self.assertEqual(today_data["lateReasonStatus"], "SUBMITTED")

    def test_scenario_9_checkout_changes_status_to_completed(self):
        """
        Scenario 9: After checkout, isCheckedIn becomes False and isCompleted becomes True.
        """
        dt_on_time = datetime(2026, 10, 27, 9, 0, 0, tzinfo=IST)
        photo_bytes = make_test_jpeg()

        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.generate_signed_url.return_value = "https://storage.googleapis.com/test-bucket/attendancePhotos/UID/2026-10-27.jpg"
        mock_bucket.blob.return_value = mock_blob

        with patch("app.routers.attendance.get_attendance_now", return_value=dt_on_time), \
             patch("app.core.firebase.is_firebase_live", return_value=True), \
             patch("app.core.firebase.get_storage_bucket", return_value=mock_bucket):

            # 1. Check in
            checkin_res = self.client.post(
                "/api/attendance/check-in",
                headers=self.headers,
                files={"photo": ("selfie.jpg", photo_bytes, "image/jpeg")},
                data={"workMode": "WFH"},
            )
            self.assertEqual(checkin_res.status_code, 200)

            # 2. Check out
            checkout_res = self.client.post(
                "/api/attendance/check-out",
                headers=self.headers,
                json={"employeeId": self.emp_id},
            )
            self.assertEqual(checkout_res.status_code, 200, checkout_res.text)

            # 3. Check today status
            today_res = self.client.get("/api/attendance/today-status", headers=self.headers)
            self.assertEqual(today_res.status_code, 200)
            today_data = today_res.json()
            self.assertFalse(today_data["isCheckedIn"], "isCheckedIn must be False after checkout")
            self.assertTrue(today_data["isCompleted"], "isCompleted must be True after checkout")
            self.assertEqual(today_data["status"], "Completed")


if __name__ == "__main__":
    unittest.main()
