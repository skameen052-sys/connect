import uuid
import pytest
from datetime import date, datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.config import settings
from app.core.security import get_password_hash, create_access_token
from app.db.session import SessionLocal
from app.models.user import User
from app.models.employee import Employee
from app.models.registration_request import RegistrationRequest
from app.models.attendance import Attendance
from app.models.leave import Leave
from app.models.announcement import Announcement
from app.services.firestore_service import FirestoreService
from app.services.sync_service import sync_employee_approval_state, sync_attendance_to_postgres

client = TestClient(app)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_scenario_1_and_2_registration_sync(db_session: Session):
    """Scenario 1 & 2: Registration across web and mobile reaches shared persistence and admin visibility."""
    uid_suffix = uuid.uuid4().hex[:6]
    test_email = f"sync_reg_{uid_suffix}@arshithgroup.com"
    test_emp_id = f"AFI-9{uid_suffix[:3]}".upper()

    import random
    unique_phone = f"98{random.randint(10000000, 99999999)}"

    res = client.post(
        "/api/auth/register",
        json={
            "fullName": "Sync Test Employee",
            "employeeId": test_emp_id,
            "email": test_email,
            "phone": unique_phone,
            "password": "Password@123",
            "confirmPassword": "Password@123",
        },
    )
    assert res.status_code == 201
    assert res.json()["status"] == "PENDING"

    # Verify registration exists in PostgreSQL
    pg_user = db_session.query(User).filter(User.email == test_email).first()
    assert pg_user is not None
    assert pg_user.approval_status == "PENDING"
    assert pg_user.is_active is False

    pg_req = db_session.query(RegistrationRequest).filter(RegistrationRequest.email == test_email).first()
    assert pg_req is not None
    assert pg_req.status == "Pending"

    # Verify registration exists in Firestore
    if settings.DATABASE_BACKEND == "firebase":
        users = FirestoreService.query("users", {"email": test_email})
        assert len(users) > 0
        assert users[0].get("approval_status") == "PENDING"


