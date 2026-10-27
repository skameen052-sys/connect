import json
import random
from datetime import date, datetime, timezone
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc

from app.core.config import settings
from app.db.session import get_db
from app.models.meeting import Meeting
from app.models.employee import Employee
from app.models.user import User
from app.schemas.meeting import MeetingCreate, MeetingUpdate, MeetingResponse
from app.dependencies.auth import get_current_user, get_current_admin
from app.services.firestore_service import FirestoreService

router = APIRouter(prefix="/meetings", tags=["Meetings"])


def format_meeting_response(m: Any) -> dict:
    if isinstance(m, dict):
        recipients_list = []
        r_ids = m.get("recipient_ids") or m.get("recipientIds") or m.get("recipients")
        if r_ids:
            if isinstance(r_ids, list):
                recipients_list = r_ids
            elif isinstance(r_ids, str):
                try:
                    recipients_list = json.loads(r_ids)
                except Exception:
                    recipients_list = [r.strip() for r in r_ids.split(",") if r.strip()]

        code = m.get("meeting_code") or m.get("id") or "MTG-001"
        return {
            "id": code,
            "meetingId": m.get("id", code),
            "title": m.get("title", "Meeting"),
            "date": str(m.get("date", "")),
            "time": m.get("time", ""),
            "start_time": m.get("start_time"),
            "startTime": m.get("start_time"),
            "end_time": m.get("end_time"),
            "endTime": m.get("end_time"),
            "duration": m.get("duration", "30 mins"),
            "organizer": m.get("organizer", "Administrator"),
            "organizer_id": m.get("organizer_id"),
            "organizerId": m.get("organizer_id"),
            "host": m.get("organizer", "Administrator"),
            "platform": m.get("platform", "Google Meet"),
            "link": m.get("link", "https://meet.google.com/new"),
            "attendees": m.get("attendees", 4),
            "description": m.get("description") or "General discussion.",
            "room": m.get("link") or "Virtual Room A",
            "status": m.get("status", "Scheduled"),
            "recipient_type": m.get("recipient_type", "All Employees"),
            "recipientType": m.get("recipient_type", "All Employees"),
            "recipient_ids": recipients_list,
            "recipientIds": recipients_list,
            "recipients": recipients_list,
        }

    recipients_list = []
    if m.recipient_ids:
        try:
            recipients_list = json.loads(m.recipient_ids)
        except Exception:
            recipients_list = [r.strip() for r in m.recipient_ids.split(",") if r.strip()]

    return {
        "id": m.meeting_code or f"MTG-{m.id:03d}",
        "meetingId": m.id,
        "title": m.title,
        "date": m.date.isoformat(),
        "time": m.time,
        "start_time": m.start_time,
        "startTime": m.start_time,
        "end_time": m.end_time,
        "endTime": m.end_time,
        "duration": m.duration,
        "organizer": m.organizer,
        "organizer_id": m.organizer_id,
        "organizerId": m.organizer_id,
        "host": m.organizer,
        "platform": m.platform,
        "link": m.link,
        "attendees": m.attendees,
        "description": m.description or "General discussion.",
        "room": m.link or "Virtual Room A",
        "status": m.status,
        "recipient_type": m.recipient_type or "All Employees",
        "recipientType": m.recipient_type or "All Employees",
        "recipient_ids": recipients_list,
        "recipientIds": recipients_list,
        "recipients": recipients_list,
    }


