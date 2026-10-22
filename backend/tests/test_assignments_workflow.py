import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.assignment import WorkAssignment
from app.models.employee import Employee
from app.models.team import Team, TeamMember
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
def cleanup_test_assignments():
    yield
    try:
        db = SessionLocal()
        try:
            db.query(WorkAssignment).filter(WorkAssignment.title.like("TEST_%")).delete(synchronize_session=False)
            db.query(Team).filter(Team.name.like("TEST_%")).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()
    except Exception:
        pass


def test_admin_creates_individual_work_assignment(admin_token, employee_token):
    """Admin delegates work to a specific employee in Individual mode."""
    from app.core.config import settings
    from app.services.firestore_service import FirestoreService

    emp_id = "AFI-001"
    emp_name = "Employee User"
    if settings.DATABASE_BACKEND == "firebase":
        emps = FirestoreService.query("employees", {"email": EMPLOYEE_EMAIL})
        if emps:
            emp_id = emps[0].get("employee_id") or emps[0].get("employeeId") or "AFI-001"
            emp_name = emps[0].get("full_name") or emps[0].get("name") or "Employee User"
    else:
        db = SessionLocal()
        emp = db.query(Employee).filter(Employee.email == EMPLOYEE_EMAIL).first()
        assert emp is not None
        emp_id = emp.employee_id
        emp_name = emp.full_name
        db.close()

    future_date = (date.today() + timedelta(days=7)).isoformat()
    payload = {
        "title": "TEST_Implement Microservice Health Probe",
        "description": "Add liveness and readiness probes to backend Kubernetes manifests.",
        "assignmentType": "Individual",
        "targetId": emp_id,
        "priority": "High",
        "deadline": future_date,
    }

    res = client.post(
        "/api/assignments",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "TEST_Implement Microservice Health Probe"
    assert data["assignmentType"] == "Individual"
    assert data["targetId"] == emp_id
    assert data["assignedTo"] == emp_name
    assert data["priority"] == "High"
    assert data["status"] == "In Progress"

    # Verify persisted in PostgreSQL
    db = SessionLocal()
    saved = db.query(WorkAssignment).filter(WorkAssignment.title == "TEST_Implement Microservice Health Probe").first()
    assert saved is not None
    assert saved.assignment_type == "Individual"
    assert saved.target_id == emp_id
    assert saved.assigned_to == emp_name
    assert saved.deadline == date.fromisoformat(future_date)
    db.close()

    # Employee GET list: targeted employee must see their assignment
    emp_res = client.get(
        "/api/assignments",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert emp_res.status_code == 200
    titles = [t["title"] for t in emp_res.json()]
    assert "TEST_Implement Microservice Health Probe" in titles


def test_admin_creates_team_work_assignment(admin_token, employee_token):
    """Admin delegates work to a team and team members can view it."""
    db = SessionLocal()
    emp = db.query(Employee).filter(Employee.email == EMPLOYEE_EMAIL).first()
    assert emp is not None

    # Create a test team with this employee enrolled
    test_team = Team(
        name="TEST_Backend Infrastructure Team",
        department="Engineering",
        description="Core infrastructure team",
        leader=emp.full_name,
    )
    db.add(test_team)
    db.commit()
    db.refresh(test_team)

    membership = TeamMember(team_id=test_team.id, employee_id=emp.employee_id)
    db.add(membership)
    db.commit()
    team_id = str(test_team.id)
    team_name = test_team.name
    db.close()

    future_date = (date.today() + timedelta(days=14)).isoformat()
    payload = {
        "title": "TEST_Upgrade Postgres Connection Pool",
        "description": "Configure async connection pooling and verify transaction limits.",
        "assignmentType": "Team",
        "targetId": team_id,
        "priority": "Medium",
        "deadline": future_date,
    }

    res = client.post(
        "/api/assignments",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "TEST_Upgrade Postgres Connection Pool"
    assert data["assignmentType"] == "Team"
    assert data["targetId"] == team_id
    assert data["assignedTo"] == team_name
    assert data["priority"] == "Medium"

    # Verify team member sees the assignment
    emp_res = client.get(
        "/api/assignments",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert emp_res.status_code == 200
    emp_titles = [t["title"] for t in emp_res.json()]
    assert "TEST_Upgrade Postgres Connection Pool" in emp_titles


def test_work_assignment_validations(admin_token):
    """Validates missing title, missing deadline, and invalid employee or team."""
    future_date = (date.today() + timedelta(days=3)).isoformat()

    # 1. Missing title
    res = client.post(
        "/api/assignments",
        json={"title": "  ", "deadline": future_date, "assignmentType": "Individual", "targetId": "AFI-001"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 400
    assert "work title" in res.json()["detail"].lower()

    # 2. Missing deadline
    res = client.post(
        "/api/assignments",
        json={"title": "Valid Title", "deadline": "", "assignmentType": "Individual", "targetId": "AFI-001"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 400
    assert "completion date" in res.json()["detail"].lower()

    # 3. Individual mode without employee
    res = client.post(
        "/api/assignments",
        json={"title": "Valid Title", "deadline": future_date, "assignmentType": "Individual", "targetId": ""},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 400
    assert "select an employee" in res.json()["detail"].lower()

    # 4. Individual mode with non-existent employee
    res = client.post(
        "/api/assignments",
        json={"title": "Valid Title", "deadline": future_date, "assignmentType": "Individual", "targetId": "NON-EXISTENT-EMP-999"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 400
    assert "not found" in res.json()["detail"].lower()

    # 5. Team mode without team
    res = client.post(
        "/api/assignments",
        json={"title": "Valid Title", "deadline": future_date, "assignmentType": "Team", "targetId": ""},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 400
    assert "select a team" in res.json()["detail"].lower()

    # 6. Team mode with non-existent team
    res = client.post(
        "/api/assignments",
        json={"title": "Valid Title", "deadline": future_date, "assignmentType": "Team", "targetId": "999999"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 400
    assert "not found" in res.json()["detail"].lower()


def test_progress_update_workflow(admin_token):
    """Admin or assignee updates progress and milestone marks completed when 100% reached."""
    db = SessionLocal()
    emp = db.query(Employee).first()
    assert emp is not None
    emp_id = emp.employee_id
    db.close()

    create_res = client.post(
        "/api/assignments",
        json={
            "title": "TEST_Performance Benchmarking",
            "deadline": (date.today() + timedelta(days=5)).isoformat(),
            "assignmentType": "Individual",
            "targetId": emp_id,
            "priority": "Low",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_res.status_code == 201
    task_id = create_res.json()["id"]

    # Update to 50%
    patch_res = client.patch(
        f"/api/assignments/{task_id}",
        json={"progress": 50},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["progress"] == 50
    assert patch_res.json()["status"] == "In Progress"

    # Update to 100% -> status becomes Completed
    patch_100 = client.patch(
        f"/api/assignments/{task_id}",
        json={"progress": 100},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert patch_100.status_code == 200
    assert patch_100.json()["progress"] == 100
    assert patch_100.json()["status"] == "Completed"


def test_non_admin_cannot_create_assignment(employee_token):
    """Non-admin employee must be rejected with 403 Forbidden."""
    res = client.post(
        "/api/assignments",
        json={"title": "TEST_Unauthorized Task", "deadline": "2026-11-01"},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert res.status_code == 403
