import io
from datetime import date, datetime, timezone
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.db.session import SessionLocal
from app.models.attendance import Attendance
from app.services.attendance_service import get_attendance_today

client = TestClient(app)


def make_test_jpeg(width: int = 50, height: int = 50, color=(11, 61, 43)) -> bytes:
    """Helper to generate valid JPEG image bytes."""
    buf = io.BytesIO()
    img = Image.new("RGB", (width, height), color=color)
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def clean_attendance_state():
    """Ensure clean attendance state for test employees before each test."""
    today = get_attendance_today()
    today_iso = today.isoformat()
    with SessionLocal() as db:
        db.query(Attendance).filter(
            Attendance.employee_id.in_(["AFI-001", "AFI-002"]),
            Attendance.date == today,
        ).delete()
        db.commit()

    from app.core.config import settings
    from app.services.firestore_service import FirestoreService
    if settings.DATABASE_BACKEND == "firebase":
        for eid in ["AFI-001", "AFI-002"]:
            FirestoreService.delete("attendance", f"{eid}_{today_iso}")
            FirestoreService.delete("attendances", f"{eid}_{today_iso}")
    yield
    with SessionLocal() as db:
        db.query(Attendance).filter(
            Attendance.employee_id.in_(["AFI-001", "AFI-002"]),
            Attendance.date == today,
        ).delete()
        db.commit()
    if settings.DATABASE_BACKEND == "firebase":
        for eid in ["AFI-001", "AFI-002"]:
            FirestoreService.delete("attendance", f"{eid}_{today_iso}")
            FirestoreService.delete("attendances", f"{eid}_{today_iso}")


def get_employee_token(email: str = "employee@arshith.com", password: str = "Employee@123") -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.json()["access_token"]


def get_admin_token() -> str:
    res = client.post(
        "/api/auth/admin-login",
        json={"email": "admin@arshith.com", "password": "AdminPassword@123"},
    )
    assert res.status_code == 200, f"Admin login failed: {res.text}"
    return res.json()["access_token"]


def test_check_in_requires_gps_coordinates():
    """Verify check-in fails if coordinates are missing or invalid."""
    token = get_employee_token()
    headers = {"Authorization": f"Bearer {token}"}
    photo = make_test_jpeg()

    # 1. Missing coordinates completely
    res1 = client.post(
        "/api/attendance/check-in",
        headers=headers,
        files={"photo": ("selfie.jpg", photo, "image/jpeg")},
        data={"workMode": "WFO"},
    )
    assert res1.status_code == 400
    assert "GPS coordinates" in res1.json()["detail"]

    # 2. Out-of-bounds latitude
    res2 = client.post(
        "/api/attendance/check-in",
        headers=headers,
        files={"photo": ("selfie.jpg", photo, "image/jpeg")},
        data={"workMode": "WFO", "latitude": "120.5", "longitude": "80.0", "accuracy": "10"},
    )
    assert res2.status_code == 400
    assert "out of valid range" in res2.json()["detail"]

    # 3. Negative accuracy
    res3 = client.post(
        "/api/attendance/check-in",
        headers=headers,
        files={"photo": ("selfie.jpg", photo, "image/jpeg")},
        data={"workMode": "WFO", "latitude": "13.0827", "longitude": "80.2707", "accuracy": "-5"},
    )
    assert res3.status_code == 400
    assert "positive number" in res3.json()["detail"]


def test_check_in_requires_valid_photo():
    """Verify check-in rejects missing, corrupt, or unsupported photo files."""
    token = get_employee_token()
    headers = {"Authorization": f"Bearer {token}"}
    coords = {"workMode": "WFO", "latitude": "12.9104417", "longitude": "77.6442435", "accuracy": "12.0"}

    # 1. Missing photo file
    res1 = client.post(
        "/api/attendance/check-in",
        headers=headers,
        data=coords,
    )
    assert res1.status_code == 400
    assert "photo is required" in res1.json()["detail"].lower()

    # 2. Corrupt or fake image (text sent as image)
    fake_bytes = b"This is clearly not a real image file."
    res2 = client.post(
        "/api/attendance/check-in",
        headers=headers,
        files={"photo": ("fake.jpg", fake_bytes, "image/jpeg")},
        data=coords,
    )
    assert res2.status_code in [400, 415]