@router.get("", response_model=List[dict])
def list_meetings(
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List scheduled meetings (Admins see all; employees see eligible meetings)."""
    user_role = getattr(current_user, "role", "employee")
    user_email = getattr(current_user, "email", "")
    user_id = getattr(current_user, "id", None)

    if settings.DATABASE_BACKEND == "firebase":
        all_meetings = FirestoreService.list_all("meetings")
        filtered = []

        emp_id = ""
        if user_role != "admin":
            emps = FirestoreService.query("employees", {"email": user_email})
            if emps:
                emp_id = emps[0].get("employee_id")

        for m in all_meetings:
            title = str(m.get("title", "")).lower()
            desc_str = str(m.get("description", "")).lower()
            org = str(m.get("organizer", "")).lower()
            st = str(m.get("status", "")).strip().lower()

            if search:
                s = search.strip().lower()
                if s not in title and s not in desc_str and s not in org:
                    continue

            if status_filter and status_filter != "ALL":
                if st != status_filter.strip().lower():
                    continue

            if user_role != "admin":
                recip_type = m.get("recipient_type", "All Employees")
                if recip_type != "All Employees":
                    r_ids = m.get("recipient_ids") or []
                    if isinstance(r_ids, str):
                        try:
                            r_ids = json.loads(r_ids)
                        except Exception:
                            r_ids = [r_ids]
                    if emp_id not in r_ids and user_email not in r_ids:
                        continue

            filtered.append(format_meeting_response(m))

        filtered.sort(key=lambda x: (str(x.get("date", "")), str(x.get("time", ""))))
        return filtered

    # PostgreSQL fallback
    query = db.query(Meeting)
    if search:
        s = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                Meeting.title.ilike(s),
                Meeting.description.ilike(s),
                Meeting.organizer.ilike(s),
            )
        )
    if status_filter and status_filter != "ALL":
        query = query.filter(Meeting.status.ilike(status_filter.strip()))

    all_meetings = query.order_by(asc(Meeting.date), asc(Meeting.time)).all()

    if current_user.role == "admin":
        return [format_meeting_response(m) for m in all_meetings]

    emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not emp:
        emp = db.query(Employee).filter(Employee.email == current_user.email).first()
    emp_id = emp.employee_id if emp else ""
    emp_email = emp.email if emp else current_user.email

    visible = []
    for m in all_meetings:
        if m.recipient_type == "All Employees" or not m.recipient_type:
            visible.append(m)
        elif m.recipient_ids:
            try:
                ids = json.loads(m.recipient_ids)
            except Exception:
                ids = [i.strip() for i in m.recipient_ids.split(",") if i.strip()]
            if emp_id in ids or emp_email in ids:
                visible.append(m)

    return [format_meeting_response(m) for m in visible]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=dict)
def create_meeting(
    data: MeetingCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Schedule a new company meeting (Admin only)."""
    user_role = getattr(current_user, "role", "employee")
    user_email = getattr(current_user, "email", "")
    user_id = getattr(current_user, "id", None)

    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required to schedule company meetings.",
        )

    if not data.title or not data.title.strip():
        raise HTTPException(status_code=400, detail="Please enter a meeting title.")

    try:
        m_date = date.fromisoformat(data.date.strip())
    except Exception:
        raise HTTPException(status_code=400, detail="Please select a valid meeting date.")

    s_time = (data.start_time or data.startTime or "").strip()
    e_time = (data.end_time or data.endTime or "").strip()
    if s_time and e_time:
        if s_time >= e_time:
            raise HTTPException(status_code=400, detail="End time must be later than start time.")
        final_time = f"{s_time} - {e_time}"
    else:
        final_time = (data.time or "").strip() or "10:00 AM - 11:00 AM"

    organizer = (data.organizer or "Administrator").strip()
    admin_id = "ADM-001"
    code = f"MTG-{int(datetime.now(timezone.utc).timestamp() * 1000) % 1000000}"
    now_iso = datetime.now(timezone.utc).isoformat()

    recip_type = (data.recipientType or data.recipient_type or "All Employees").strip()
    raw_recipients = data.recipients or data.recipient_ids or data.recipientIds
    if isinstance(raw_recipients, str):
        raw_recipients = [r.strip() for r in raw_recipients.split(",") if r.strip()]
    elif not isinstance(raw_recipients, list):
        raw_recipients = []

    if settings.DATABASE_BACKEND == "firebase":
        attendees_count = len(raw_recipients) if (recip_type != "All Employees" and raw_recipients) else len(FirestoreService.list_all("employees"))

        meeting_doc = {
            "id": code,
            "meeting_code": code,
            "title": data.title.strip(),
            "date": m_date.isoformat(),
            "time": final_time,
            "start_time": s_time or None,
            "end_time": e_time or None,
            "duration": data.duration or "30 mins",
            "organizer": organizer,
            "organizer_id": admin_id,
            "platform": data.platform or "Google Meet",
            "link": data.link or "https://meet.google.com/new",
            "attendees": attendees_count,
            "description": data.description.strip() if data.description else "General discussion.",
            "status": "Scheduled",
            "recipient_type": recip_type,
            "recipient_ids": raw_recipients if recip_type != "All Employees" else None,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        FirestoreService.save("meetings", code, meeting_doc)
        return format_meeting_response(meeting_doc)

    # PostgreSQL fallback
    attendees_count = db.query(Employee).filter(Employee.status == "Active").count() or 4
    meeting = Meeting(
        meeting_code=code,
        title=data.title.strip(),
        date=m_date,
        time=final_time,
        start_time=s_time or None,
        end_time=e_time or None,
        duration=data.duration or "30 mins",
        organizer=organizer,
        organizer_id=admin_id,
        platform=data.platform or "Google Meet",
        link=data.link or "https://meet.google.com/new",
        attendees=attendees_count,
        description=data.description.strip() if data.description else "General discussion.",
        status="Scheduled",
        recipient_type=recip_type,
        recipient_ids=json.dumps(raw_recipients) if raw_recipients else None,
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return format_meeting_response(meeting)


@router.patch("/{meeting_id}", response_model=dict)
def update_meeting(
    meeting_id: str,
    data: MeetingUpdate,
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin),
):
    """Update meeting details (Admin only)."""
    if settings.DATABASE_BACKEND == "firebase":
        m = FirestoreService.get_by_id("meetings", meeting_id)
        if not m:
            raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found.")
        updates = {}
        if data.title:
            updates["title"] = data.title.strip()
        if data.date:
            try:
                updates["date"] = date.fromisoformat(data.date).isoformat()
            except ValueError:
                pass
        if data.time:
            updates["time"] = data.time.strip()
        if data.platform:
            updates["platform"] = data.platform.strip()
        if data.link:
            updates["link"] = data.link.strip()
        if data.status:
            updates["status"] = data.status.strip()
        if data.description is not None:
            updates["description"] = data.description.strip()

        doc_key = m.get("meeting_code") or meeting_id
        FirestoreService.update("meetings", doc_key, updates)
        m.update(updates)
        return format_meeting_response(m)

    # PostgreSQL fallback
    meeting = (
        db.query(Meeting)
        .filter(
            (Meeting.meeting_code == meeting_id)
            | (Meeting.id == int(meeting_id) if meeting_id.isdigit() else False)
        )
        .first()
    )
    if not meeting:
        raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found.")

    if data.title:
        meeting.title = data.title.strip()
    if data.date:
        try:
            meeting.date = date.fromisoformat(data.date)
        except ValueError:
            pass
    if data.time:
        meeting.time = data.time.strip()
    if data.status:
        meeting.status = data.status.strip()

    db.commit()
    db.refresh(meeting)
    return format_meeting_response(meeting)


@router.delete("/{meeting_id}", status_code=status.HTTP_200_OK)
def delete_meeting(
    meeting_id: str,
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin),
):
    """Cancel and delete a scheduled meeting (Admin only)."""
    if settings.DATABASE_BACKEND == "firebase":
        m = FirestoreService.get_by_id("meetings", meeting_id)
        if not m:
            raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found.")
        doc_key = m.get("meeting_code") or meeting_id
        FirestoreService.delete("meetings", doc_key)
        return {"success": True, "message": "Meeting cancelled successfully."}

    meeting = (
        db.query(Meeting)
        .filter(
            (Meeting.meeting_code == meeting_id)
            | (Meeting.id == int(meeting_id) if meeting_id.isdigit() else False)
        )
        .first()
    )
    if not meeting:
        raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found.")

    db.delete(meeting)
    db.commit()
    return {"success": True, "message": "Meeting cancelled successfully."}