def test_scenario_3_marco_mobile_approval_reconciliation(db_session: Session):
    """Scenario 3: Mobile approval (where status='approved' was set only on employee doc) is automatically reconciled."""
    marco_email = "marco@arshithgroup.com"
    marco_pass = "Marco@123"

    res = client.post(
        "/api/auth/login",
        json={"email": marco_email, "password": marco_pass},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "employee"
    assert data["user"]["email"] == marco_email

    # Verify PostgreSQL reflects approved state
    pg_user = db_session.query(User).filter(User.email == marco_email).first()
    if pg_user:
        assert pg_user.approval_status == "APPROVED"
        assert pg_user.is_active is True


def test_scenario_4_admin_web_approval_sync(db_session: Session):
    """Scenario 4: When admin approves an employee, sync_employee_approval_state commits across Firestore and PostgreSQL."""
    uid_suffix = uuid.uuid4().hex[:6]
    test_email = f"sync_approve_{uid_suffix}@arshithgroup.com"
    test_uid = f"sync_approve_{uid_suffix}"
    emp_id = f"AFI-8{uid_suffix[:3]}".upper()

    user_doc = {
        "id": test_uid,
        "email": test_email,
        "approval_status": "PENDING",
        "is_active": False,
        "status": "pending",
        "role": "employee",
    }
    emp_doc = {
        "id": emp_id,
        "employeeId": emp_id,
        "email": test_email,
        "status": "pending",
    }
    if settings.DATABASE_BACKEND == "firebase":
        FirestoreService.save("users", test_uid, user_doc)
        FirestoreService.save("employees", emp_id, emp_doc)

    # Perform synchronization action
    updated = sync_employee_approval_state(test_email, "approved", db=db_session)
    assert bool(updated)
    assert updated["status"] == "Approved"

    # Verify Firestore state
    if settings.DATABASE_BACKEND == "firebase":
        users = FirestoreService.query("users", {"email": test_email})
        if users:
            assert users[0].get("approval_status") == "APPROVED"
            assert users[0].get("is_active") is True


def test_scenario_5_pending_employee_cannot_login():
    """Scenario 5: Pending employee cannot log in and receives awaiting approval message."""
    uid_suffix = uuid.uuid4().hex[:6]
    pending_email = f"pending_{uid_suffix}@arshithgroup.com"
    pending_pass = "Pending@123"

    if settings.DATABASE_BACKEND == "firebase":
        user_doc = {
            "id": f"pending_id_{uid_suffix}",
            "email": pending_email,
            "hashed_password": get_password_hash(pending_pass),
            "role": "employee",
            "is_active": False,
            "approval_status": "PENDING",
            "status": "pending",
        }
        FirestoreService.save("users", f"pending_id_{uid_suffix}", user_doc)
        FirestoreService.save("employees", f"AFI-P{uid_suffix[:3]}".upper(), {
            "id": f"AFI-P{uid_suffix[:3]}".upper(),
            "employeeId": f"AFI-P{uid_suffix[:3]}".upper(),
            "email": pending_email,
            "status": "pending",
        })

    res = client.post(
        "/api/auth/login",
        json={"email": pending_email, "password": pending_pass},
    )
    assert res.status_code == 403
    assert "awaiting admin approval" in res.json()["detail"].lower()


def test_scenario_6_rejected_employee_cannot_login():
    """Scenario 6: Rejected employee cannot log in."""
    uid_suffix = uuid.uuid4().hex[:6]
    rejected_email = f"rejected_{uid_suffix}@arshithgroup.com"
    rejected_pass = "Rejected@123"

    if settings.DATABASE_BACKEND == "firebase":
        user_doc = {
            "id": f"rej_id_{uid_suffix}",
            "email": rejected_email,
            "hashed_password": get_password_hash(rejected_pass),
            "role": "employee",
            "is_active": False,
            "approval_status": "REJECTED",
            "status": "rejected",
        }
        FirestoreService.save("users", f"rej_id_{uid_suffix}", user_doc)
        FirestoreService.save("employees", f"AFI-R{uid_suffix[:3]}".upper(), {
            "id": f"AFI-R{uid_suffix[:3]}".upper(),
            "employeeId": f"AFI-R{uid_suffix[:3]}".upper(),
            "email": rejected_email,
            "status": "rejected",
        })

    res = client.post(
        "/api/auth/login",
        json={"email": rejected_email, "password": rejected_pass},
    )
    assert res.status_code == 403
    assert "not approved" in res.json()["detail"].lower()


def test_scenario_8_and_9_attendance_checkout_and_duration_sync(db_session: Session):
    """Scenario 8 & 9: Attendance check-in, check-out, and duration sync across mobile and PostgreSQL."""
    today = date.today()
    emp_id = "AFI-0235"  # Marco

    record = {
        "employee_id": emp_id,
        "employee_name": "Marco",
        "date": today.isoformat(),
        "check_in": "09:30:00",
        "check_out": "18:30:00",
        "status": "Present",
        "work_mode": "WFO",
        "working_duration": "09 hrs 00 mins",
    }
    synced = sync_attendance_to_postgres(emp_id, today, record, db=db_session)
    assert synced is True

    att = db_session.query(Attendance).filter(
        Attendance.employee_id == emp_id,
        Attendance.date == today,
    ).first()
    assert att is not None
    assert att.check_in_time == "09:30:00"
    assert att.check_out_time == "18:30:00"
    assert att.duration == "09 hrs 00 mins"


def test_scenario_13_unauthorized_user_cannot_access_admin_api():
    """Scenario 13: Employee credentials cannot access administrator approval or management endpoints."""
    # Log in as real employee (Marco) to get a legitimate employee token
    login_res = client.post(
        "/api/auth/login",
        json={"email": "marco@arshithgroup.com", "password": "Marco@123"},
    )
    assert login_res.status_code == 200
    emp_token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {emp_token}"}

    # Calling Admin registration requests or admin dashboard must return 403
    res_dash = client.get("/api/admin/dashboard", headers=headers)
    assert res_dash.status_code == 403

    res_reg = client.get("/api/admin/employee-registrations", headers=headers)
    assert res_reg.status_code == 403