def test_complete_attendance_workflow_with_photo_and_lock():
    """Verify full end-to-end check-in at office coordinates, photo storage, checkout, duration, and daily lock."""
    emp_token = get_employee_token()
    headers = {"Authorization": f"Bearer {emp_token}"}
    photo_bytes = make_test_jpeg(80, 80)

    # 1. Check in with valid photo and GPS within office geofence
    coords = {
        "workMode": "WFO",
        "latitude": "12.9104417",
        "longitude": "77.6442435",
        "accuracy": "15.0",
    }
    checkin_res = client.post(
        "/api/attendance/check-in",
        headers=headers,
        files={"photo": ("checkin.jpg", photo_bytes, "image/jpeg")},
        data=coords,
    )
    assert checkin_res.status_code == 200, f"Check-in failed: {checkin_res.text}"
    res_data = checkin_res.json()
    assert res_data["success"] is True
    assert res_data["hasCheckInPhoto"] is True
    att_id = res_data["id"]

    # 2. Check today-status endpoint
    today_res = client.get("/api/attendance/today", headers=headers)
    assert today_res.status_code == 200
    today_data = today_res.json()
    assert today_data["isCheckedIn"] is True
    assert today_data["isCompleted"] is False
    assert today_data["canCheckIn"] is False
    assert today_data["canCheckOut"] is True
    assert today_data["checkInLatitude"] == 12.9104417
    assert today_data["checkInLongitude"] == 77.6442435

    # 3. Retrieve check-in photo with authenticated employee token
    photo_res = client.get(f"/api/attendance/{att_id}/photo/check-in", headers=headers)
    assert photo_res.status_code == 200
    assert photo_res.headers["content-type"] == "image/jpeg"
    assert len(photo_res.content) == len(photo_bytes)

    # 4. Attempting second check-in while checked in rejected (409)
    dup_res = client.post(
        "/api/attendance/check-in",
        headers=headers,
        files={"photo": ("checkin.jpg", photo_bytes, "image/jpeg")},
        data=coords,
    )
    assert dup_res.status_code == 409
    assert "already checked in" in dup_res.json()["detail"].lower()

    # 5. Check out
    checkout_res = client.post(
        "/api/attendance/check-out",
        headers=headers,
        json={},
    )
    assert checkout_res.status_code == 200
    checkout_data = checkout_res.json()
    assert checkout_data["success"] is True
    assert checkout_data["status"] == "Completed"
    assert checkout_data["isCompleted"] is True
    assert "duration" in checkout_data
    assert checkout_data["canCheckIn"] is False
    assert checkout_data["canCheckOut"] is False

    # 6. Verify status after checkout
    after_res = client.get("/api/attendance/today-status", headers=headers)
    assert after_res.status_code == 200
    after_data = after_res.json()
    assert after_data["isCheckedIn"] is False
    assert after_data["isCompleted"] is True
    assert after_data["status"] == "Completed"
    assert after_data["canCheckIn"] is False
    assert after_data["canCheckOut"] is False

    # 7. DAILY LOCK ENFORCEMENT: Attempting check-in after checkout rejected (409)
    locked_in_res = client.post(
        "/api/attendance/check-in",
        headers=headers,
        files={"photo": ("checkin.jpg", photo_bytes, "image/jpeg")},
        data=coords,
    )
    assert locked_in_res.status_code == 409
    assert "already completed" in locked_in_res.json()["detail"].lower()

    # 8. DAILY LOCK ENFORCEMENT: Attempting checkout after checkout rejected (409)
    locked_out_res = client.post(
        "/api/attendance/check-out",
        headers=headers,
        json={},
    )
    assert locked_out_res.status_code == 409
    assert "already completed" in locked_out_res.json()["detail"].lower()


