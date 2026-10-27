import json
import logging
from datetime import date, datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.services.firestore_service import FirestoreService, firestore_service

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class MarkReadRequest(BaseModel):
    module: str  # "announcements" | "meetings" | "assignments" | "leaves"
    ids: Optional[List[str]] = None
    leaveDecisions: Optional[Dict[str, str]] = None  # { leaveId: status }


def _get_employee_meta(current_user) -> tuple:
    """Helper to extract employee identifiers from current_user."""
    emp_id = getattr(current_user, "employee_id", None) or getattr(current_user, "employeeId", None) or ""
    emp_email = getattr(current_user, "email", "")
    emp_uid = str(getattr(current_user, "uid", None) or getattr(current_user, "id", None) or "")
    emp_name = str(getattr(current_user, "name", None) or getattr(current_user, "full_name", None) or "").strip().lower()

    if not emp_id and emp_email:
        emps = FirestoreService.query("employees", {"email": emp_email})
        if emps:
            emp_id = emps[0].get("employee_id") or emps[0].get("id") or ""
            if not emp_name:
                emp_name = str(emps[0].get("full_name") or emps[0].get("name") or "").strip().lower()

    return str(emp_id), str(emp_email), str(emp_uid), str(emp_name)


def _get_read_state(emp_key: str) -> dict:
    """Load persistent read notification state for this employee from Firestore."""
    if not emp_key:
        return {"read_announcements": [], "seen_meetings": [], "seen_assignments": [], "seen_leave_decisions": {}}
    
    doc = FirestoreService.get_by_id("employee_notifications", emp_key)
    if not doc:
        return {"read_announcements": [], "seen_meetings": [], "seen_assignments": [], "seen_leave_decisions": {}}
    
    return {
        "read_announcements": list(doc.get("read_announcements", [])),
        "seen_meetings": list(doc.get("seen_meetings", [])),
        "seen_assignments": list(doc.get("seen_assignments", [])),
        "seen_leave_decisions": dict(doc.get("seen_leave_decisions", {})),
    }


def _save_read_state(emp_key: str, state: dict):
    """Persist read notification state for this employee to Firestore."""
    if not emp_key:
        return
    now_iso = datetime.now(timezone.utc).isoformat()
    state["updated_at"] = now_iso
    FirestoreService.save("employee_notifications", emp_key, state)


