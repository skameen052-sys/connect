import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

ADMIN_EMAIL = "admin@arshith.com"
ADMIN_PASSWORD = "AdminPassword@123"
EMPLOYEE_EMAIL = "employee@arshith.com"
EMPLOYEE_PASSWORD = "Employee@123"


@pytest.fixture(scope="module")
def admin_token():
    res = client.post(
        "/api/auth/admin-login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    if res.status_code != 200:
        # Fallback to Admin@123 if needed
        res = client.post(
            "/api/auth/admin-login",
            json={"email": ADMIN_EMAIL, "password": "Admin@123"},
        )
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.fixture(scope="module")
def employee_token():
    res = client.post(
        "/api/auth/login",
        json={"email": EMPLOYEE_EMAIL, "password": EMPLOYEE_PASSWORD},
    )
    assert res.status_code == 200
    return res.json()["access_token"]


def test_unauthorized_user_cannot_approve_or_reject(employee_token):
    """Test 11: Unauthorized user (employee or unauthenticated) attempting to approve or reject gets 403 or 401."""
    # 1. Unauthenticated request
    res_no_auth = client.patch(
        "/api/leaves/TEST-LEAVE-999",
        json={"status": "Approved"}
    )
    assert res_no_auth.status_code in [401, 403]

    # 2. Employee token on Admin endpoint
    res_emp = client.patch(
        "/api/leaves/TEST-LEAVE-999",
        json={"status": "Approved"},
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert res_emp.status_code == 403
    assert "Administrative privileges required" in res_emp.json().get("detail", "")


def test_invalid_leave_request_id(admin_token):
    """Test 10: Test an invalid leave request ID returns 404 Not Found."""
    res = client.patch(
        "/api/leaves/NONEXISTENT-LEAVE-ID-99999",
        json={"status": "Approved"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 404
    assert "not found" in res.json().get("detail", "").lower()


def test_approve_pending_leave_request(admin_token, employee_token):
    """Tests 1, 2, 5, 7, 9, 13: Approve pending leave request, verify database updates, and prevent re-approval."""
    # 1. Submit a test leave request as employee
    start_str = (date.today() + timedelta(days=20)).isoformat()
    end_str = (date.today() + timedelta(days=21)).isoformat()
    apply_res = client.post(
        "/api/leaves",
        json={
            "leaveType": "Casual Leave",
            "durationType": "Full-Day Leave",
            "startDate": start_str,
            "endDate": end_str,
            "reason": "Test leave for approval verification",
        },
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert apply_res.status_code == 201
    created_leave = apply_res.json()
    leave_id = created_leave["id"]
    assert created_leave["status"] == "Pending"

    # 2. Admin approves the leave
    approve_res = client.patch(
        f"/api/leaves/{leave_id}",
        json={"status": "Approved"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert approve_res.status_code == 200
    approved_leave = approve_res.json()
    assert approved_leave["status"] == "Approved"
    assert approved_leave["reviewed_by"] == ADMIN_EMAIL
    assert approved_leave["approved_at"] is not None
    assert approved_leave["reason"] == "Test leave for approval verification"
    assert approved_leave["start_date"] == start_str
    assert approved_leave["end_date"] == end_str

    # 3. Verify in leaves list that status is Approved
    list_res = client.get(
        "/api/leaves",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert list_res.status_code == 200
    all_leaves = list_res.json()
    matched = next((l for l in all_leaves if l.get("id") == leave_id or l.get("request_id") == leave_id), None)
    assert matched is not None
    assert matched["status"] == "Approved"

    # 4. Test 9: Attempting to process an already-approved request returns 400 Bad Request
    reapprove_res = client.patch(
        f"/api/leaves/{leave_id}",
        json={"status": "Approved"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert reapprove_res.status_code == 400
    assert "already Approved" in reapprove_res.json().get("detail", "")


def test_reject_pending_leave_request(admin_token, employee_token):
    """Tests 3, 4, 5, 8, 9, 13: Reject pending leave request, verify remarks and rejection status."""
    # 1. Submit another test leave request as employee
    start_str = (date.today() + timedelta(days=25)).isoformat()
    end_str = (date.today() + timedelta(days=25)).isoformat()
    apply_res = client.post(
        "/api/leaves",
        json={
            "leaveType": "Sick Leave",
            "durationType": "Full-Day Leave",
            "startDate": start_str,
            "endDate": end_str,
            "reason": "Test leave for rejection verification",
        },
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert apply_res.status_code == 201
    created_leave = apply_res.json()
    leave_id = created_leave["id"]

    # 2. Admin rejects the leave
    reject_res = client.patch(
        f"/api/leaves/{leave_id}",
        json={"status": "Rejected", "rejectionRemarks": "High workload during this sprint."},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert reject_res.status_code == 200
    rejected_leave = reject_res.json()
    assert rejected_leave["status"] == "Rejected"
    assert rejected_leave["reviewed_by"] == ADMIN_EMAIL
    assert rejected_leave["rejection_remarks"] == "High workload during this sprint."
    assert rejected_leave["reason"] == "Test leave for rejection verification"

    # 3. Test 9: Attempting to process an already-rejected request returns 400 Bad Request
    rereject_res = client.patch(
        f"/api/leaves/{leave_id}",
        json={"status": "Rejected"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert rereject_res.status_code == 400
    assert "already Rejected" in rereject_res.json().get("detail", "")