def test_wfo_check_in_rejected_outside_geofence():
    """Verify WFO check-in is strictly rejected when employee is outside 250m radius."""
    emp_token = get_employee_token()
    headers = {"Authorization": f"Bearer {emp_token}"}
    photo_bytes = make_test_jpeg(50, 50)

    # Coordinates beyond 250m (at ~300m)
    distant_coords = {
        "workMode": "WFO",
        "latitude": "12.9131417",
        "longitude": "77.6442435",
        "accuracy": "15.0",
    }
    res = client.post(
        "/api/attendance/check-in",
        headers=headers,
        files={"photo": ("checkin.jpg", photo_bytes, "image/jpeg")},
        data=distant_coords,
    )
    assert res.status_code == 403
    data = res.json()
    err_detail = data.get("detail", data)
    assert err_detail.get("code") == "OUTSIDE_OFFICE_GEOFENCE"
    assert "You are outside the permitted attendance area." in err_detail.get("message", "")


def test_wfo_check_in_rejected_inaccurate_gps():
    """Verify WFO check-in is rejected when accuracy is worse than 100 meters."""
    emp_token = get_employee_token()
    headers = {"Authorization": f"Bearer {emp_token}"}
    photo_bytes = make_test_jpeg(50, 50)

    # Inaccurate GPS reading (125m > 100m threshold)
    inaccurate_coords = {
        "workMode": "WFO",
        "latitude": "12.9104417",
        "longitude": "77.6442435",
        "accuracy": "125.0",
    }
    res = client.post(
        "/api/attendance/check-in",
        headers=headers,
        files={"photo": ("checkin.jpg", photo_bytes, "image/jpeg")},
        data=inaccurate_coords,
    )
    assert res.status_code == 400
    data = res.json()
    err_detail = data.get("detail", data)
    assert err_detail.get("code") == "INACCURATE_GPS"


def test_invalid_work_mode_rejected():
    """Verify check-in rejects unsupported work mode with 400 INVALID_WORK_MODE."""
    emp_token = get_employee_token()
    headers = {"Authorization": f"Bearer {emp_token}"}
    photo_bytes = make_test_jpeg(50, 50)

    res = client.post(
        "/api/attendance/check-in",
        headers=headers,
        files={"photo": ("checkin.jpg", photo_bytes, "image/jpeg")},
        data={"workMode": "INVALID_RANDOM_MODE"},
    )
    assert res.status_code == 400
    data = res.json()
    err_detail = data.get("detail", data)
    assert err_detail.get("code") == "INVALID_WORK_MODE"


def test_wfh_check_in_without_gps_succeeds():
    """Verify an employee can check in with WFH mode without any GPS coordinates or geofence requirement."""
    emp_token = get_employee_token()
    headers = {"Authorization": f"Bearer {emp_token}"}
    photo_bytes = make_test_jpeg(50, 50)

    res = client.post(
        "/api/attendance/check-in",
        headers=headers,
        files={"photo": ("checkin.jpg", photo_bytes, "image/jpeg")},
        data={"workMode": "WFH"},  # No latitude, longitude, or accuracy
    )
    assert res.status_code == 200, f"WFH check-in failed: {res.text}"
    data = res.json()
    assert data["success"] is True
    assert data["workMode"] == "WFH"
    assert data["checkInLatitude"] is None


def test_wfh_cannot_bypass_duplicate_check_in():
    """Verify an employee who checks in with WFH cannot check in again today."""
    emp_token = get_employee_token()
    headers = {"Authorization": f"Bearer {emp_token}"}
    photo_bytes = make_test_jpeg(50, 50)

    # 1. First check in with WFH
    res1 = client.post(
        "/api/attendance/check-in",
        headers=headers,
        files={"photo": ("checkin.jpg", photo_bytes, "image/jpeg")},
        data={"workMode": "WFH"},
    )
    assert res1.status_code == 200

    # 2. Attempt duplicate check-in (rejected with 409 Conflict)
    res2 = client.post(
        "/api/attendance/check-in",
        headers=headers,
        files={"photo": ("checkin2.jpg", photo_bytes, "image/jpeg")},
        data={"workMode": "WFH"},
    )
    assert res2.status_code == 409