@router.get("/unread-summary", response_model=dict)
def get_unread_summary(
    current_user=Depends(get_current_user),
):
    """Calculate authentic employee-specific unread counts for Quick Actions badges."""
    user_role = getattr(current_user, "role", "employee")
    emp_id, emp_email, emp_uid, emp_name = _get_employee_meta(current_user)
    emp_key = emp_id or emp_uid or emp_email

    today_iso = date.today().isoformat()
    read_state = _get_read_state(emp_key)
    read_anns = set(read_state["read_announcements"])
    seen_mtgs = set(read_state["seen_meetings"])
    seen_asgs = set(read_state["seen_assignments"])
    seen_lvs = dict(read_state["seen_leave_decisions"])

    # 1. Announcements
    all_announcements = FirestoreService.list_all("announcements")
    if not all_announcements:
        all_announcements = FirestoreService.list_all("notifications")
    unread_ann_count = 0
    valid_ann_ids = []
    for a in all_announcements:
        is_act = a.get("is_active", True) if "is_active" in a else a.get("isActive", True)
        if not is_act:
            continue
        code = str(a.get("announcement_code") or a.get("id") or "")
        if not code:
            continue
        
        # Check audience
        recip_type = str(a.get("recipient_type") or a.get("recipientType") or "All Employees")
        if recip_type != "All Employees" and user_role != "admin":
            r_ids = a.get("recipient_ids") or a.get("recipientIds") or []
            if isinstance(r_ids, str):
                try:
                    r_ids = json.loads(r_ids)
                except Exception:
                    r_ids = [r_ids]
            if emp_id not in r_ids and emp_email not in r_ids and emp_uid not in r_ids:
                continue

        valid_ann_ids.append(code)
        if code not in read_anns:
            unread_ann_count += 1

    # 2. Meetings (Upcoming & Today only)
    all_meetings = FirestoreService.list_all("meetings")
    unread_mtg_count = 0
    valid_mtg_ids = []
    for m in all_meetings:
        code = str(m.get("meeting_code") or m.get("id") or "")
        m_date = str(m.get("date") or "")
        if not code or not m_date:
            continue
        # Only count upcoming or today's meetings
        if m_date < today_iso:
            continue

        recip_type = str(m.get("recipient_type") or m.get("recipientType") or "All Employees")
        if recip_type != "All Employees" and user_role != "admin":
            r_ids = m.get("recipient_ids") or m.get("recipientIds") or []
            if isinstance(r_ids, str):
                try:
                    r_ids = json.loads(r_ids)
                except Exception:
                    r_ids = [r_ids]
            if emp_id not in r_ids and emp_email not in r_ids and emp_uid not in r_ids:
                continue

        valid_mtg_ids.append(code)
        if code not in seen_mtgs:
            unread_mtg_count += 1

    # 3. Work Assignments (Active and assigned to employee/team)
    all_tasks = firestore_service.list_documents("assignments")
    all_teams = firestore_service.list_documents("teams")
    member_team_names = []
    member_team_ids = []
    for tm in all_teams:
        m_list = [str(x).strip().lower() for x in tm.get("members", [])]
        if emp_name in m_list or emp_id.lower() in m_list:
            member_team_names.append(str(tm.get("name", "")).strip().lower())
            member_team_ids.append(str(tm.get("id", "")))

    unread_asg_count = 0
    valid_asg_ids = []
    for t in all_tasks:
        code = str(t.get("task_code") or t.get("id") or "")
        if not code:
            continue
        status_val = str(t.get("status") or "In Progress").strip()
        if status_val.lower() == "completed":
            continue

        if user_role != "admin":
            assignee_str = str(t.get("assigned_to", "")).strip().lower()
            t_type = (t.get("assignment_type") or "Individual").capitalize()
            t_target = str(t.get("target_id", "")).strip()

            is_mine = False
            if t_type == "Individual":
                if (
                    t_target == emp_id
                    or assignee_str == emp_name
                    or assignee_str == emp_id.lower()
                    or assignee_str == emp_email.lower()
                ):
                    is_mine = True
            elif t_type == "Team":
                if t_target in member_team_ids or assignee_str in member_team_names:
                    is_mine = True
            else:
                if assignee_str == emp_name or assignee_str == emp_id.lower() or assignee_str in member_team_names:
                    is_mine = True

            if not is_mine:
                continue

        valid_asg_ids.append(code)
        if code not in seen_asgs:
            unread_asg_count += 1

    # 4. Leave Management Updates
    # An unread leave notification exists when an employee's leave has status "Approved" or "Rejected"
    # and the employee has not yet seen/acknowledged this decision.
    unread_leave_count = 0
    decided_leaves = []
    if emp_id or emp_uid:
        all_leaves = FirestoreService.query("leaves", {"employee_id": emp_id}) if emp_id else []
        cg_requests = FirestoreService.collection_group("requests")
        merged = {}
        for l in all_leaves:
            code = str(l.get("leave_code") or l.get("id") or "")
            if code:
                merged[code] = l
        for req in cg_requests:
            c_eid = str(req.get("employeeId") or req.get("employee_id") or "")
            if c_eid in [str(emp_id), str(emp_uid)]:
                req_id = str(req.get("id") or req.get("leave_code") or "")
                if req_id and req_id not in merged:
                    merged[req_id] = req

        for l_code, l_doc in merged.items():
            l_status = str(l_doc.get("status") or "Pending").strip().capitalize()
            if l_status in ["Approved", "Rejected"]:
                decided_leaves.append({
                    "id": l_code,
                    "status": l_status,
                    "reason": l_doc.get("reason", ""),
                    "rejection_remarks": l_doc.get("rejection_remarks") or l_doc.get("rejectionRemarks"),
                    "leave_type": l_doc.get("leave_type") or l_doc.get("leaveType"),
                })
                # Check if this status decision was seen
                ack_val = seen_lvs.get(l_code)
                if not ack_val or (ack_val != l_status and ack_val != "Acknowledged"):
                    unread_leave_count += 1

    return {
        "success": True,
        "employeeId": emp_id,
        "unread": {
            "announcements": unread_ann_count,
            "meetings": unread_mtg_count,
            "assignments": unread_asg_count,
            "leaves": unread_leave_count,
            "total": unread_ann_count + unread_mtg_count + unread_asg_count + unread_leave_count,
        },
        "readState": {
            "readAnnouncements": list(read_anns),
            "seenMeetings": list(seen_mtgs),
            "seenAssignments": list(seen_asgs),
            "seenLeaveDecisions": seen_lvs,
        },
        "decidedLeaves": decided_leaves,
    }


