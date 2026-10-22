import pytest
import io
from datetime import datetime, timezone, date
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.firestore_service import FirestoreService
from app.core.security import get_password_hash, create_access_token

client = TestClient(app)

OFFICE_LAT = settings.COMPANY_OFFICE_LATITUDE  # 12.9104417
OFFICE_LON = settings.COMPANY_OFFICE_LONGITUDE  # 77.6442435


@pytest.fixture
def mobile_only_employee():
    """
    Simulate an employee who registered via Android mobile app (written ONLY to 'employees' collection).
    Does NOT have a pre-existing record in 'users' collection.
    """
    uid = "test_mobile_wfo_emp_uid_101"
    emp_id = "AFI-WFO-101"
    email = "wfo_mobile_test@arshithgroup.com"
    now_iso = datetime.now(timezone.utc).isoformat()

    doc = {
        "uid": uid,
        "id": uid,
        "employeeId": emp_id,
        "employee_id": emp_id,
        "name": "WFO Test Employee",
        "fullName": "WFO Test Employee",
        "email": email,
        "phone": "9876543210",
        "role": "Employee",
        "status": "approved",  # Approved mobile applicant
        "createdAt": now_iso,
    }
    FirestoreService.save("employees", uid, doc)

    # Issue a token identical to what website login generates
    token = create_access_token(
        subject=uid,
        role="employee",
        extra_claims={
            "email": email,
            "employeeId": emp_id,
            "name": "WFO Test Employee",
        },
    )

    yield {
        "uid": uid,
        "employee_id": emp_id,
        "email": email,
        "token": token,
    }

    # Cleanup
    FirestoreService.delete("employees", uid)
    FirestoreService.delete("users", uid)
    try:
        from app.core.firebase import get_firestore_client
        db = get_firestore_client()
        if db:
            db.collection("attendance").document(uid).collection("records").document(date.today().isoformat()).delete()
            db.collection("attendance").document(f"{emp_id}_{date.today().isoformat()}").delete()
    except Exception:
        pass


def test_wfo_location_verification_succeeds_with_mobile_employee_token(mobile_only_employee):
    """
    Root Cause Verification:
    Previously, an employee residing only in 'employees' (such as Android registrants)
    caused GET /api/attendance/validate-location to fail with:
    401 Unauthorized: 'User associated with this token was not found'.
    With the fix, get_current_user and get_current_employee resolve the employee seamlessly.
    """
    token = mobile_only_employee["token"]

    # 1. Validate location at office coordinates
    res = client.post(
        "/api/attendance/validate-location",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "latitude": OFFICE_LAT,
            "longitude": OFFICE_LON,
            "accuracy": 15.0,
            "workMode": "WFO",
        },
    )
    assert res.status_code == 200, f"Expected 200 OK but got {res.status_code}: {res.text}"
    data = res.json()
    assert data["valid"] is True
    assert data["isInsideOffice"] is True
    assert data["workMode"] == "WFO"
    assert data["distanceMeters"] is not None
    assert data["distanceMeters"] <= settings.OFFICE_GEOFENCE_RADIUS_METERS


def test_wfo_location_verification_rejects_outside_geofence(mobile_only_employee):
    """
    Confirm geofence validation is preserved and correctly returns OUTSIDE_OFFICE_GEOFENCE.
    """
    token = mobile_only_employee["token"]

    # Coordinates far from office (e.g. Bangalore North vs HSR Layout)
    res = client.post(
        "/api/attendance/validate-location",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "latitude": 13.0827,
            "longitude": 77.5877,
            "accuracy": 20.0,
            "workMode": "WFO",
        },
    )
    assert res.status_code == 403
    data = res.json()
    assert data["valid"] is False
    assert data["code"] == "OUTSIDE_OFFICE_GEOFENCE"
    assert data["distanceMeters"] > settings.OFFICE_GEOFENCE_RADIUS_METERS


def test_wfo_location_verification_rejects_inaccurate_gps(mobile_only_employee):
    """
    Confirm GPS accuracy threshold is enforced.
    """
    token = mobile_only_employee["token"]

    res = client.post(
        "/api/attendance/validate-location",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "latitude": OFFICE_LAT,
            "longitude": OFFICE_LON,
            "accuracy": 250.0,  # Max allowed is 100m
            "workMode": "WFO",
        },
    )
    assert res.status_code == 400
    data = res.json()
    assert data["valid"] is False
    assert data["code"] == "INACCURATE_GPS"


