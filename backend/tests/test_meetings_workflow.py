import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.meeting import Meeting
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
def cleanup_test_meetings():
    yield
    try:
        db = SessionLocal()
        try:
            db.query(Meeting).filter(Meeting.title.like("TEST_%")).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()
    except Exception:
        pass


def test_admin_schedules_meeting_all_employees(admin_token):
    """Admin schedules meeting with 'All Employees' audience."""
    future_date = (date.today() + timedelta(days=5)).isoformat()
    payload = {
        "title": "TEST_All Employees Strategy Briefing",
        "date": future_date,
        "startTime": "10:00",
        "endTime": "11:00",
        "organizer": "Farook",
        "room": "Boardroom A",
        "description": "Company-wide quarterly alignment meeting.",
        "recipientType": "All Employees",
    }
    res = client.post(
        "/api/meetings",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "TEST_All Employees Strategy Briefing"
    assert data["recipient_type"] == "All Employees"
    assert data["organizer"] == "Farook"
    assert data["organizer_id"] is not None
    assert data["status"] == "Scheduled"

    # Verify persisted in PostgreSQL
    db = SessionLocal()
    mtg = db.query(Meeting).filter(Meeting.title == "TEST_All Employees Strategy Briefing").first()
    assert mtg is not None
    assert mtg.recipient_type == "All Employees"
    assert mtg.recipient_ids is None
    db.close()


def test_admin_schedules_meeting_selected_members(admin_token):
    """Admin schedules meeting with 'Selected Members' audience and persists recipients."""
    future_date = (date.today() + timedelta(days=6)).isoformat()
    selected_emp_ids = ["AFI-001", "AFI-004"]

    payload = {
        "title": "TEST_Selected Members Sync",
        "date": future_date,
        "startTime": "14:00",
        "endTime": "15:00",
        "organizer": "Farook",
        "room": "https://meet.google.com/test-room",
        "description": "Project sync with select developers.",
        "recipientType": "Selected Members",
        "recipients": selected_emp_ids,
    }
    res = client.post(
        "/api/meetings",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["recipient_type"] == "Selected Members"
    assert "AFI-001" in data["recipient_ids"]
    assert "AFI-004" in data["recipient_ids"]
    assert data["attendees"] == 2

    # Verify persisted in DB
    db = SessionLocal()
    mtg = db.query(Meeting).filter(Meeting.title == "TEST_Selected Members Sync").first()
    assert mtg is not None
    assert mtg.recipient_type == "Selected Members"
    assert mtg.recipient_ids is not None
    db.close()


def test_selected_members_requires_at_least_one_employee(admin_token):
    """Validation: empty recipients in Selected Members mode must be rejected."""
    future_date = (date.today() + timedelta(days=7)).isoformat()
    payload = {
        "title": "TEST_Empty Members Fail",
        "date": future_date,
        "startTime": "10:00",
        "endTime": "11:00",
        "recipientType": "Selected Members",
        "recipients": [],
    }
    res = client.post(
        "/api/meetings",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 400
    assert "Please select at least one employee" in res.json()["detail"]


def test_invalid_date_in_past_rejected(admin_token):
    """Validation: past meeting dates must be rejected."""
    past_date = (date.today() - timedelta(days=2)).isoformat()
    payload = {
        "title": "TEST_Past Date Fail",
        "date": past_date,
        "startTime": "10:00",
        "endTime": "11:00",
        "recipientType": "All Employees",
    }
    res = client.post(
        "/api/meetings",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 400
    assert "Meeting date cannot be in the past" in res.json()["detail"]


def test_end_time_before_start_time_rejected(admin_token):
    """Validation: end time earlier than start time must be rejected."""
    future_date = (date.today() + timedelta(days=8)).isoformat()
    payload = {
        "title": "TEST_Invalid Time Fail",
        "date": future_date,
        "startTime": "15:00",
        "endTime": "14:00",
        "recipientType": "All Employees",
    }
    res = client.post(
        "/api/meetings",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 400
    assert "End time must be later than start time" in res.json()["detail"]


def test_empty_title_rejected(admin_token):
    """Validation: empty meeting title must be rejected."""
    future_date = (date.today() + timedelta(days=8)).isoformat()
    payload = {
        "title": "   ",
        "date": future_date,
        "startTime": "10:00",
        "endTime": "11:00",
        "recipientType": "All Employees",
    }
    res = client.post(
        "/api/meetings",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 400
    assert "Please enter a meeting title" in res.json()["detail"]


def test_employee_cannot_create_meeting(employee_token):
    """Security: employee user cannot schedule meetings."""
    future_date = (date.today() + timedelta(days=5)).isoformat()
    payload = {
        "title": "TEST_Unauthorized Create",
        "date": future_date,
        "startTime": "10:00",
        "endTime": "11:00",
        "recipientType": "All Employees",
    }
    res = client.post(
        "/api/meetings",
        json=payload,
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert res.status_code == 403


def test_employee_audience_filtering(admin_token, employee_token):
    """Audience filtering: Employee sees All Employees meetings, but not Selected Members meetings where they are not included."""
    future_date = (date.today() + timedelta(days=10)).isoformat()

    # 1. Meeting for All Employees
    res_all = client.post(
        "/api/meetings",
        json={
            "title": "TEST_Public All Employees Meeting",
            "date": future_date,
            "startTime": "10:00",
            "endTime": "11:00",
            "recipientType": "All Employees",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_all.status_code == 201

    # 2. Meeting for another employee (AFI-004 only)
    res_private = client.post(
        "/api/meetings",
        json={
            "title": "TEST_Private For AFI-004 Only",
            "date": future_date,
            "startTime": "11:00",
            "endTime": "12:00",
            "recipientType": "Selected Members",
            "recipients": ["AFI-004"],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_private.status_code == 201

    # Employee AFI-001 checks meetings
    emp_res = client.get("/api/meetings", headers={"Authorization": f"Bearer {employee_token}"})
    assert emp_res.status_code == 200
    emp_meetings = emp_res.json()
    titles = [m["title"] for m in emp_meetings]

    # Must see Public meeting, but MUST NOT see Private meeting for AFI-004
    assert "TEST_Public All Employees Meeting" in titles
    assert "TEST_Private For AFI-004 Only" not in titles
