import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.firestore_service import FirestoreService
from app.core.security import get_password_hash

client = TestClient(app)

# Test constants
EXISTING_APPROVED_EMAIL = "yedulla@arshithgroup.com"
EXISTING_APPROVED_EID = "AFI-004"
EXISTING_APPROVED_PASS = "ValidPass123"

PENDING_EMAIL = "pending_worker@arshithgroup.com"
PENDING_EID = "AFI-PENDING-01"
PENDING_PASS = "PendingPass123"

REJECTED_EMAIL = "rejected_worker@arshithgroup.com"
REJECTED_EID = "AFI-REJECTED-01"
REJECTED_PASS = "RejectedPass123"

INACTIVE_EMAIL = "inactive_worker@arshithgroup.com"
INACTIVE_EID = "AFI-INACTIVE-01"
INACTIVE_PASS = "InactivePass123"


def cleanup_test_data():
    from app.services.firestore_service import _load_local_db, _save_local_db
    db = _load_local_db()
    for coll in ["users", "employees", "registration_requests", "admins"]:
        if coll in db:
            db[coll] = [
                item for item in db[coll]
                if not (
                    "AFI-REG-" in str(item.get("employee_id") or item.get("employeeId") or "")
                    or any(kw in str(item.get("email", "")).lower() for kw in [
                        "new_hire_", "eight_pwd_", "admin_approval_test", "short_pwd_", "unique_email_",
                        "superadmin@arshithgroup.com", "director.external@gmail.com"
                    ])
                )
            ]
    _save_local_db(db)


@pytest.fixture(scope="module", autouse=True)
def setup_test_accounts():
    """Seed test accounts in Firestore to verify all login and approval cases."""
    cleanup_test_data()

    # 1. Approved employee
    FirestoreService.save("users", "test_user_approved", {
        "id": "test_user_approved",
        "email": EXISTING_APPROVED_EMAIL,
        "hashed_password": get_password_hash(EXISTING_APPROVED_PASS),
        "role": "employee",
        "is_active": True,
        "approval_status": "APPROVED",
    })
    FirestoreService.save("employees", EXISTING_APPROVED_EID, {
        "id": "test_user_approved",
        "employee_id": EXISTING_APPROVED_EID,
        "employeeId": EXISTING_APPROVED_EID,
        "full_name": "Approved Employee",
        "email": EXISTING_APPROVED_EMAIL,
        "status": "Active",
        "role": "Employee",
        "department": "Operations",
    })

    # 2. Pending employee
    FirestoreService.save("users", "test_user_pending", {
        "id": "test_user_pending",
        "email": PENDING_EMAIL,
        "hashed_password": get_password_hash(PENDING_PASS),
        "role": "employee",
        "is_active": False,
        "approval_status": "PENDING",
    })
    FirestoreService.save("employees", PENDING_EID, {
        "id": "test_user_pending",
        "employee_id": PENDING_EID,
        "employeeId": PENDING_EID,
        "full_name": "Pending Employee",
        "email": PENDING_EMAIL,
        "status": "pending",
        "role": "Employee",
    })

    # 3. Rejected employee
    FirestoreService.save("users", "test_user_rejected", {
        "id": "test_user_rejected",
        "email": REJECTED_EMAIL,
        "hashed_password": get_password_hash(REJECTED_PASS),
        "role": "employee",
        "is_active": False,
        "approval_status": "REJECTED",
        "rejection_reason": "Incomplete verification documents",
    })

    # 4. Inactive employee
    FirestoreService.save("users", "test_user_inactive", {
        "id": "test_user_inactive",
        "email": INACTIVE_EMAIL,
        "hashed_password": get_password_hash(INACTIVE_PASS),
        "role": "employee",
        "is_active": False,
        "approval_status": "APPROVED",
    })

    # 5. Authorized Administrator with company domain (@arshithgroup.com)
    FirestoreService.save("users", "test_admin_company", {
        "id": "test_admin_company",
        "email": "superadmin@arshithgroup.com",
        "hashed_password": get_password_hash("AdminPass123!"),
        "role": "admin",
        "name": "Super Admin",
        "is_active": True,
        "approval_status": "APPROVED",
    })

    # 6. Authorized Administrator with non-company domain (@gmail.com)
    FirestoreService.save("users", "test_admin_external", {
        "id": "test_admin_external",
        "email": "director.external@gmail.com",
        "hashed_password": get_password_hash("AdminPass123!"),
        "role": "admin",
        "name": "External Director",
        "is_active": True,
        "approval_status": "APPROVED",
    })

    yield

    cleanup_test_data()


