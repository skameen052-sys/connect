import pytest
from datetime import datetime, timezone, date
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.services.firestore_service import FirestoreService
from app.core.security import create_access_token
from app.core.firebase import get_firestore_client
from app.routers.attendance import is_checkin_late

client = TestClient(app)
IST = ZoneInfo("Asia/Kolkata")


class DummyDB:
    def query(self, *args, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return None


def test_ist_cutoff_930am_rule():
    """
    Scenario 1-4:
    1. Check-in at 9:20 AM IST: no late reason required.
    2. Check-in at exactly 9:30 AM IST: no late reason required.
    3. Check-in at 9:31 AM IST: late reason required.
    4. Check-in at 10:00 AM IST: late reason required.
    """
    dummy_db = DummyDB()

    # 1. 9:20 AM IST -> Not late
    dt_920 = datetime(2026, 10, 22, 9, 20, 0, tzinfo=IST)
    assert is_checkin_late(dt_920, dummy_db) is False

    # 2. Exactly 9:30 AM IST -> Not late
    dt_930 = datetime(2026, 10, 22, 9, 30, 0, tzinfo=IST)
    assert is_checkin_late(dt_930, dummy_db) is False

    # 3. 9:31 AM IST -> Late (Mandatory reason required)
    dt_931 = datetime(2026, 10, 22, 9, 31, 0, tzinfo=IST)
    assert is_checkin_late(dt_931, dummy_db) is True

    # 4. 10:00 AM IST -> Late (Mandatory reason required)
    dt_1000 = datetime(2026, 10, 22, 10, 0, 0, tzinfo=IST)
    assert is_checkin_late(dt_1000, dummy_db) is True


@pytest.fixture
def late_attendance_employee():
    """
    Creates an employee with a late attendance record already recorded today.
    """
    uid = "test_emp_late_checkin_uid_202"
    emp_id = "AFI-LATE-202"
    email = "late_emp_test@arshithgroup.com"
    today_str = date.today().isoformat()
    doc_id = f"{emp_id}_{today_str}"

    emp_doc = {
        "uid": uid,
        "id": uid,
        "employeeId": emp_id,
        "employee_id": emp_id,
        "name": "Late Employee Test",
        "fullName": "Late Employee Test",
        "email": email,
        "role": "Employee",
        "status": "approved",
    }
    FirestoreService.save("employees", uid, emp_doc)

    # Recorded check-in at 09:45 AM (Late)
    record_doc = {
        "id": doc_id,
        "employeeId": emp_id,
        "employee_id": emp_id,
        "employeeName": "Late Employee Test",
        "date": today_str,
        "workMode": "WFO",
        "status": "Late",
        "checkIn": "09:45 AM",
        "checkOut": "--",
        "isLate": True,
        "lateReason": None,
        "late_reason": None,
        "lateReasonStatus": "PENDING",
        "late_reason_status": "PENDING",
        "lateReasonSubmittedAt": None,
        "isCheckedIn": True,
        "isCompleted": False,
    }
    FirestoreService.save("attendance", doc_id, record_doc)
    FirestoreService.save_subdocument("attendance", uid, "records", today_str, record_doc)

    token = create_access_token(
        subject=uid,
        role="employee",
        extra_claims={
            "email": email,
            "employeeId": emp_id,
            "name": "Late Employee Test",
        },
    )

    yield {
        "uid": uid,
        "employee_id": emp_id,
        "email": email,
        "token": token,
        "record_id": doc_id,
        "date": today_str,
    }

    # Cleanup
    FirestoreService.delete("employees", uid)
    FirestoreService.delete("attendance", doc_id)
    try:
        db = get_firestore_client()
        if db:
            db.collection("attendance").document(uid).collection("records").document(today_str).delete()
    except Exception:
        pass


@pytest.fixture
def ontime_attendance_employee():
    """
    Creates an employee who checked in on time (09:15 AM).
    """
    uid = "test_emp_ontime_checkin_uid_203"
    emp_id = "AFI-ONTIME-203"
    email = "ontime_emp_test@arshithgroup.com"
    today_str = date.today().isoformat()
    doc_id = f"{emp_id}_{today_str}"

    emp_doc = {
        "uid": uid,
        "id": uid,
        "employeeId": emp_id,
        "employee_id": emp_id,
        "name": "Ontime Employee Test",
        "fullName": "Ontime Employee Test",
        "email": email,
        "role": "Employee",
        "status": "approved",
    }
    FirestoreService.save("employees", uid, emp_doc)

    record_doc = {
        "id": doc_id,
        "employeeId": emp_id,
        "employee_id": emp_id,
        "employeeName": "Ontime Employee Test",
        "date": today_str,
        "workMode": "WFO",
        "status": "Present",
        "checkIn": "09:15 AM",
        "checkOut": "--",
        "isLate": False,
        "lateReason": None,
        "late_reason": None,
        "lateReasonStatus": "NOT_REQUIRED",
        "isCheckedIn": True,
        "isCompleted": False,
    }
    FirestoreService.save("attendance", doc_id, record_doc)
    FirestoreService.save_subdocument("attendance", uid, "records", today_str, record_doc)

    token = create_access_token(
        subject=uid,
        role="employee",
        extra_claims={
            "email": email,
            "employeeId": emp_id,
            "name": "Ontime Employee Test",
        },
    )

    yield {
        "uid": uid,
        "employee_id": emp_id,
        "token": token,
        "record_id": doc_id,
    }

    # Cleanup
    FirestoreService.delete("employees", uid)
    FirestoreService.delete("attendance", doc_id)
    try:
        db = get_firestore_client()
        if db:
            db.collection("attendance").document(uid).collection("records").document(today_str).delete()
    except Exception:
        pass


def test_empty_reason_rejected(late_attendance_employee):
    """
    Scenario 5: Empty reason must be rejected with 400 Bad Request.
    """
    token = late_attendance_employee["token"]
    res = client.post(
        "/api/attendance/late-reason",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "attendanceId": late_attendance_employee["record_id"],
            "reason": "",
        },
    )
    assert res.status_code == 400
    assert "cannot be empty" in res.json().get("detail", "").lower()


