import json
import random
from datetime import date, datetime, timezone
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from app.core.config import settings
from app.db.session import get_db
from app.models.announcement import Announcement
from app.models.employee import Employee
from app.models.user import User
from app.schemas.announcement import AnnouncementCreate, AnnouncementUpdate, AnnouncementResponse
from app.dependencies.auth import get_current_user, get_current_admin
from app.services.firestore_service import FirestoreService

router = APIRouter(prefix="/announcements", tags=["Announcements"])


def format_announcement_response(a: Any) -> dict:
    if isinstance(a, dict):
        r_ids = a.get("recipient_ids") or a.get("recipientIds") or a.get("recipients")
        if isinstance(r_ids, str):
            try:
                r_ids = json.loads(r_ids)
            except Exception:
                r_ids = [i.strip() for i in r_ids.split(",") if i.strip()]
        elif not isinstance(r_ids, list):
            r_ids = None

        ann_type = a.get("announcement_type") or a.get("announcementType") or a.get("type") or "General"
        recip_type = a.get("recipient_type") or a.get("recipientType") or "All Employees"
        code = a.get("announcement_code") or a.get("id") or "ANN-001"

        return {
            "id": code,
            "announcementId": a.get("id", code),
            "title": a.get("title", ""),
            "message": a.get("message", ""),
            "author": a.get("author", "Administrator"),
            "date": str(a.get("date", date.today().isoformat())),
            "priority": a.get("priority", "Normal"),
            "type": ann_type,
            "announcement_type": ann_type,
            "announcementType": ann_type,
            "recipient_type": recip_type,
            "recipientType": recip_type,
            "recipient_ids": r_ids,
            "recipientIds": r_ids,
            "recipients": r_ids,
            "isActive": a.get("is_active", True) if "is_active" in a else a.get("isActive", True),
        }

    r_ids = None
    if a.recipient_ids:
        try:
            r_ids = json.loads(a.recipient_ids)
        except Exception:
            r_ids = [i.strip() for i in a.recipient_ids.split(",") if i.strip()]

    ann_type = a.announcement_type or "General"
    recip_type = a.recipient_type or "All Employees"

    return {
        "id": a.announcement_code or f"ANN-{a.id:03d}",
        "announcementId": a.id,
        "title": a.title,
        "message": a.message,
        "author": a.author,
        "date": a.date.isoformat(),
        "priority": a.priority or "Normal",
        "type": ann_type,
        "announcement_type": ann_type,
        "announcementType": ann_type,
        "recipient_type": recip_type,
        "recipientType": recip_type,
        "recipient_ids": r_ids,
        "recipientIds": r_ids,
        "recipients": r_ids,
        "isActive": a.is_active,
    }