@router.post("/mark-read", response_model=dict)
def mark_notifications_read(
    payload: MarkReadRequest,
    current_user=Depends(get_current_user),
):
    """Mark announcements, meetings, assignments, or leaves as read/seen for the employee."""
    emp_id, emp_email, emp_uid, _ = _get_employee_meta(current_user)
    emp_key = emp_id or emp_uid or emp_email
    if not emp_key:
        raise HTTPException(status_code=400, detail="Cannot identify authenticated employee.")

    state = _get_read_state(emp_key)
    module = (payload.module or "").strip().lower()
    ids_to_add = [str(x) for x in (payload.ids or []) if str(x).strip()]

    if module in ["announcements", "announcement"]:
        current_set = set(state["read_announcements"])
        if not ids_to_add or "*" in ids_to_add or "all" in ids_to_add:
            all_a = FirestoreService.list_all("announcements")
            if not all_a:
                all_a = FirestoreService.list_all("notifications")
            for a in all_a:
                cid = str(a.get("announcement_code") or a.get("id") or "")
                if cid:
                    current_set.add(cid)
        else:
            current_set.update(ids_to_add)
        state["read_announcements"] = list(current_set)

    elif module in ["meetings", "meeting"]:
        current_set = set(state["seen_meetings"])
        if not ids_to_add or "*" in ids_to_add or "all" in ids_to_add:
            all_m = FirestoreService.list_all("meetings")
            for m in all_m:
                cid = str(m.get("meeting_code") or m.get("id") or "")
                if cid:
                    current_set.add(cid)
        else:
            current_set.update(ids_to_add)
        state["seen_meetings"] = list(current_set)

    elif module in ["assignments", "assignment", "work_assignments"]:
        current_set = set(state["seen_assignments"])
        if not ids_to_add or "*" in ids_to_add or "all" in ids_to_add:
            all_t = firestore_service.list_documents("assignments")
            for t in all_t:
                cid = str(t.get("task_code") or t.get("id") or "")
                if cid:
                    current_set.add(cid)
        else:
            current_set.update(ids_to_add)
        state["seen_assignments"] = list(current_set)

    elif module in ["leaves", "leave", "leave_management"]:
        decisions = state.get("seen_leave_decisions", {})
        if payload.leaveDecisions:
            for l_id, l_status in payload.leaveDecisions.items():
                decisions[str(l_id)] = str(l_status)
        if not ids_to_add or "*" in ids_to_add or "all" in ids_to_add:
            all_l = FirestoreService.query("leaves", {"employee_id": emp_id}) if emp_id else []
            for l in all_l:
                l_code = str(l.get("leave_code") or l.get("id") or "")
                l_status = str(l.get("status") or "").strip().capitalize()
                if l_code and l_status in ["Approved", "Rejected"]:
                    decisions[l_code] = l_status
        else:
            for l_id in ids_to_add:
                decisions[str(l_id)] = "Acknowledged"
        state["seen_leave_decisions"] = decisions

    _save_read_state(emp_key, state)
    return {"success": True, "module": module, "readState": state}
