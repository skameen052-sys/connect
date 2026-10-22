import pytest
from datetime import date
from app.db.session import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User
from app.models.employee import Employee
from app.models.attendance import Attendance
from app.models.registration_request import RegistrationRequest


@pytest.fixture(scope="session", autouse=True)
def test_environment_fixture():
    """
    Session fixture: creates test employee credentials required by automated test suites,
    and cleans up all test fixtures when the test session completes.
    """
    test_email = "employee@arshith.com"
    test_id = "AFI-001"

    # Seed Firestore / local JSON if in Firebase mode
    try:
        from app.core.config import settings
        from app.services.firestore_service import FirestoreService
        if settings.DATABASE_BACKEND == "firebase":
            user_doc = {
                "id": "AFI-001",
                "email": test_email,
                "hashed_password": get_password_hash("Employee@123"),
                "role": "employee",
                "is_active": True,
                "approval_status": "APPROVED",
            }
            FirestoreService.save("users", "AFI-001", user_doc)
            emp_doc = {
                "id": "AFI-001",
                "employee_id": test_id,
                "employeeId": test_id,
                "full_name": "Employee User",
                "name": "Employee User",
                "email": test_email,
                "phone": "9876543210",
                "department": "Operations",
                "designation": "Operations Associate",
                "status": "Active",
                "shift": "General (09:30 AM - 06:30 PM)",
                "location": "HQ Office",
            }
            FirestoreService.save("employees", test_id, emp_doc)
    except Exception:
        pass

    # Setup test employee for PostgreSQL tests if available
    try:
        with SessionLocal() as db:
            user = db.query(User).filter(User.email == test_email).first()
            if not user:
                user = User(
                    email=test_email,
                    hashed_password=get_password_hash("Employee@123"),
                    role="employee",
                    is_active=True,
                )
                db.add(user)
                db.flush()

            emp = db.query(Employee).filter(Employee.employee_id == test_id).first()
            if not emp:
                emp = Employee(
                    employee_id=test_id,
                    user_id=user.id,
                    full_name="Employee User",
                    email=test_email,
                    phone="9876543210",
                    department="Operations",
                    designation="Operations Associate",
                    status="Active",
                    shift="General (09:30 AM - 06:30 PM)",
                    location="HQ Office",
                )
                db.add(emp)
            db.commit()
    except Exception:
        pass

    yield

    # Teardown: Remove all temporary test users & test records after test session
    cleanup_emails = [
        "employee@arshith.com",
        "newhire@arshith.com",
        "rejectedhire@arshith.com",
        "test777@arshith.com",
        "another@arshith.com",
        "fail@arshith.com",
    ]
    cleanup_ids = ["AFI-001", "AFI-777", "AFI-888", "AFI-889", "AFI-999", "AFI-TEST-FAIL", "AFI-INACTIVE"]

    try:
        with SessionLocal() as db:
            # Clean test attendance
            db.query(Attendance).filter(Attendance.employee_id.in_(cleanup_ids)).delete(synchronize_session=False)

            # Clean test registration requests
            db.query(RegistrationRequest).filter(
                (RegistrationRequest.email.in_(cleanup_emails)) | (RegistrationRequest.employee_id.in_(cleanup_ids))
            ).delete(synchronize_session=False)

            # Clean test employees
            db.query(Employee).filter(
                (Employee.employee_id.in_(cleanup_ids)) | (Employee.email.in_(cleanup_emails))
            ).delete(synchronize_session=False)

            # Clean test users
            db.query(User).filter(User.email.in_(cleanup_emails)).delete(synchronize_session=False)

            db.commit()
    except Exception:
        pass