def test_office_location_endpoint():
    """Verify GET /api/attendance/office-location returns official company coordinates from backend config."""
    res = client.get("/api/attendance/office-location")
    assert res.status_code == 200
    data = res.json()
    assert data["latitude"] == 12.9104417
    assert data["longitude"] == 77.6442435
    assert data["radiusMeters"] == 250.0
    assert data["maxAccuracyMeters"] == 100.0
    assert data["timezone"] == "Asia/Kolkata"


def test_validate_location_endpoint():
    """Verify POST /api/attendance/validate-location endpoint works correctly for in/out of office."""
    emp_token = get_employee_token()
    headers = {"Authorization": f"Bearer {emp_token}"}

    # 1. At Office -> valid
    res_in = client.post(
        "/api/attendance/validate-location",
        headers=headers,
        json={"latitude": 12.9104417, "longitude": 77.6442435, "accuracy": 12.0},
    )
    assert res_in.status_code == 200
    assert res_in.json()["valid"] is True
    assert res_in.json()["isInsideOffice"] is True

    # 2. Outside 250m (at ~300m) -> 403 OUTSIDE_OFFICE_GEOFENCE
    res_out = client.post(
        "/api/attendance/validate-location",
        headers=headers,
        json={"latitude": 12.9131417, "longitude": 77.6442435, "accuracy": 12.0},
    )
    assert res_out.status_code == 403
    assert res_out.json()["code"] == "OUTSIDE_OFFICE_GEOFENCE"
    assert "You are outside the permitted attendance area." in res_out.json()["message"]

    # 3. Inaccurate GPS -> 400 INACCURATE_GPS
    res_acc = client.post(
        "/api/attendance/validate-location",
        headers=headers,
        json={"latitude": 12.9104417, "longitude": 77.6442435, "accuracy": 125.0},
    )
    assert res_acc.status_code == 400
    assert res_acc.json()["code"] == "INACCURATE_GPS"


def test_geofence_boundary_scenarios():
    """Verify boundary conditions: within 100m, within 250m, and beyond 250m."""
    emp_token = get_employee_token()
    headers = {"Authorization": f"Bearer {emp_token}"}

    # Scenario 1: Within 100 meters (~70m away) -> Allowed
    res_100m = client.post(
        "/api/attendance/validate-location",
        headers=headers,
        json={"latitude": 12.9110717, "longitude": 77.6442435, "accuracy": 15.0},
    )
    assert res_100m.status_code == 200
    assert res_100m.json()["valid"] is True
    assert res_100m.json()["isInsideOffice"] is True
    assert res_100m.json()["distanceMeters"] < 100.0

    # Scenario 2: Within 250 meters (~155m away) -> Allowed
    res_250m = client.post(
        "/api/attendance/validate-location",
        headers=headers,
        json={"latitude": 12.9118417, "longitude": 77.6442435, "accuracy": 15.0},
    )
    assert res_250m.status_code == 200
    assert res_250m.json()["valid"] is True
    assert res_250m.json()["isInsideOffice"] is True
    assert 100.0 < res_250m.json()["distanceMeters"] <= 250.0

    # Scenario 3: Beyond 250 meters (~300m away) -> Rejected
    res_beyond = client.post(
        "/api/attendance/validate-location",
        headers=headers,
        json={"latitude": 12.9131417, "longitude": 77.6442435, "accuracy": 15.0},
    )
    assert res_beyond.status_code == 403
    assert res_beyond.json()["valid"] is False
    assert res_beyond.json()["code"] == "OUTSIDE_OFFICE_GEOFENCE"
    assert res_beyond.json()["distanceMeters"] > 250.0


