import io
import unittest
from unittest.mock import MagicMock, patch
from datetime import date
from PIL import Image

from app.services.attendance_service import upload_to_firebase_storage


def make_test_jpeg(width: int = 60, height: int = 60, color=(10, 50, 40)) -> bytes:
    """Helper to generate valid JPEG image bytes."""
    buf = io.BytesIO()
    img = Image.new("RGB", (width, height), color=color)
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestSingleSelfieUpload(unittest.TestCase):
    def test_upload_to_firebase_storage_single_upload_and_canonical_path(self):
        """
        Verify upload_to_firebase_storage:
        1. Uploads to exactly ONE canonical path: attendancePhotos/{uid}/{date}.jpg
        2. Calls blob.upload_from_string exactly ONCE.
        3. Never uploads duplicate files (no AFI-9099_2026-10-27.jpg duplicate).
        4. Returns the single canonical path and signed photo URL.
        """
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.generate_signed_url.return_value = "https://storage.googleapis.com/test-bucket/attendancePhotos/T73w1A4VK/2026-10-27.jpg"
        mock_bucket.blob.return_value = mock_blob

        photo_bytes = make_test_jpeg()
        emp_uid = "T73w1A4VK"
        emp_id = "AFI-9099"
        record_id = "AFI-9099_2026-10-27"
        date_str = "2026-10-27"

        with patch("app.core.firebase.is_firebase_live", return_value=True), \
             patch("app.core.firebase.get_storage_bucket", return_value=mock_bucket):

            storage_path, photo_url = upload_to_firebase_storage(
                photo_bytes=photo_bytes,
                mime_type="image/jpeg",
                employee_id=emp_id,
                attendance_record_id=record_id,
                photo_type="check-in",
                employee_uid=emp_uid,
                attendance_date=date_str,
            )

            # 1. Bucket.blob must be called EXACTLY ONCE
            self.assertEqual(mock_bucket.blob.call_count, 1, "Bucket blob should only be requested once!")
            called_path = mock_bucket.blob.call_args[0][0]
            expected_canonical_path = f"attendancePhotos/{emp_uid}/{date_str}.jpg"
            self.assertEqual(called_path, expected_canonical_path)

            # 2. Upload_from_string must be called EXACTLY ONCE
            self.assertEqual(mock_blob.upload_from_string.call_count, 1, "upload_from_string should only be called once!")
            uploaded_bytes, kwargs = mock_blob.upload_from_string.call_args
            self.assertEqual(uploaded_bytes[0], photo_bytes)
            self.assertEqual(kwargs.get("content_type"), "image/jpeg")

            # 3. Path returned matches canonical path
            self.assertEqual(storage_path, expected_canonical_path)
            self.assertTrue(photo_url.startswith("https://"))

    def test_upload_to_firebase_storage_without_explicit_date(self):
        """
        Verify that even if attendance_date is not passed, date is correctly parsed
        from attendance_record_id and uploaded once to attendancePhotos/{uid}/{date}.jpg.
        """
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.generate_signed_url.return_value = "https://storage.googleapis.com/test-url"
        mock_bucket.blob.return_value = mock_blob

        photo_bytes = make_test_jpeg()
        emp_uid = "UID_TEST_123"
        emp_id = "AFI-9099"
        record_id = "AFI-9099_2026-10-27"

        with patch("app.core.firebase.is_firebase_live", return_value=True), \
             patch("app.core.firebase.get_storage_bucket", return_value=mock_bucket):

            storage_path, photo_url = upload_to_firebase_storage(
                photo_bytes=photo_bytes,
                mime_type="image/jpeg",
                employee_id=emp_id,
                attendance_record_id=record_id,
                photo_type="check-in",
                employee_uid=emp_uid,
                attendance_date=None,  # Not provided
            )

            self.assertEqual(mock_bucket.blob.call_count, 1)
            self.assertEqual(storage_path, f"attendancePhotos/{emp_uid}/2026-10-27.jpg")
            self.assertEqual(mock_blob.upload_from_string.call_count, 1)

    def test_upload_retry_uses_same_canonical_path(self):
        """
        Verify that retrying an upload uses the exact same canonical path and does not create
        new paths or duplicate files.
        """
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.generate_signed_url.return_value = "https://storage.googleapis.com/test-url"
        mock_bucket.blob.return_value = mock_blob

        photo_bytes = make_test_jpeg()
        emp_uid = "T73w1A4VK"
        emp_id = "AFI-9099"
        record_id = "AFI-9099_2026-10-27"
        date_str = "2026-10-27"

        with patch("app.core.firebase.is_firebase_live", return_value=True), \
             patch("app.core.firebase.get_storage_bucket", return_value=mock_bucket):

            path1, url1 = upload_to_firebase_storage(
                photo_bytes=photo_bytes,
                mime_type="image/jpeg",
                employee_id=emp_id,
                attendance_record_id=record_id,
                photo_type="check-in",
                employee_uid=emp_uid,
                attendance_date=date_str,
            )

            path2, url2 = upload_to_firebase_storage(
                photo_bytes=photo_bytes,
                mime_type="image/jpeg",
                employee_id=emp_id,
                attendance_record_id=record_id,
                photo_type="check-in",
                employee_uid=emp_uid,
                attendance_date=date_str,
            )

            # Both attempts must target the identical canonical path
            self.assertEqual(path1, path2)
            self.assertEqual(path1, "attendancePhotos/T73w1A4VK/2026-10-27.jpg")
            # Each call uploads once
            self.assertEqual(mock_blob.upload_from_string.call_count, 2)

    def test_check_in_api_persists_single_canonical_photo_path(self):
        """
        Verify check-in API route:
        1. Calls upload_to_firebase_storage once.
        2. Database document stores only ONE canonical storage path across all photo path fields.
        3. Double check-in returns 409 and does not upload duplicate files.
        """
        from fastapi.testclient import TestClient
        from app.main import app
        from app.services.attendance_service import get_attendance_today
        from app.services.firestore_service import FirestoreService

        client = TestClient(app)

        # Login employee
        login_res = client.post("/api/auth/login", json={"email": "employee@arshith.com", "password": "Employee@123"})
        self.assertEqual(login_res.status_code, 200, f"Login failed: {login_res.text}")
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        today_iso = get_attendance_today().isoformat()
        user = login_res.json().get("user", {})
        test_emp_id = user.get("employee_id") or user.get("employeeId") or "EMP-1001"
        rec_id = f"{test_emp_id}_{today_iso}"

        # Clean existing record if any
        FirestoreService.delete("attendance", rec_id)

        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.generate_signed_url.return_value = "https://storage.googleapis.com/test-bucket/attendancePhotos/UID_001/2026-10-27.jpg"
        mock_bucket.blob.return_value = mock_blob

        photo_bytes = make_test_jpeg(80, 80)

        with patch("app.core.firebase.is_firebase_live", return_value=True), \
             patch("app.core.firebase.get_storage_bucket", return_value=mock_bucket):

            # 1. Perform Check-In (WFH to bypass office geofence dependency in test environment)
            res = client.post(
                "/api/attendance/check-in",
                headers=headers,
                files={"photo": ("selfie.jpg", photo_bytes, "image/jpeg")},
                data={"workMode": "WFH", "lateReason": "Scheduled check-in"},
            )

            self.assertEqual(res.status_code, 200, f"Check-in failed: {res.text}")
            res_data = res.json()
            self.assertTrue(res_data["success"])
            self.assertTrue(res_data["hasCheckInPhoto"])

            # 2. Check the saved Firestore record
            saved_doc = FirestoreService.get_by_id("attendance", rec_id)
            self.assertIsNotNone(saved_doc, "Attendance record should exist in Firestore")

            # Check that ALL photo path fields reference the EXACT SAME single canonical path
            key_path = saved_doc.get("check_in_photo_key")
            storage_path = saved_doc.get("check_in_photo_storage_path")
            photo_path = saved_doc.get("checkInPhotoPath")

            self.assertEqual(key_path, storage_path, "check_in_photo_key and check_in_photo_storage_path must be identical!")
            self.assertEqual(photo_path, storage_path, "checkInPhotoPath and check_in_photo_storage_path must be identical!")
            self.assertTrue(storage_path.startswith("attendancePhotos/"), f"Path {storage_path} must follow attendancePhotos/ convention")
            self.assertTrue(storage_path.endswith(f"{today_iso}.jpg"), f"Filename must end with {today_iso}.jpg")

            # Verify that only ONE upload occurred
            self.assertEqual(mock_blob.upload_from_string.call_count, 1, "Expected exactly 1 upload to Cloud Storage")

            # 3. Duplicate check-in attempt (e.g. accidental double click) must fail with 409
            dup_res = client.post(
                "/api/attendance/check-in",
                headers=headers,
                files={"photo": ("selfie.jpg", photo_bytes, "image/jpeg")},
                data={"workMode": "WFH"},
            )
            self.assertEqual(dup_res.status_code, 409, "Duplicate check-in should be rejected with 409 Conflict")
            # Upload count should still be 1 (no extra upload on duplicate attempt)
            self.assertEqual(mock_blob.upload_from_string.call_count, 1)

        # Clean up test attendance record
        FirestoreService.delete("attendance", rec_id)


if __name__ == "__main__":
    unittest.main()