# ============================================================================
# 1. REGISTRATION TESTS (15 SCENARIOS)
# ============================================================================

import time

UNIQUE_TS = str(int(time.time()))[-5:]


def test_reg_01_valid_company_email_and_valid_details():
    """1. Valid company email and valid details: Succeeds in PENDING state."""
    eid = f"AFI-R1{UNIQUE_TS}"
    email = f"new_hire_1{UNIQUE_TS}@arshithgroup.com"
    payload = {
        "fullName": "New Hire 101",
        "employeeId": eid,
        "email": email,
        "phone": f"98761{UNIQUE_TS}",
        "password": "StrongPassword123",
        "confirmPassword": "StrongPassword123",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "PENDING"
    assert "awaiting admin approval" in data["message"].lower()


def test_reg_02_gmail_address_rejected():
    """2. Gmail address: Reject with exact company email message."""
    payload = {
        "fullName": "Gmail User",
        "employeeId": "AFI-REG-102",
        "email": "ameen@gmail.com",
        "phone": "9876543211",
        "password": "StrongPassword123",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 400
    err_json = res.json()
    assert "Please use your company email ending with @arshithgroup.com." in (err_json.get("detail") or err_json.get("errors", {}).get("email"))


def test_reg_03_yahoo_address_rejected():
    """3. Yahoo address: Reject with exact company email message."""
    payload = {
        "fullName": "Yahoo User",
        "employeeId": "AFI-REG-103",
        "email": "ameen@yahoo.com",
        "phone": "9876543212",
        "password": "StrongPassword123",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 400
    err_json = res.json()
    assert "Please use your company email ending with @arshithgroup.com." in (err_json.get("detail") or err_json.get("errors", {}).get("email"))


def test_reg_04_incorrect_company_domain_rejected():
    """4. Incorrect company domain (@arshithgroup.co or @othercompany.com): Reject."""
    for bad_email in ["ameen@arshithgroup.co", "ameen@othercompany.com"]:
        payload = {
            "fullName": "Bad Domain User",
            "employeeId": "AFI-REG-104",
            "email": bad_email,
            "phone": "9876543213",
            "password": "StrongPassword123",
        }
        res = client.post("/api/auth/register", json=payload)
        assert res.status_code == 400
        err_json = res.json()
        assert "Please use your company email ending with @arshithgroup.com." in (err_json.get("detail") or err_json.get("errors", {}).get("email"))


def test_reg_05_email_company_domain_invalid_position_rejected():
    """5. Email containing company domain in invalid position: Reject."""
    payload = {
        "fullName": "Domain Position User",
        "employeeId": "AFI-REG-105",
        "email": "ameen@arshithgroup.com.example.com",
        "phone": "9876543214",
        "password": "StrongPassword123",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 400
    err_json = res.json()
    assert "Please use your company email ending with @arshithgroup.com." in (err_json.get("detail") or err_json.get("errors", {}).get("email"))


def test_reg_06_employee_id_without_afi_prefix_rejected():
    """6. Employee ID without AFI prefix (e.g. 12345, EMP123): Reject."""
    for bad_id in ["12345", "EMP123"]:
        payload = {
            "fullName": "Bad Prefix User",
            "employeeId": bad_id,
            "email": "valid_user_06@arshithgroup.com",
            "phone": "9876543215",
            "password": "StrongPassword123",
        }
        res = client.post("/api/auth/register", json=payload)
        assert res.status_code == 400
        err_json = res.json()
        assert "Employee ID must start with AFI." in (err_json.get("detail") or err_json.get("errors", {}).get("employeeId"))


def test_reg_07_employee_id_lowercase_prefix_rejected():
    """7. Employee ID using lowercase prefix (afi12345): Reject."""
    payload = {
        "fullName": "Lowercase Prefix User",
        "employeeId": "afi12345",
        "email": "valid_user_07@arshithgroup.com",
        "phone": "9876543216",
        "password": "StrongPassword123",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 400
    err_json = res.json()
    assert "Employee ID must start with AFI." in (err_json.get("detail") or err_json.get("errors", {}).get("employeeId"))


def test_reg_08_duplicate_employee_id_rejected():
    """8. Duplicate employee ID: Reject with exact message."""
    payload = {
        "fullName": "Duplicate ID User",
        "employeeId": EXISTING_APPROVED_EID,
        "email": "unique_email_08@arshithgroup.com",
        "phone": "9876543217",
        "password": "StrongPassword123",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 409
    err_json = res.json()
    msg = err_json.get("detail") or err_json.get("errors", {}).get("employeeId") or err_json.get("errors", {}).get("employee_id")
    assert "This employee ID is already registered. Please check your details or contact HR." in msg


def test_reg_09_duplicate_company_email_rejected():
    """9. Duplicate company email: Reject with exact message."""
    payload = {
        "fullName": "Duplicate Email User",
        "employeeId": "AFI-REG-109",
        "email": EXISTING_APPROVED_EMAIL,
        "phone": "9876543218",
        "password": "StrongPassword123",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 409
    err_json = res.json()
    msg = err_json.get("detail") or err_json.get("errors", {}).get("email")
    assert "An account with this company email already exists. Please log in or contact HR." in msg


def test_reg_10_password_fewer_than_8_chars_rejected():
    """10. Password containing fewer than 8 characters: Reject."""
    payload = {
        "fullName": "Short Password User",
        "employeeId": "AFI-REG-110",
        "email": "short_pwd_110@arshithgroup.com",
        "phone": "9876543219",
        "password": "pass123",  # 7 chars
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 400
    err_json = res.json()
    assert "Password must contain at least 8 characters." in (err_json.get("detail") or err_json.get("errors", {}).get("password"))


def test_reg_11_password_exactly_8_chars_accepted():
    """11. Password containing exactly 8 characters: Accepted."""
    payload = {
        "fullName": "Eight Char User",
        "employeeId": f"AFI-R2{UNIQUE_TS}",
        "email": f"eight_pwd_2{UNIQUE_TS}@arshithgroup.com",
        "phone": f"98762{UNIQUE_TS}",
        "password": "pass1234",  # exactly 8 chars
        "confirmPassword": "pass1234",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 201


def test_reg_12_empty_required_fields_rejected():
    """12. Empty required fields: Specific messages for each field."""
    # Missing name
    res1 = client.post("/api/auth/register", json={
        "fullName": "",
        "employeeId": f"AFI-R4{UNIQUE_TS}",
        "email": f"field_test1_{UNIQUE_TS}@arshithgroup.com",
        "phone": f"98764{UNIQUE_TS}",
        "password": "Password123",
    })
    assert res1.status_code == 400
    assert "Please enter your full name." in (res1.json().get("detail") or res1.json().get("errors", {}).get("fullName"))

    # Missing employee ID
    res2 = client.post("/api/auth/register", json={
        "fullName": "Missing EID User",
        "employeeId": "",
        "email": f"field_test2_{UNIQUE_TS}@arshithgroup.com",
        "phone": f"98765{UNIQUE_TS}",
        "password": "Password123",
    })
    assert res2.status_code == 400
    assert "Please enter your employee ID." in (res2.json().get("detail") or res2.json().get("errors", {}).get("employeeId"))

    # Missing email
    res3 = client.post("/api/auth/register", json={
        "fullName": "Missing Email User",
        "employeeId": f"AFI-R6{UNIQUE_TS}",
        "email": "",
        "phone": f"98766{UNIQUE_TS}",
        "password": "Password123",
    })
    assert res3.status_code == 400
    assert "Please enter your company email address." in (res3.json().get("detail") or res3.json().get("errors", {}).get("email"))

    # Missing password
    res4 = client.post("/api/auth/register", json={
        "fullName": "Missing Pwd User",
        "employeeId": f"AFI-R7{UNIQUE_TS}",
        "email": f"field_test4_{UNIQUE_TS}@arshithgroup.com",
        "phone": f"98767{UNIQUE_TS}",
        "password": "",
    })
    assert res4.status_code == 400
    assert "Please enter your password." in (res4.json().get("detail") or res4.json().get("errors", {}).get("password"))


def test_reg_13_invalid_phone_number_rejected():
    """13. Invalid phone number (fewer than 10 digits or non-numeric): Reject."""
    for bad_phone in ["123", "abcdef", ""]:
        payload = {
            "fullName": "Bad Phone User",
            "employeeId": f"AFI-R8{UNIQUE_TS}",
            "email": f"bad_phone_8{UNIQUE_TS}@arshithgroup.com",
            "phone": bad_phone,
            "password": "Password123",
        }
        res = client.post("/api/auth/register", json=payload)
        assert res.status_code == 400
        assert "Please enter a valid phone number." in (res.json().get("detail") or res.json().get("errors", {}).get("phone"))


def test_reg_14_confirm_password_mismatch_rejected():
    """14. Mismatched confirm password rejected with 'Passwords do not match.'"""
    payload = {
        "fullName": "Mismatch Pwd User",
        "employeeId": f"AFI-R9{UNIQUE_TS}",
        "email": f"mismatch_pwd_9{UNIQUE_TS}@arshithgroup.com",
        "phone": f"98769{UNIQUE_TS}",
        "password": "Password123",
        "confirmPassword": "DifferentPassword123",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 400
    assert "Passwords do not match." in (res.json().get("detail") or res.json().get("errors", {}).get("confirmPassword"))


def test_reg_15_registration_requiring_admin_approval():
    """15. Registration creates pending account requiring admin approval; cannot login yet."""
    eid = f"AFI-R3{UNIQUE_TS}"
    email = f"admin_approval_3{UNIQUE_TS}@arshithgroup.com"
    pwd = "ApprovalPass123"
    reg_res = client.post("/api/auth/register", json={
        "fullName": "Admin Approval Test",
        "employeeId": eid,
        "email": email,
        "phone": f"98763{UNIQUE_TS}",
        "password": pwd,
        "confirmPassword": pwd,
    })
    assert reg_res.status_code == 201

    # Attempt login while in PENDING status
    login_res = client.post("/api/auth/login", json={"email": email, "password": pwd})
    assert login_res.status_code == 403
    assert login_res.json()["detail"] == "Your registration is awaiting admin approval. You can log in after your account is approved."


# ============================================================================
# 2. LOGIN TESTS (9 SCENARIOS)
# ============================================================================

def test_login_01_valid_registered_and_approved_employee():
    """1. Valid registered and approved employee: 200 OK with token."""
    res = client.post("/api/auth/login", json={
        "email": EXISTING_APPROVED_EMAIL,
        "password": EXISTING_APPROVED_PASS,
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "employee"
    assert data["user"]["email"] == EXISTING_APPROVED_EMAIL


def test_login_02_employee_who_has_never_registered():
    """2. Employee who has never registered: 404 with exact unregistered message."""
    res = client.post("/api/auth/login", json={
        "email": "never_registered_employee_999@arshithgroup.com",
        "password": "Password123",
    })
    assert res.status_code == 404
    assert res.json()["detail"] == "You are not registered with Arshith Connect. Please register using your company email or contact HR."


def test_login_03_registered_employee_incorrect_password():
    """3. Registered employee with incorrect password: 401 with authentication error."""
    res = client.post("/api/auth/login", json={
        "email": EXISTING_APPROVED_EMAIL,
        "password": "WrongPassword999",
    })
    assert res.status_code == 401
    assert "Invalid employee email or password." in res.json()["detail"]
    assert "not registered" not in res.json()["detail"].lower()


def test_login_04_pending_employee_blocked():
    """4. Pending employee: 403 awaiting approval message."""
    res = client.post("/api/auth/login", json={
        "email": PENDING_EMAIL,
        "password": PENDING_PASS,
    })
    assert res.status_code == 403
    assert res.json()["detail"] == "Your registration is awaiting admin approval. You can log in after your account is approved."


def test_login_05_rejected_or_disabled_employee():
    """5. Rejected or disabled employee: 403 inactive / rejection message."""
    # Rejected employee
    res_rej = client.post("/api/auth/login", json={
        "email": REJECTED_EMAIL,
        "password": REJECTED_PASS,
    })
    assert res_rej.status_code == 403
    assert "Your registration request was not approved" in res_rej.json()["detail"]

    # Inactive employee
    res_inact = client.post("/api/auth/login", json={
        "email": INACTIVE_EMAIL,
        "password": INACTIVE_PASS,
    })
    assert res_inact.status_code == 403
    assert "Your account is currently inactive" in res_inact.json()["detail"]


def test_login_06_invalid_email_domain():
    """6. Invalid email domain: 400 with company domain guidance."""
    for bad_email in ["ameen@gmail.com", "ameen@yahoo.com", "ameen@other.com", "ameen@arshithgroup.co"]:
        res = client.post("/api/auth/login", json={
            "email": bad_email,
            "password": "Password123",
        })
        assert res.status_code == 400
        assert res.json()["detail"] == "Please use your company email ending with @arshithgroup.com."


def test_login_07_missing_email_or_password():
    """7. Missing email or password: 400 with missing credentials message."""
    # Empty email
    res1 = client.post("/api/auth/login", json={"email": "", "password": "Password123"})
    assert res1.status_code == 400
    assert res1.json()["detail"] == "Please enter your company email and password."

    # Empty password
    res2 = client.post("/api/auth/login", json={"email": "ameen@arshithgroup.com", "password": ""})
    assert res2.status_code == 400
    assert res2.json()["detail"] == "Please enter your company email and password."

    # Both empty
    res3 = client.post("/api/auth/login", json={"email": "", "password": ""})
    assert res3.status_code == 400
    assert res3.json()["detail"] == "Please enter your company email and password."


def test_login_08_admin_credentials_on_employee_login():
    """8. Admin credentials used on employee login: 403 with guidance to Admin Login page."""
    res = client.post("/api/auth/login", json={
        "email": "admin@arshith.com",
        "password": "AdminPassword@123",
    })
    assert res.status_code == 403
    assert "Admin credentials cannot be used to log in through Employee Login." in res.json()["detail"]


def test_login_09_unauthorized_attempt_to_access_protected_api():
    """9. Unauthorized attempt to access protected employee API without token: 401."""
    res = client.get("/api/auth/me")
    assert res.status_code in (401, 403)


# ============================================================================
# 3. ADMIN PORTAL VALIDATION & AUTHENTICATION TESTS
# ============================================================================

def test_admin_01_authorized_admin_with_company_domain_login():
    """Admin logs in using @arshithgroup.com company address — works normally."""
    res = client.post("/api/auth/admin-login", json={
        "email": "superadmin@arshithgroup.com",
        "password": "AdminPass123!",
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "admin"
    assert data["user"]["email"] == "superadmin@arshithgroup.com"


def test_admin_02_authorized_admin_with_non_company_domain_login():
    """Admin logs in using a valid non-company email address (@gmail.com) — not blocked by domain restriction."""
    res = client.post("/api/auth/admin-login", json={
        "email": "director.external@gmail.com",
        "password": "AdminPass123!",
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "admin"
    assert data["user"]["email"] == "director.external@gmail.com"


def test_admin_03_authorized_admin_with_arshith_com_domain_login():
    """Admin logs in using default designated address (admin@arshith.com) — succeeds with admin role."""
    res = client.post("/api/auth/admin-login", json={
        "email": "admin@arshith.com",
        "password": "AdminPassword@123",
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "admin"
    assert data["user"]["email"] == "admin@arshith.com"


def test_admin_04_admin_login_with_invalid_credentials():
    """Admin logs in with wrong password — rejected with 401 Invalid administrator credentials."""
    res = client.post("/api/auth/admin-login", json={
        "email": "director.external@gmail.com",
        "password": "WrongAdminPassword999",
    })
    assert res.status_code == 401
    assert "Invalid administrator credentials" in res.json()["detail"]


def test_admin_05_unauthorized_user_non_company_email_blocked_from_admin():
    """Unauthorized user with arbitrary non-company email cannot access admin login — 401 rejected."""
    res = client.post("/api/auth/admin-login", json={
        "email": "unauthorized.stranger@gmail.com",
        "password": "Password123!",
    })
    assert res.status_code in (401, 403)


def test_admin_06_employee_credentials_blocked_from_admin_login():
    """Employee credentials cannot log in via Admin Login — returns 403 with redirection guidance."""
    res = client.post("/api/auth/admin-login", json={
        "email": EXISTING_APPROVED_EMAIL,
        "password": EXISTING_APPROVED_PASS,
    })
    assert res.status_code == 403
    assert "Employee credentials cannot be used to log in through Admin Login." in res.json()["detail"]


def test_admin_07_unauthorized_access_to_admin_portal_api_blocked():
    """Unauthorized requests without admin role cannot access Admin Portal endpoints."""
    # 1. No token
    res_no_token = client.get("/api/registration-requests")
    assert res_no_token.status_code in (401, 403)

    # 2. Employee token accessing admin endpoint
    emp_login = client.post("/api/auth/login", json={
        "email": EXISTING_APPROVED_EMAIL,
        "password": EXISTING_APPROVED_PASS,
    })
    emp_token = emp_login.json()["access_token"]
    res_emp = client.get(
        "/api/registration-requests",
        headers={"Authorization": f"Bearer {emp_token}"},
    )
    assert res_emp.status_code == 403
    assert "Administrative privileges required" in res_emp.json()["detail"]

    # 3. Authorized Admin with non-company email accessing admin endpoint
    admin_login = client.post("/api/auth/admin-login", json={
        "email": "director.external@gmail.com",
        "password": "AdminPass123!",
    })
    admin_token = admin_login.json()["access_token"]
    res_admin = client.get(
        "/api/registration-requests",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_admin.status_code == 200


def test_admin_08_company_admin_blocked_from_employee_login():
    """Admin with @arshithgroup.com domain cannot log in through Employee Login — 403 guidance returned."""
    res = client.post("/api/auth/login", json={
        "email": "superadmin@arshithgroup.com",
        "password": "AdminPass123!",
    })
    assert res.status_code == 403
    assert "Admin credentials cannot be used to log in through Employee Login." in res.json()["detail"]