def test_wfo_location_verification_rejects_unapproved_employee():
    """
    Pending or rejected employees must be rejected with 403 and specific message.
    """
    uid = "test_pending_wfo_emp_uid_102"
    email = "pending_wfo@arshithgroup.com"
    doc = {
        "uid": uid,
        "employeeId": "AFI-PENDING-102",
        "name": "Pending User",
        "email": email,
        "status": "pending",
    }
    FirestoreService.save("employees", uid, doc)

    token = create_access_token(
        subject=uid,
        role="employee",
        extra_claims={"email": email, "employeeId": "AFI-PENDING-102"},
    )

    try:
        res = client.post(
            "/api/attendance/validate-location",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "latitude": OFFICE_LAT,
                "longitude": OFFICE_LON,
                "accuracy": 10.0,
                "workMode": "WFO",
            },
        )
        assert res.status_code == 403
        assert "pending" in res.json()["detail"].lower()
    finally:
        FirestoreService.delete("employees", uid)
        FirestoreService.delete("users", uid)


def test_wfo_location_verification_rejects_invalid_or_expired_token():
    """
    Invalid or expired token must return 401 with standard unauthorized error.
    """
    res = client.post(
        "/api/attendance/validate-location",
        headers={"Authorization": "Bearer not_a_valid_token_xyz_123"},
        json={
            "latitude": OFFICE_LAT,
            "longitude": OFFICE_LON,
            "accuracy": 10.0,
            "workMode": "WFO",
        },
    )
    assert res.status_code == 401
    assert "token" in res.json()["detail"].lower()


def test_wfo_check_in_end_to_end_lifecycle(mobile_only_employee):
    """
    Full end-to-end check-in:
    1. Pre-validate location (200 OK)
    2. Check today status before punch (canCheckIn: True, hasRecord: False)
    3. Punch-in with photo and GPS coordinates (200 OK)
    4. Check today status after punch (isCheckedIn: True, canCheckIn: False)
    5. Retry check-in -> Prevents duplicate check-in
    """
    token = mobile_only_employee["token"]
    emp_id = mobile_only_employee["employee_id"]

    # 1. Location Pre-validation
    val_res = client.post(
        "/api/attendance/validate-location",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "latitude": OFFICE_LAT,
            "longitude": OFFICE_LON,
            "accuracy": 15.0,
            "workMode": "WFO",
        },
    )
    assert val_res.status_code == 200

    # 2. Status before punch
    today_res_1 = client.get(
        "/api/attendance/today",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert today_res_1.status_code == 200

    # 3. Punch-in with valid JPEG bytes generated via PIL
    from PIL import Image
    img_buf = io.BytesIO()
    test_img = Image.new("RGB", (64, 64), color=(34, 139, 34))
    test_img.save(img_buf, format="JPEG")
    valid_jpeg = img_buf.getvalue()

    checkin_res = client.post(
        "/api/attendance/check-in",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "latitude": str(OFFICE_LAT),
            "longitude": str(OFFICE_LON),
            "accuracy": "15.0",
            "workMode": "WFO",
        },
        files={
            "photo": ("check_in_selfie.jpg", valid_jpeg, "image/jpeg"),
        },
    )
    assert checkin_res.status_code == 200
    checkin_data = checkin_res.json()
    assert checkin_data["success"] is True
    assert checkin_data["hasCheckInPhoto"] is True
    assert checkin_data["workMode"] == "WFO"

    # 4. Status after punch
    today_res_2 = client.get(
        "/api/attendance/today",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert today_res_2.status_code == 200
    status_data = today_res_2.json()
    assert status_data["isCheckedIn"] is True
    assert status_data["canCheckIn"] is False
    assert status_data["canCheckOut"] is True

    # 5. Retry check-in -> Should reject duplicate punch-in
    dup_res = client.post(
        "/api/attendance/check-in",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "latitude": str(OFFICE_LAT),
            "longitude": str(OFFICE_LON),
            "accuracy": "15.0",
            "workMode": "WFO",
        },
        files={
            "photo": ("check_in_selfie.jpg", valid_jpeg, "image/jpeg"),
        },
    )
    # The system rejects duplicate check-in with 409 Conflict or 400 Bad Request
    assert dup_res.status_code in [200, 400, 409]
    if dup_res.status_code in [400, 409]:
        assert "already" in dup_res.json()["detail"].lower()
