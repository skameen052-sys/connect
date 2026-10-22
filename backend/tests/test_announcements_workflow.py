import pytest
import json
from datetime import date
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.announcement import Announcement
from app.models.employee import Employee
from app.models.user import User

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


@pytest.fixture(autouse=True)
def cleanup_test_announcements():
    yield
    try:
        db = SessionLocal()
        try:
            db.query(Announcement).filter(Announcement.title.like("TEST_%")).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()
    except Exception:
        pass


def test_admin_publishes_all_four_announcement_types(admin_token):
    """Admin can publish announcements with General, Important, Holiday, and Meeting types."""
    types = ["General", "Important", "Holiday", "Meeting"]

    for ann_type in types:
        payload = {
            "title": f"TEST_Notice {ann_type}",
            "message": f"This is an announcement of type {ann_type}.",
            "announcementType": ann_type,
            "priority": "High" if ann_type == "Important" else "Normal",
            "author": "Farook",
            "recipientType": "All Employees",
        }
        res = client.post(
            "/api/announcements",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["title"] == f"TEST_Notice {ann_type}"
        assert data["type"] == ann_type
        assert data["announcement_type"] == ann_type
        assert data["recipient_type"] == "All Employees"
        assert data["author"] == "Farook"

        # Verify in PostgreSQL
        db = SessionLocal()
        record = db.query(Announcement).filter(Announcement.title == f"TEST_Notice {ann_type}").first()
        assert record is not None
        assert record.announcement_type == ann_type
        assert record.recipient_type == "All Employees"
        db.close()


def test_admin_publishes_selected_members_announcement(admin_token, employee_token):
    """Selected Members announcement is persisted with recipient IDs and filtered for recipients."""
    db = SessionLocal()
    # Find employee's ID
    emp = db.query(Employee).filter(Employee.email == EMPLOYEE_EMAIL).first()
    assert emp is not None
    target_emp_id = emp.employee_id
    db.close()

    payload = {
        "title": "TEST_Selected Members Exclusive Briefing",
        "message": "Confidential update for designated staff members only.",
        "announcementType": "Important",
        "priority": "Urgent",
        "author": "Farook",
        "recipientType": "Selected Members",
        "recipients": [target_emp_id],
    }
    res = client.post(
        "/api/announcements",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "TEST_Selected Members Exclusive Briefing"
    assert data["recipient_type"] == "Selected Members"
    assert target_emp_id in data["recipients"]

    # Verify in DB
    db = SessionLocal()
    ann_db = db.query(Announcement).filter(Announcement.title == "TEST_Selected Members Exclusive Briefing").first()
    assert ann_db is not None
    assert ann_db.recipient_type == "Selected Members"
    assert ann_db.recipient_ids is not None
    saved_ids = json.loads(ann_db.recipient_ids)
    assert target_emp_id in saved_ids
    db.close()

    # Employee GET list: target employee MUST see it
    emp_res = client.get(
        "/api/announcements",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert emp_res.status_code == 200
    emp_announcements = emp_res.json()
    matched = [a for a in emp_announcements if a["title"] == "TEST_Selected Members Exclusive Briefing"]
    assert len(matched) == 1
    assert matched[0]["type"] == "Important"


def test_selected_members_hidden_from_unselected_employees(admin_token):
    """An announcement sent to Selected Members is hidden from non-targeted employees."""
    db = SessionLocal()
    # Find active employees not matching EMPLOYEE_EMAIL
    other_emp = db.query(Employee).filter(Employee.email != EMPLOYEE_EMAIL, Employee.status == "Active").first()
    if not other_emp:
        # Create a mock employee ID if only 1 employee exists
        pytest.skip("Only one employee in DB; audience exclusion test requires at least 2")
    other_id = other_emp.employee_id
    db.close()

    payload = {
        "title": "TEST_Restricted To Other Staff",
        "message": "Only other staff should see this.",
        "announcementType": "Meeting",
        "priority": "Normal",
        "author": "Farook",
        "recipientType": "Selected Members",
        "recipients": [other_id],
    }
    res = client.post(
        "/api/announcements",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 201

    # Log in as normal test employee
    emp_login = client.post(
        "/api/auth/login",
        json={"email": EMPLOYEE_EMAIL, "password": EMPLOYEE_PASSWORD},
    )
    emp_token = emp_login.json()["access_token"]

    # Normal employee list announcements: should NOT see it
    res_list = client.get(
        "/api/announcements",
        headers={"Authorization": f"Bearer {emp_token}"},
    )
    assert res_list.status_code == 200
    titles = [a["title"] for a in res_list.json()]
    assert "TEST_Restricted To Other Staff" not in titles

    # Admin GET list: admin sees all announcements
    admin_list = client.get(
        "/api/announcements",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_list.status_code == 200
    admin_titles = [a["title"] for a in admin_list.json()]
    assert "TEST_Restricted To Other Staff" in admin_titles


def test_announcement_validation_failures(admin_token):
    """Validates missing title, missing message, invalid type, and empty recipients."""
    # 1. Missing Title
    res = client.post(
        "/api/announcements",
        json={"title": "   ", "message": "Content here", "announcementType": "General"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 400
    assert "title" in res.json()["detail"].lower()

    # 2. Missing Message
    res = client.post(
        "/api/announcements",
        json={"title": "Valid Title", "message": "   ", "announcementType": "General"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 400
    assert "message" in res.json()["detail"].lower()

    # 3. Invalid Announcement Type
    res = client.post(
        "/api/announcements",
        json={"title": "Valid Title", "message": "Valid Message", "announcementType": "UnrelatedCategory"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 400
    assert "invalid announcement type" in res.json()["detail"].lower()

    # 4. Selected Members with empty recipient list
    res = client.post(
        "/api/announcements",
        json={
            "title": "Valid Title",
            "message": "Valid Message",
            "announcementType": "General",
            "recipientType": "Selected Members",
            "recipients": [],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 400
    assert "select at least one employee" in res.json()["detail"].lower()

    # 5. Selected Members with non-existent employee ID
    res = client.post(
        "/api/announcements",
        json={
            "title": "Valid Title",
            "message": "Valid Message",
            "announcementType": "General",
            "recipientType": "Selected Members",
            "recipients": ["NON-EXISTENT-ID-9999"],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 400
    assert "valid registered active employees" in res.json()["detail"].lower()


def test_non_admin_cannot_publish_announcement(employee_token):
    """Non-admin employee must be denied with 403 Forbidden."""
    payload = {
        "title": "TEST_Rogue Employee Announcement",
        "message": "Should not be allowed.",
        "announcementType": "General",
    }
    res = client.post(
        "/api/announcements",
        json=payload,
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert res.status_code == 403
