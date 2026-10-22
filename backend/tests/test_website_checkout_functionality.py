import io
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.core.config import settings
from app.services.attendance_service import get_attendance_today, get_attendance_now
from app.services.firestore_service import FirestoreService

client = TestClient(app)


def make_test_jpeg(width: int = 60, height: int = 60, color=(14, 116, 144)) -> bytes:
    """Helper to generate a valid JPEG image."""
    buf = io.BytesIO()
    img = Image.new("RGB", (width, height), color=color)
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def clean_test_attendance():
    """Ensure clean attendance records before and after each test."""
    today = get_attendance_today()
    today_iso = today.isoformat()

    test_eids = ["AFI-001", "AFI-002", "AFI-004", "EMP-TEST-CHECKOUT", "test_user_approved"]
    if settings.DATABASE_BACKEND == "firebase":
        for eid in test_eids:
            FirestoreService.delete("attendance", f"{eid}_{today_iso}")
            FirestoreService.delete("attendances", f"{eid}_{today_iso}")
            FirestoreService.delete_subdocument("attendance", eid, "records", today_iso)
    else:
        from app.db.session import SessionLocal
        from app.models.attendance import Attendance
        with SessionLocal() as db:
            db.query(Attendance).filter(
                Attendance.employee_id.in_(test_eids),
                Attendance.date == today,
            ).delete()
            db.commit()

    yield

    if settings.DATABASE_BACKEND == "firebase":
        for eid in test_eids:
            FirestoreService.delete("attendance", f"{eid}_{today_iso}")
            FirestoreService.delete("attendances", f"{eid}_{today_iso}")
            FirestoreService.delete_subdocument("attendance", eid, "records", today_iso)
    else:
        from app.db.session import SessionLocal
        from app.models.attendance import Attendance
        with SessionLocal() as db:
            db.query(Attendance).filter(
                Attendance.employee_id.in_(test_eids),
                Attendance.date == today,
            ).delete()
            db.commit()


def get_employee_token(email: str = "employee@arshith.com", password: str = "Employee@123") -> tuple[str, dict]:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    data = res.json()
    return data["access_token"], data.get("user", {})


def get_admin_token() -> str:
    res = client.post(
        "/api/auth/admin-login",
        json={"email": "admin@arshith.com", "password": "AdminPassword@123"},
    )
    assert res.status_code == 200, f"Admin login failed: {res.text}"
    return res.json()["access_token"]


def test_checkout_unauthenticated_rejected():
    """Verify check-out is rejected when no authentication token is provided."""
    res = client.post("/api/attendance/check-out", json={})
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"
    assert "token is missing or invalid" in res.json().get("detail", "").lower()


def test_checkout_without_active_checkin_fails():
    """Verify check-out fails with 400 when an employee has not checked in for today."""
    token, user = get_employee_token()
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/attendance/check-out", headers=headers, json={})
    assert res.status_code == 400, f"Expected 400, got {res.status_code}: {res.text}"
    assert "without an active check-in" in res.json().get("detail", "").lower()


