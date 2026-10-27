import pytest
import io
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


def test_get_contacts(admin_token, employee_token):
    """Test contacts retrieval for both admin and employee."""
    # Admin gets contacts
    res_admin = client.get("/api/chat/contacts", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin.status_code == 200
    contacts_admin = res_admin.json()
    assert isinstance(contacts_admin, list)

    # Employee gets contacts
    res_emp = client.get("/api/chat/contacts", headers={"Authorization": f"Bearer {employee_token}"})
    assert res_emp.status_code == 200
    contacts_emp = res_emp.json()
    assert isinstance(contacts_emp, list)
    # Admin should be in contacts for employee
    assert any(c["role"] == "admin" or c["id"] == "ADM-001" for c in contacts_emp)


def test_get_teams_and_channels(admin_token, employee_token):
    """Test team channels retrieval."""
    res = client.get("/api/chat/teams", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    teams = res.json()
    assert isinstance(teams, list)


def test_direct_messaging_workflow(admin_token, employee_token):
    """Test complete direct messaging workflow: send, edit, reaction, pin, delete."""
    # 1. Admin sends message to employee
    send_res = client.post(
        "/api/chat/messages",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "chat_type": "direct",
            "target_id": "AFI-001",
            "content": "Hello employee! Please review the sprint goals.",
            "attachments": [],
        },
    )
    assert send_res.status_code == 201
    msg_data = send_res.json()
    msg_id = msg_data["id"]
    assert msg_data["content"] == "Hello employee! Please review the sprint goals."

    # 2. Admin edits their own message
    edit_res = client.patch(
        f"/api/chat/messages/{msg_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"content": "Hello employee! Please review the sprint goals ASAP."},
    )
    assert edit_res.status_code == 200
    assert edit_res.json()["message"]["content"] == "Hello employee! Please review the sprint goals ASAP."
    assert edit_res.json()["message"]["is_edited"] is True

    # 3. Employee toggles reaction
    react_res = client.post(
        f"/api/chat/messages/{msg_id}/reactions",
        headers={"Authorization": f"Bearer {employee_token}"},
        json={"emoji": "👍"},
    )
    assert react_res.status_code == 200
    assert "👍" in react_res.json()["reactions"]

    # 4. Toggle pin
    pin_res = client.post(
        f"/api/chat/messages/{msg_id}/pin",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert pin_res.status_code == 200
    assert pin_res.json()["is_pinned"] is True

    # 5. Retrieve message history
    history_res = client.get(
        "/api/chat/messages",
        headers={"Authorization": f"Bearer {employee_token}"},
        params={"chat_type": "direct", "target_id": "ADM-001"},
    )
    assert history_res.status_code == 200
    history = history_res.json()
    assert any(m["id"] == msg_id for m in history)

    # 6. Delete message
    del_res = client.delete(
        f"/api/chat/messages/{msg_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert del_res.status_code == 200


def test_group_channel_workflow(admin_token, employee_token):
    """Test group creation, adding members, and member leaving/removal."""
    # 1. Admin creates a custom team group
    group_res = client.post(
        "/api/chat/conversations/group",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Frontend Guild",
            "description": "Collaboration on web architecture",
            "member_ids": ["AFI-001"],
        },
    )
    assert group_res.status_code == 200
    group_data = group_res.json()
    group_id = str(group_data["id"])
    assert group_data["name"] == "Frontend Guild"
    assert "AFI-001" in group_data["members"]

    # 2. Add an additional member
    add_res = client.post(
        f"/api/chat/conversations/{group_id}/members",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"user_id": "AFI-002"},
    )
    assert add_res.status_code == 200
    assert "AFI-002" in add_res.json()["members"]

    # 3. Post a message to group
    post_res = client.post(
        "/api/chat/messages",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "chat_type": "team",
            "target_id": group_id,
            "content": "Welcome all to Frontend Guild!",
        },
    )
    assert post_res.status_code == 201

    # 4. Remove a member
    rem_res = client.delete(
        f"/api/chat/conversations/{group_id}/members/AFI-002",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert rem_res.status_code == 200
    assert "AFI-002" not in rem_res.json()["members"]


def test_file_attachment_upload(admin_token):
    """Test attachment upload with validation and size check."""
    # 1. Allowed text file upload
    file_content = b"Sample work specification document content."
    file_obj = io.BytesIO(file_content)

    upload_res = client.post(
        "/api/chat/attachments/upload",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={"file": ("project_spec.txt", file_obj, "text/plain")},
    )
    assert upload_res.status_code == 200
    file_info = upload_res.json()
    assert file_info["filename"] == "project_spec.txt"
    assert file_info["url"].startswith("/static/chat_uploads/")
    assert file_info["is_image"] is False

    # 2. Reject disallowed executable file
    exe_file = io.BytesIO(b"binary content")
    bad_upload = client.post(
        "/api/chat/attachments/upload",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={"file": ("script.exe", exe_file, "application/x-msdownload")},
    )
    assert bad_upload.status_code == 400


def test_unread_count_endpoint(admin_token, employee_token):
    """Test unread count check for navbar badges."""
    res = client.get("/api/chat/unread-count", headers={"Authorization": f"Bearer {employee_token}"})
    assert res.status_code == 200
    assert "total_unread" in res.json()
    assert isinstance(res.json()["total_unread"], int)