def test_whitespace_only_reason_rejected(late_attendance_employee):
    """
    Scenario 6: Whitespace-only reason must be rejected with 400 Bad Request.
    """
    token = late_attendance_employee["token"]
    res = client.post(
        "/api/attendance/late-reason",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "attendanceId": late_attendance_employee["record_id"],
            "reason": "   \n\t  \r  ",
        },
    )
    assert res.status_code == 400
    assert "cannot be empty" in res.json().get("detail", "").lower()


def test_unauthorized_request_rejected(late_attendance_employee):
    """
    Scenario 12: Unauthorized request rejected without valid auth token.
    """
    res = client.post(
        "/api/attendance/late-reason",
        json={
            "attendanceId": late_attendance_employee["record_id"],
            "reason": "Heavy rain on Silk Board junction",
        },
    )
    assert res.status_code in (401, 403)


def test_ontime_checkin_reason_not_allowed(ontime_attendance_employee):
    """
    Attempting to submit a late reason for an on-time check-in is rejected.
    """
    token = ontime_attendance_employee["token"]
    res = client.post(
        "/api/attendance/late-reason",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "attendanceId": ontime_attendance_employee["record_id"],
            "reason": "Traffic jam",
        },
    )
    assert res.status_code == 400
    detail = res.json().get("detail", "").lower()
    assert "not required" in detail or "on-time" in detail


def test_valid_reason_saved_and_prevents_duplicate(late_attendance_employee):
    """
    Scenario 7 & 9 & 10 & 11:
    - Valid reason saved against existing record.
    - Prevents repeated submission for the same record (409 Conflict).
    - Returned in employee getTodayStatus.
    - Returned in admin getRecords list.
    """
    token = late_attendance_employee["token"]
    rec_id = late_attendance_employee["record_id"]
    valid_reason = "Metro delay between Indiranagar and Trinity stations"

    # 1. Submit valid reason
    res = client.post(
        "/api/attendance/late-reason",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "attendanceId": rec_id,
            "reason": valid_reason,
        },
    )
    assert res.status_code == 200, f"Submit reason failed: {res.text}"
    body = res.json()
    assert body.get("success") is True
    assert body.get("lateReason") == valid_reason
    assert body.get("lateReasonStatus") == "SUBMITTED"

    # 2. Repeated submission: must be rejected with 409 Conflict (Scenario 9)
    res_repeat = client.post(
        "/api/attendance/late-reason",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "attendanceId": rec_id,
            "reason": "Another excuse should not duplicate",
        },
    )
    assert res_repeat.status_code == 409
    assert "already been submitted" in res_repeat.json().get("detail", "").lower()

    # 3. Employee dashboard status check (Scenario 10)
    res_status = client.get(
        "/api/attendance/today-status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_status.status_code == 200
    today_status = res_status.json()
    assert today_status.get("isLate") is True
    assert today_status.get("lateReason") == valid_reason
    assert today_status.get("lateReasonStatus") == "SUBMITTED"

    # 4. Admin dashboard check (Scenario 11)
    admin_uid = "test_admin_late_check_uid"
    admin_doc = {
        "id": admin_uid,
        "uid": admin_uid,
        "email": "admin_late_test@arshith.com",
        "role": "admin",
        "name": "Admin Verifier",
        "is_active": True,
    }
    FirestoreService.save("admins", admin_uid, admin_doc)

    try:
        admin_token = create_access_token(
            subject=admin_uid,
            role="admin",
            extra_claims={"email": "admin_late_test@arshith.com", "name": "Admin Verifier"},
        )
        res_admin = client.get(
            "/api/attendance/records",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_admin.status_code == 200
        records = res_admin.json()
        matching = [r for r in records if r.get("id") == rec_id or r.get("employeeId") == late_attendance_employee["employee_id"]]
        assert len(matching) > 0
        saved_record = matching[0]
        assert saved_record.get("isLate") is True
        assert saved_record.get("lateReason") == valid_reason
        assert saved_record.get("lateReasonStatus") == "SUBMITTED"
    finally:
        FirestoreService.delete("admins", admin_uid)