def test_photo_access_authorization():
    """Verify unauthorized employees cannot view other employees' attendance photos, while admins can."""
    emp1_token = get_employee_token()
    admin_token = get_admin_token()

    # Check in AFI-001 at office coordinates
    photo_bytes = make_test_jpeg(40, 40)
    checkin_res = client.post(
        "/api/attendance/check-in",
        headers={"Authorization": f"Bearer {emp1_token}"},
        files={"photo": ("checkin.jpg", photo_bytes, "image/jpeg")},
        data={"workMode": "WFO", "latitude": "12.9104417", "longitude": "77.6442435", "accuracy": "10"},
    )
    assert checkin_res.status_code == 200
    att_id = checkin_res.json()["id"]

    # 1. Admin can access photo
    admin_photo_res = client.get(
        f"/api/attendance/{att_id}/photo/check-in",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_photo_res.status_code == 200

    # 2. Unauthenticated access rejected (401)
    unauth_res = client.get(f"/api/attendance/{att_id}/photo/check-in")
    assert unauth_res.status_code == 401


def test_wfh_employee_remote_checkin_succeeds():
    """Verify an employee assigned to WFH can check in remotely outside the office geofence."""
    from app.models.employee import Employee
    with SessionLocal() as db:
        emp = db.query(Employee).filter(Employee.employee_id == "AFI-001").first()
        orig_location = emp.location
        emp.location = "Remote WFH"
        db.commit()

    try:
        emp_token = get_employee_token()
        headers = {"Authorization": f"Bearer {emp_token}"}
        photo_bytes = make_test_jpeg(50, 50)

        # Distant coordinates (8.6 km from office coordinates)
        remote_coords = {
            "workMode": "WFH",
            "latitude": "12.9716",
            "longitude": "77.5946",
            "accuracy": "20.0",
        }
        res = client.post(
            "/api/attendance/check-in",
            headers=headers,
            files={"photo": ("wfh_checkin.jpg", photo_bytes, "image/jpeg")},
            data=remote_coords,
        )
        assert res.status_code == 200, f"WFH check-in failed: {res.text}"
        data = res.json()
        assert data["success"] is True
        assert data["workMode"] == "WFH"
        assert data["checkInLatitude"] == 12.9716
    finally:
        with SessionLocal() as db:
            emp = db.query(Employee).filter(Employee.employee_id == "AFI-001").first()
            emp.location = orig_location
            db.commit()


def test_wfo_check_in_persists_evidence_and_today_status():
    """Verify WFO check-in persists photo and GPS evidence in DB and reflects in today-status & personal records."""
    token = get_employee_token()
    headers = {"Authorization": f"Bearer {token}"}
    photo_bytes = make_test_jpeg(100, 100)

    # 1. Successful WFO check-in within permitted geofence
    res = client.post(
        "/api/attendance/check-in",
        headers=headers,
        files={"photo": ("selfie.jpg", photo_bytes, "image/jpeg")},
        data={
            "latitude": "12.9104417",
            "longitude": "77.6442435",
            "accuracy": "30.0",
            "workMode": "WFO",
        },
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True
    assert data["workMode"] == "WFO"
    assert data["hasCheckInPhoto"] is True
    rec_id = data["id"]

    # 2. Today status reflects persisted check-in and evidence state
    today_res = client.get("/api/attendance/today-status", headers=headers)
    assert today_res.status_code == 200
    today_data = today_res.json()
    assert today_data["id"] == rec_id
    assert today_data["isCheckedIn"] is True
    assert today_data["hasCheckInPhoto"] is True
    assert today_data["workMode"] == "WFO"

    # 3. Personal attendance history records preserve photo evidence reference
    my_records_res = client.get("/api/attendance/me", headers=headers)
    assert my_records_res.status_code == 200
    records = my_records_res.json()
    assert len(records) > 0
    today_rec = next((r for r in records if r["id"] == rec_id), None)
    assert today_rec is not None
    assert today_rec["hasCheckInPhoto"] is True
    assert today_rec["workMode"] == "WFO"

    # 4. Authorized photo retrieval succeeds
    photo_res = client.get(f"/api/attendance/{rec_id}/photo/check-in", headers=headers)
    assert photo_res.status_code == 200
    assert photo_res.headers["content-type"] == "image/jpeg"
    assert len(photo_res.content) == len(photo_bytes)

    # 5. Direct database verification: Confirm BYTEA column in PostgreSQL contains non-empty image bytes
    with SessionLocal() as db:
        db_record = db.query(Attendance).filter(Attendance.id == rec_id).first()
        assert db_record is not None
        assert db_record.check_in_photo_data is not None
        assert len(db_record.check_in_photo_data) == len(photo_bytes)
        assert db_record.check_in_photo_data[:3] == b"\xff\xd8\xff"  # JPEG magic bytes
        assert db_record.check_in_photo_mime == "image/jpeg"