@router.get("", response_model=List[dict])
def list_announcements(
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List announcements for staff and administration with audience filtering."""
    user_role = getattr(current_user, "role", "employee")
    user_email = getattr(current_user, "email", "")

    if settings.DATABASE_BACKEND == "firebase":
        raw = FirestoreService.list_all("announcements")
        if not raw:
            raw = FirestoreService.list_all("notifications")
        filtered = []

        emp_id = ""
        if user_role != "admin":
            emps = FirestoreService.query("employees", {"email": user_email})
            if emps:
                emp_id = emps[0].get("employee_id")

        for a in raw:
            is_act = a.get("is_active", True) if "is_active" in a else a.get("isActive", True)
            if not is_act:
                continue

            title = str(a.get("title", "")).lower()
            msg = str(a.get("message", "")).lower()
            author = str(a.get("author", "")).lower()

            if search:
                s = search.strip().lower()
                if s not in title and s not in msg and s not in author:
                    continue

            if user_role != "admin":
                recip_type = a.get("recipient_type", "All Employees")
                if recip_type != "All Employees":
                    r_ids = a.get("recipient_ids") or []
                    if isinstance(r_ids, str):
                        try:
                            r_ids = json.loads(r_ids)
                        except Exception:
                            r_ids = [r_ids]
                    if emp_id not in r_ids and user_email not in r_ids:
                        continue

            filtered.append(format_announcement_response(a))

        filtered.sort(key=lambda x: str(x.get("date", "")), reverse=True)
        return filtered

    # PostgreSQL fallback
    query = db.query(Announcement).filter(Announcement.is_active == True)
    if search:
        s = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                Announcement.title.ilike(s),
                Announcement.message.ilike(s),
                Announcement.author.ilike(s),
                Announcement.announcement_type.ilike(s),
            )
        )

    all_announcements = query.order_by(desc(Announcement.date), desc(Announcement.id)).all()
    if current_user.role == "admin":
        return [format_announcement_response(a) for a in all_announcements]

    emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not emp:
        emp = db.query(Employee).filter(Employee.email == current_user.email).first()
    emp_id = emp.employee_id if emp else ""
    emp_email = emp.email if emp else current_user.email

    visible = []
    for a in all_announcements:
        if a.recipient_type == "All Employees" or not a.recipient_type:
            visible.append(a)
        elif a.recipient_ids:
            try:
                ids = json.loads(a.recipient_ids)
            except Exception:
                ids = [i.strip() for i in a.recipient_ids.split(",") if i.strip()]
            if emp_id in ids or emp_email in ids:
                visible.append(a)

    return [format_announcement_response(a) for a in visible]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=dict)
def create_announcement(
    data: AnnouncementCreate,
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin),
):
    """Publish a new announcement (Admin only)."""
    if not data.title or not data.title.strip():
        raise HTTPException(status_code=400, detail="Please enter an announcement title.")
    if not data.message or not data.message.strip():
        raise HTTPException(status_code=400, detail="Please write an announcement message.")

    raw_type = (data.announcementType or data.announcement_type or data.type or "General").strip()
    valid_types = ["General", "Important", "Holiday", "Meeting"]
    matched_type = "General"
    for vt in valid_types:
        if raw_type.lower() == vt.lower():
            matched_type = vt
            break

    raw_priority = (data.priority or "Normal").strip()
    author_val = (data.author or "Administrator").strip()

    recip_type = (data.recipientType or data.recipient_type or "All Employees").strip()
    raw_recipients = data.recipients or data.recipient_ids or data.recipientIds
    if isinstance(raw_recipients, str):
        raw_recipients = [r.strip() for r in raw_recipients.split(",") if r.strip()]
    elif not isinstance(raw_recipients, list):
        raw_recipients = None

    code = f"ANN-{int(datetime.now(timezone.utc).timestamp() * 1000) % 1000000}"
    now_iso = datetime.now(timezone.utc).isoformat()
    today_iso = date.today().isoformat()

    if settings.DATABASE_BACKEND == "firebase":
        ann_doc = {
            "id": code,
            "announcement_code": code,
            "title": data.title.strip(),
            "message": data.message.strip(),
            "type": matched_type,
            "announcement_type": matched_type,
            "author": author_val,
            "date": today_iso,
            "priority": raw_priority,
            "sendTo": recip_type,
            "recipient_type": recip_type,
            "recipient_ids": raw_recipients if recip_type != "All Employees" else None,
            "selectedEmployeeIds": raw_recipients if recip_type != "All Employees" else None,
            "is_active": True,
            "createdAt": now_iso,
            "created_at": now_iso,
            "createdBy": getattr(admin_user, "email", "Administrator"),
            "updated_at": now_iso,
        }
        FirestoreService.save("announcements", code, ann_doc)
        FirestoreService.save("notifications", code, ann_doc)

        # Dual-write to PostgreSQL database for shared persistence
        try:
            pg_ann = Announcement(
                announcement_code=code,
                title=data.title.strip(),
                message=data.message.strip(),
                author=author_val,
                date=date.today(),
                priority=raw_priority,
                announcement_type=matched_type,
                recipient_type=recip_type,
                recipient_ids=json.dumps(raw_recipients) if raw_recipients else None,
                is_active=True,
            )
            db.add(pg_ann)
            db.commit()
        except Exception as e:
            db.rollback()

        return format_announcement_response(ann_doc)

    # PostgreSQL fallback
    ann = Announcement(
        announcement_code=code,
        title=data.title.strip(),
        message=data.message.strip(),
        author=author_val,
        date=date.today(),
        priority=raw_priority,
        announcement_type=matched_type,
        recipient_type=recip_type,
        recipient_ids=json.dumps(raw_recipients) if raw_recipients else None,
        is_active=True,
    )
    db.add(ann)
    db.commit()
    db.refresh(ann)
    return format_announcement_response(ann)


@router.patch("/{announcement_id}", response_model=dict)
def update_announcement(
    announcement_id: str,
    data: AnnouncementUpdate,
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin),
):
    """Edit announcement (Admin only)."""
    if settings.DATABASE_BACKEND == "firebase":
        ann = FirestoreService.get_by_id("announcements", announcement_id)
        if not ann:
            raise HTTPException(status_code=404, detail=f"Announcement '{announcement_id}' not found.")
        updates = {}
        if data.title and data.title.strip():
            updates["title"] = data.title.strip()
        if data.message and data.message.strip():
            updates["message"] = data.message.strip()
        if data.author and data.author.strip():
            updates["author"] = data.author.strip()
        if data.priority and data.priority.strip():
            updates["priority"] = data.priority.strip()
        if data.is_active is not None:
            updates["is_active"] = data.is_active

        doc_key = ann.get("announcement_code") or announcement_id
        FirestoreService.update("announcements", doc_key, updates)
        ann.update(updates)
        return format_announcement_response(ann)

    # PostgreSQL fallback
    ann = (
        db.query(Announcement)
        .filter(
            (Announcement.announcement_code == announcement_id)
            | (Announcement.id == int(announcement_id) if announcement_id.isdigit() else False)
        )
        .first()
    )
    if not ann:
        raise HTTPException(status_code=404, detail=f"Announcement '{announcement_id}' not found.")

    if data.title and data.title.strip():
        ann.title = data.title.strip()
    if data.message and data.message.strip():
        ann.message = data.message.strip()
    if data.author and data.author.strip():
        ann.author = data.author.strip()
    if data.priority and data.priority.strip():
        ann.priority = data.priority.strip()
    if data.is_active is not None:
        ann.is_active = data.is_active

    db.commit()
    db.refresh(ann)
    return format_announcement_response(ann)


@router.delete("/{announcement_id}", status_code=status.HTTP_200_OK)
def delete_announcement(
    announcement_id: str,
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin),
):
    """Delete an announcement (Admin only)."""
    if settings.DATABASE_BACKEND == "firebase":
        ann = FirestoreService.get_by_id("announcements", announcement_id)
        if not ann:
            raise HTTPException(status_code=404, detail=f"Announcement '{announcement_id}' not found.")
        doc_key = ann.get("announcement_code") or announcement_id
        FirestoreService.delete("announcements", doc_key)
        return {"success": True, "message": "Announcement removed successfully."}

    ann = (
        db.query(Announcement)
        .filter(
            (Announcement.announcement_code == announcement_id)
            | (Announcement.id == int(announcement_id) if announcement_id.isdigit() else False)
        )
        .first()
    )
    if not ann:
        raise HTTPException(status_code=404, detail=f"Announcement '{announcement_id}' not found.")

    db.delete(ann)
    db.commit()
    return {"success": True, "message": "Announcement removed successfully."}
