import pytest
from datetime import datetime, timezone, date
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.firestore_service import FirestoreService

client = TestClient(app)

ADMIN_EMAIL = "admin@arshith.com"
ADMIN_PASSWORD = "AdminPassword@123"


@pytest.fixture(scope="module")
def admin_token():
    res = client.post(
        "/api/auth/admin-login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert res.status_code == 200, f"Admin login failed: {res.text}"
    return res.json()["access_token"]


def test_registration_requests_includes_mobile_applicants(admin_token):
    """
    Scenario 1: Mobile registration requests stored in 'employees' collection
    (e.g., Tharun, AFI-0879) must appear on the website Admin Portal.
    """
    res = client.get(
        "/api/registration-requests",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    
    # Check if mobile applicant Tharun or any pending employee is present
    tharun_req = next(
        (r for r in data if r.get("email") == "tharun@arshithgroup.com" or r.get("employeeId") == "AFI-0879"),
        None,
    )
    assert tharun_req is not None, "Mobile applicant Tharun (AFI-0879) not found in admin registration requests list!"
    tharun_name = tharun_req.get("fullName") or tharun_req.get("name") or tharun_req.get("full_name")
    assert tharun_name == "Tharun"
    assert tharun_req["status"] in ["Pending", "pending"]


def test_mobile_applicant_approval_and_login_lifecycle(admin_token):
    """
    Scenario 2 & 3: Approve mobile applicant and verify cross-platform status sync and employee login.
    """
    test_mobile_uid = "test_mobile_applicant_uid_999"
    test_emp_id = "AFI-TEST-999"
    test_email = "test_mobile_applicant@arshith.com"
    
    # 1. Simulate mobile app RegisterActivity.java write:
    # Writes to employees/{uid} with status: 'pending', role: 'Employee'
    now_iso = datetime.now(timezone.utc).isoformat()
    mobile_applicant_doc = {
        "uid": test_mobile_uid,
        "employeeId": test_emp_id,
        "employee_id": test_emp_id,
        "name": "Mobile Test User",
        "fullName": "Mobile Test User",
        "email": test_email,
        "phone": "9123456789",
        "role": "Employee",
        "status": "pending",
        "createdAt": now_iso,
        "source": "mobile_app",
    }
    FirestoreService.save("employees", test_mobile_uid, mobile_applicant_doc)
    
    # Also save in users with pending status
    from app.core.security import get_password_hash
    FirestoreService.save("users", test_mobile_uid, {
        "id": test_mobile_uid,
        "email": test_email,
        "hashed_password": get_password_hash("Applicant@123"),
        "role": "employee",
        "is_active": True,
        "approval_status": "PENDING",
        "status": "pending",
    })
    
    try:
        # 2. Verify applicant appears in Admin Portal GET /api/registration-requests
        res_list = client.get(
            "/api/registration-requests",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_list.status_code == 200
        items = res_list.json()
        found = any(i.get("email") == test_email for i in items)
        assert found, "Mobile applicant did not appear in admin registration requests list"

        # 3. Verify pending employee cannot log in yet
        login_res_pending = client.post(
            "/api/auth/login",
            json={"email": test_email, "password": "Applicant@123"},
        )
        assert login_res_pending.status_code == 403
        assert "pending" in login_res_pending.json()["detail"].lower()

        # 4. Admin Portal approves the registration request
        res_approve = client.patch(
            f"/api/registration-requests/{test_mobile_uid}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_approve.status_code == 200
        approve_data = res_approve.json()
        assert approve_data["status"] == "Approved"

        # 5. Verify the Firestore employee document has lowercase status: 'approved' (for Android MainActivity.java)
        updated_emp = FirestoreService.get_by_id("employees", test_mobile_uid)
        assert updated_emp is not None
        assert updated_emp.get("status") == "approved"
        assert updated_emp.get("approved_by") is not None
        assert updated_emp.get("approved_at") is not None

        # 6. Verify approved employee can now log in successfully
        login_res_approved = client.post(
            "/api/auth/login",
            json={"email": test_email, "password": "Applicant@123"},
        )
        assert login_res_approved.status_code == 200
        emp_token = login_res_approved.json()["access_token"]
        assert emp_token is not None

    finally:
        # Cleanup
        FirestoreService.delete("employees", test_mobile_uid)
        FirestoreService.delete("users", test_mobile_uid)
        FirestoreService.delete("registration_requests", test_mobile_uid)


def test_mobile_applicant_rejection_lifecycle(admin_token):
    """
    Scenario 4: Reject mobile applicant and verify status: 'rejected' and rejection reason.
    """
    test_mobile_uid = "test_mobile_applicant_reject_888"
    test_emp_id = "AFI-REJECT-888"
    test_email = "test_mobile_reject@arshith.com"

    now_iso = datetime.now(timezone.utc).isoformat()
    mobile_applicant_doc = {
        "uid": test_mobile_uid,
        "employeeId": test_emp_id,
        "employee_id": test_emp_id,
        "name": "Mobile Reject User",
        "email": test_email,
        "phone": "9988776655",
        "role": "Employee",
        "status": "pending",
        "createdAt": now_iso,
    }
    FirestoreService.save("employees", test_mobile_uid, mobile_applicant_doc)

    try:
        # Reject via Admin API
        res_reject = client.patch(
            f"/api/registration-requests/{test_mobile_uid}/reject",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"rejection_reason": "Incomplete documentation submitted"},
        )
        assert res_reject.status_code == 200
        assert res_reject.json()["status"] == "Rejected"

        # Verify Firestore employee doc status: 'rejected'
        updated_emp = FirestoreService.get_by_id("employees", test_mobile_uid)
        assert updated_emp is not None
        assert updated_emp.get("status") == "rejected"
        assert updated_emp.get("rejection_reason") == "Incomplete documentation submitted"

    finally:
        FirestoreService.delete("employees", test_mobile_uid)
        FirestoreService.delete("registration_requests", test_mobile_uid)


def test_duplicate_registration_prevention():
    """
    Scenario 5: Duplicate registration prevention using existing employee ID and email.
    """
    # Attempt to register with Tharun's existing email
    res_dup_email = client.post(
        "/api/auth/register",
        json={
            "employee_id": "AFI-NEW-UNIQUE",
            "full_name": "Duplicate Tester",
            "email": "tharun@arshithgroup.com",
            "password": "Password@123",
            "phone": "9876543210",
            "department": "Engineering",
            "designation": "Developer",
        },
    )
    assert res_dup_email.status_code in [400, 409]
    dup_json = res_dup_email.json()
    assert "duplicate" in dup_json.get("detail", "").lower() or "already" in str(dup_json).lower()

    # Attempt to register with Tharun's existing employee ID AFI-0879
    res_dup_id = client.post(
        "/api/auth/register",
        json={
            "employee_id": "AFI-0879",
            "full_name": "Duplicate Tester",
            "email": "brandnew@arshith.com",
            "password": "Password@123",
            "phone": "9876543210",
            "department": "Engineering",
            "designation": "Developer",
        },
    )
    assert res_dup_id.status_code in [400, 409]
    dup_id_json = res_dup_id.json()
    assert "duplicate" in dup_id_json.get("detail", "").lower() or "already" in str(dup_id_json).lower()


def test_attendance_mobile_subcollection_sync(admin_token):
    """
    Scenario 7, 8, 9: Attendance records created in mobile subcollection attendance/{uid}/records/{date}
    must be readable by web admin via collection_group('records') and check-in dual writes correctly.
    """
    test_uid = "test_sync_employee_uid_777"
    today_str = date.today().isoformat()
    now_iso = datetime.now(timezone.utc).isoformat()
    
    # 1. Simulate mobile app check-in writing to attendance/{uid}/records/{date}
    mobile_record = {
        "recordId": f"{test_uid}_{today_str}",
        "userId": test_uid,
        "employeeId": "AFI-SYNC-777",
        "employeeName": "Sync Test Employee",
        "date": today_str,
        "checkInTime": "09:15:00",
        "checkInTimestamp": now_iso,
        "checkInLatitude": 12.9104417,
        "checkInLongitude": 77.6442435,
        "checkInPhotoUrl": "https://firebasestorage.googleapis.com/v0/b/arshith-connect-attendance.firebasestorage.app/o/attendancePhotos%2Ftest.jpg",
        "status": "Present",
        "workType": "Office",
        "lateByMinutes": 0,
    }
    FirestoreService.save_subdocument("attendance", test_uid, "records", today_str, mobile_record)

    try:
        # 2. Query admin attendance history on web: must find the subcollection record via collection_group('records')
        res = client.get(
            "/api/attendance/history",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        records = res.json()
        assert isinstance(records, list)
        found = any(r.get("employee_id") == "AFI-SYNC-777" or r.get("employeeId") == "AFI-SYNC-777" for r in records)
        assert found, "Mobile attendance subcollection record not surfaced in admin attendance history!"

    finally:
        # Cleanup subdocument
        try:
            from app.core.firebase import get_firestore_client
            db = get_firestore_client()
            if db:
                db.collection("attendance").document(test_uid).collection("records").document(today_str).delete()
        except Exception:
            pass


def test_leaves_mobile_subcollection_sync(admin_token):
    """
    Scenario 10: Leaves submitted in mobile subcollection leaves/{uid}/requests/{requestId}
    must be readable by web admin via collection_group('requests').
    """
    test_uid = "test_sync_leave_uid_666"
    test_req_id = "REQ-LEAVE-SYNC-666"
    now_iso = datetime.now(timezone.utc).isoformat()

    mobile_leave = {
        "requestId": test_req_id,
        "userId": test_uid,
        "employeeId": "AFI-LEAVE-666",
        "employeeName": "Leave Sync Employee",
        "leaveType": "Sick Leave",
        "startDate": "2026-11-01",
        "endDate": "2026-11-02",
        "totalDays": 2,
        "reason": "Medical appointment",
        "status": "Pending",
        "appliedAt": now_iso,
    }
    FirestoreService.save_subdocument("leaves", test_uid, "requests", test_req_id, mobile_leave)

    try:
        # Query admin leaves on web: must find subcollection request
        res = client.get(
            "/api/leaves",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        leaves = res.json()
        assert isinstance(leaves, list)
        found = any(l.get("employee_id") == "AFI-LEAVE-666" or l.get("leave_code") == test_req_id for l in leaves)
        assert found, "Mobile leave subcollection request not surfaced in web leaves list!"

    finally:
        try:
            from app.core.firebase import get_firestore_client
            db = get_firestore_client()
            if db:
                db.collection("leaves").document(test_uid).collection("requests").document(test_req_id).delete()
        except Exception:
            pass


def test_announcements_cross_platform_sync(admin_token):
    """
    Scenario 11: Announcements created on web must be saved in Firestore canonical 'announcements'
    and reflected on both platforms.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    ann_payload = {
        "title": "Cross-Platform Integration Verified",
        "message": "Both mobile and website are now synchronized with Firebase.",
        "type": "Company",
        "send_to": "all",
    }
    res = client.post(
        "/api/announcements",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=ann_payload,
    )
    assert res.status_code in [200, 201]
    ann_data = res.json()
    assert ann_data["title"] == ann_payload["title"]
    ann_id = ann_data["id"]

    try:
        # Verify it exists in Firestore 'announcements'
        doc = FirestoreService.get_by_id("announcements", str(ann_id))
        assert doc is not None
        assert doc.get("title") == ann_payload["title"]

        # Verify get announcements endpoint
        get_res = client.get(
            "/api/announcements",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert get_res.status_code == 200
        items = get_res.json()
        assert any(i.get("id") == ann_id for i in items)

    finally:
        FirestoreService.delete("announcements", str(ann_id))