def test_complete_employee_website_checkout_workflow():
    """
    Test the complete employee check-in and check-out workflow:
    1. Authenticate employee
    2. Check in successfully (WFO mode with photo and GPS)
    3. Verify today status shows checked in, checkOutTime is '--'
    4. Call check-out endpoint without requiring manual employee ID input
    5. Verify check-out succeeds and returns server-authoritative check-out time and duration
    6. Verify today status reflects isCompleted=True, isCheckedIn=False, checkOutTime != '--'
    7. Verify working duration matches formatted duration (e.g. 'XX hrs YY mins')
    8. Verify duplicate check-out attempt is rejected with HTTP 409
    """
    token, user = get_employee_token("employee@arshith.com", "Employee@123")
    headers = {"Authorization": f"Bearer {token}"}
    emp_id = user.get("employeeId") or user.get("employee_id") or "AFI-001"

    # Step 1: Check in
    photo = make_test_jpeg(80, 80)
    checkin_payload = {
        "workMode": "WFO",
        "latitude": "12.9104417",
        "longitude": "77.6442435",
        "accuracy": "15.0",
    }
    checkin_res = client.post(
        "/api/attendance/check-in",
        headers=headers,
        files={"photo": ("selfie.jpg", photo, "image/jpeg")},
        data=checkin_payload,
    )
    assert checkin_res.status_code in [200, 201], f"Check-in failed: {checkin_res.text}"
    checkin_data = checkin_res.json()
    assert checkin_data.get("success") is True

    # Step 2: Verify today status before check-out
    status_before = client.get("/api/attendance/today-status", headers=headers)
    assert status_before.status_code == 200
    before_data = status_before.json()
    assert before_data["isCheckedIn"] is True
    assert before_data["isCompleted"] is False
    assert before_data["checkOutTime"] == "--"
    assert before_data["checkInTime"] != "--"

    # Step 3: Check out (employee sends empty payload or employeeId, neither manual nor hardcoded)
    checkout_res = client.post(
        "/api/attendance/check-out",
        headers=headers,
        json={"employeeId": emp_id},
    )
    assert checkout_res.status_code == 200, f"Check-out failed: {checkout_res.text}"
    checkout_data = checkout_res.json()

    assert checkout_data.get("success") is True
    assert checkout_data.get("status") == "Completed"
    assert checkout_data.get("isCompleted") is True
    assert checkout_data.get("isCheckedIn") is False
    assert checkout_data.get("canCheckIn") is False
    assert checkout_data.get("canCheckOut") is False

    # Check-out time must not be '--'
    checkout_time = checkout_data.get("checkOut") or checkout_data.get("checkOutTime")
    assert checkout_time and checkout_time != "--", f"Expected valid check-out time, got '{checkout_time}'"

    # Working duration must be formatted e.g. '00 hrs 00 mins'
    duration = checkout_data.get("duration") or checkout_data.get("workingDuration")
    assert duration and "hrs" in duration and "mins" in duration, f"Expected formatted duration, got '{duration}'"

    # Step 4: Verify today status after check-out (simulating website refresh)
    status_after = client.get("/api/attendance/today-status", headers=headers)
    assert status_after.status_code == 200
    after_data = status_after.json()

    assert after_data["isCheckedIn"] is False
    assert after_data["isCompleted"] is True
    assert after_data["status"] == "Completed"
    assert after_data["checkOutTime"] == checkout_time
    assert after_data["workingDuration"] == duration

    # Step 5: Duplicate check-out must be blocked (HTTP 409)
    dup_checkout = client.post(
        "/api/attendance/check-out",
        headers=headers,
        json={},
    )
    assert dup_checkout.status_code == 409, f"Expected 409 Conflict on second check-out, got {dup_checkout.status_code}"
    assert "already" in dup_checkout.json().get("detail", "").lower()


def test_checkout_works_when_employee_role_is_capitalized():
    """
    Verify employee checkout works seamlessly when employee record has 'role': 'Employee'
    and 'employeeId' in camelCase.
    """
    token, user = get_employee_token("yedulla@arshithgroup.com", "ValidPass123")
    headers = {"Authorization": f"Bearer {token}"}

    photo = make_test_jpeg(80, 80)
    checkin_res = client.post(
        "/api/attendance/check-in",
        headers=headers,
        files={"photo": ("selfie.jpg", photo, "image/jpeg")},
        data={
            "workMode": "WFO",
            "latitude": "12.9104417",
            "longitude": "77.6442435",
            "accuracy": "10.0",
        },
    )
    assert checkin_res.status_code in [200, 201], f"Checkin failed: {checkin_res.text}"

    # Employee checkout without passing employeeId in body
    checkout_res = client.post(
        "/api/attendance/check-out",
        headers=headers,
        json={},
    )
    assert checkout_res.status_code == 200, f"Check-out failed: {checkout_res.text}"
    res_data = checkout_res.json()
    assert res_data["success"] is True
    assert res_data["status"] == "Completed"
    assert res_data["isCompleted"] is True
    assert res_data["checkOutTime"] != "--"
    assert "hrs" in res_data["duration"]
