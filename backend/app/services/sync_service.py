import logging
from datetime import datetime, date, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User
from app.models.employee import Employee
from app.models.registration_request import RegistrationRequest
from app.models.attendance import Attendance
from app.models.leave import Leave
from app.models.announcement import Announcement
from app.services.firestore_service import FirestoreService

logger = logging.getLogger("uvicorn.error")


def sync_employee_approval_state(
    email: str,
    status: str,  # "approved" or "rejected" or "pending"
    admin_identifier: str = "admin@arshith.com",
    rejection_reason: Optional[str] = None,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Authoritative state synchronization across Google Cloud Firestore and PostgreSQL.
    Ensures employee, user, and registration_request records are perfectly aligned.
    """
    clean_email = email.strip().lower()
    norm_status = status.strip().lower()
    now_iso = datetime.now(timezone.utc).isoformat()
    now_dt = datetime.now(timezone.utc)

    is_approved = norm_status in ("approved", "active")
    is_rejected = norm_status == "rejected"
    is_pending = norm_status == "pending"

    ui_status = "Approved" if is_approved else ("Rejected" if is_rejected else "Pending")
    app_status = "approved" if is_approved else ("rejected" if is_rejected else "pending")
    approval_status = "APPROVED" if is_approved else ("REJECTED" if is_rejected else "PENDING")

    logger.info(f"[SyncService] Synchronizing approval state for {clean_email} -> {ui_status}")

    # -------------------------------------------------------------
    # 1. Update all matching documents in Cloud Firestore
    # -------------------------------------------------------------
    # Employees collection
    emps = FirestoreService.query("employees", {"email": clean_email})
    emp_ids_seen = set()
    emp_name = clean_email.split("@")[0]
    emp_code = None
    phone = "--"
    dept = "Operations"
    desig = "Operations Associate"

    for emp in emps:
        doc_id = emp.get("_firestore_id") or emp.get("uid") or emp.get("id") or emp.get("employeeId") or emp.get("employee_id")
        emp_code = emp_code or emp.get("employeeId") or emp.get("employee_id")
        emp_name = emp.get("name") or emp.get("fullName") or emp.get("full_name") or emp_name
        phone = emp.get("phone") or phone
        dept = emp.get("department") or dept
        desig = emp.get("designation") or desig

        if doc_id:
            emp_ids_seen.add(str(doc_id))
            FirestoreService.update("employees", str(doc_id), {
                "status": app_status,
                "reviewedAt": now_iso,
                "reviewedBy": admin_identifier,
                "reviewed_at": now_iso,
                "reviewed_by": admin_identifier,
                "rejectionReason": rejection_reason if is_rejected else None,
                "rejection_reason": rejection_reason if is_rejected else None,
                "updated_at": now_iso,
            })

    # Also update alternate employee doc by employeeId if not already updated
    if emp_code and str(emp_code) not in emp_ids_seen:
        alt_matches = FirestoreService.query("employees", {"employee_id": emp_code})
        for alt in alt_matches:
            alt_id = alt.get("_firestore_id") or alt.get("id")
            if alt_id and str(alt_id) not in emp_ids_seen:
                emp_ids_seen.add(str(alt_id))
                FirestoreService.update("employees", str(alt_id), {
                    "status": app_status,
                    "reviewedAt": now_iso,
                    "reviewedBy": admin_identifier,
                    "reviewed_at": now_iso,
                    "reviewed_by": admin_identifier,
                    "rejectionReason": rejection_reason if is_rejected else None,
                    "rejection_reason": rejection_reason if is_rejected else None,
                    "updated_at": now_iso,
                })

    # Users collection
    users = FirestoreService.query("users", {"email": clean_email})
    user_uid = None
    hashed_pwd = None
    for u in users:
        u_id = u.get("id") or u.get("_firestore_id")
        user_uid = user_uid or u.get("uid") or u_id
        hashed_pwd = hashed_pwd or u.get("hashed_password")
        if u_id:
            FirestoreService.update("users", str(u_id), {
                "approval_status": approval_status,
                "status": app_status,
                "is_active": is_approved,
                "reviewed_at": now_iso,
                "reviewed_by_id": admin_identifier,
                "rejection_reason": rejection_reason if is_rejected else None,
                "updated_at": now_iso,
            })

    # Registration requests collection
    reqs = FirestoreService.query("registration_requests", {"email": clean_email})
    for r in reqs:
        r_id = r.get("request_code") or r.get("id") or r.get("_firestore_id")
        if r_id:
            FirestoreService.update("registration_requests", str(r_id), {
                "status": ui_status,
                "reviewed_at": now_iso,
                "reviewed_by": admin_identifier,
                "rejection_reason": rejection_reason if is_rejected else None,
                "updated_at": now_iso,
            })

    # -------------------------------------------------------------
    # 2. Synchronize PostgreSQL database
    # -------------------------------------------------------------
    should_close_db = False
    session = db
    if session is None:
        try:
            session = SessionLocal()
            should_close_db = True
        except Exception as e:
            logger.warning(f"[SyncService] Could not open PostgreSQL session: {e}")
            session = None

    if session is not None:
        try:
            # Sync or create User
            user_pg = session.query(User).filter(func.lower(func.trim(User.email)) == clean_email).first()
            if user_pg:
                user_pg.approval_status = approval_status
                user_pg.is_active = is_approved
                user_pg.reviewed_at = now_dt
                user_pg.rejection_reason = rejection_reason if is_rejected else None
                user_pg.updated_at = now_dt
            else:
                user_pg = User(
                    email=clean_email,
                    hashed_password=hashed_pwd or "$2b$12$WAn/o7le7B7G9l1iIunkrOPfMjFchVMwxnW6HecwYxUgEI1TV.OmG",
                    role="employee",
                    is_active=is_approved,
                    approval_status=approval_status,
                    reviewed_at=now_dt,
                    rejection_reason=rejection_reason if is_rejected else None,
                )
                session.add(user_pg)
                session.flush()

            # Sync or create Employee
            emp_code_val = emp_code or (f"AFI-{clean_email.split('@')[0].upper()[:4]}")
            emp_pg = session.query(Employee).filter(
                (func.lower(func.trim(Employee.email)) == clean_email) |
                (func.upper(func.trim(Employee.employee_id)) == emp_code_val.upper())
            ).first()

            if emp_pg:
                emp_pg.status = "Active" if is_approved else ("Inactive" if is_rejected else "Pending")
                emp_pg.full_name = emp_name or emp_pg.full_name
                emp_pg.phone = phone if phone != "--" else emp_pg.phone
                emp_pg.department = dept or emp_pg.department
                emp_pg.designation = desig or emp_pg.designation
                emp_pg.updated_at = now_dt
            else:
                emp_pg = Employee(
                    employee_id=emp_code_val,
                    user_id=user_pg.id,
                    full_name=emp_name,
                    email=clean_email,
                    phone=phone,
                    department=dept,
                    designation=desig,
                    status="Active" if is_approved else ("Inactive" if is_rejected else "Pending"),
                )
                session.add(emp_pg)

            # Sync or create RegistrationRequest
            req_pg = session.query(RegistrationRequest).filter(
                (func.lower(func.trim(RegistrationRequest.email)) == clean_email) |
                (func.upper(func.trim(RegistrationRequest.employee_id)) == emp_code_val.upper())
            ).first()

            if req_pg:
                req_pg.status = ui_status
                req_pg.reviewed_by = admin_identifier
                req_pg.reviewed_at = now_dt
                req_pg.rejection_reason = rejection_reason if is_rejected else None
                req_pg.updated_at = now_dt
            else:
                req_code = f"REQ-{datetime.now().strftime('%Y%m%d%H%M%S')[-4:]}"
                req_pg = RegistrationRequest(
                    request_code=req_code,
                    full_name=emp_name,
                    employee_id=emp_code_val,
                    email=clean_email,
                    phone=phone,
                    status=ui_status,
                    requested_date=date.today(),
                    reviewed_by=admin_identifier,
                    reviewed_at=now_dt,
                    rejection_reason=rejection_reason if is_rejected else None,
                )
                session.add(req_pg)

            session.commit()
            logger.info(f"[SyncService] PostgreSQL commit successful for {clean_email} -> {ui_status}")
        except Exception as e:
            session.rollback()
            logger.error(f"[SyncService] Error synchronizing PostgreSQL for {clean_email}: {e}")
        finally:
            if should_close_db:
                session.close()

    return {
        "email": clean_email,
        "status": ui_status,
        "app_status": app_status,
        "approval_status": approval_status,
        "is_approved": is_approved,
        "is_rejected": is_rejected,
        "is_pending": is_pending,
    }


def sync_attendance_to_postgres(
    emp_id: str,
    att_date: date,
    check_in_time: Optional[str] = None,
    check_out_time: Optional[str] = None,
    duration: Optional[str] = None,
    work_mode: str = "WFO",
    status_str: str = "Present",
    is_late: bool = False,
    late_reason: Optional[str] = None,
    db: Optional[Session] = None,
) -> None:
    """Synchronize attendance check-in / check-out to PostgreSQL."""
    should_close = False
    session = db
    if session is None:
        try:
            session = SessionLocal()
            should_close = True
        except Exception:
            return

    if isinstance(check_in_time, dict):
        rec_data = check_in_time
        check_in_time = rec_data.get("check_in") or rec_data.get("check_in_time")
        check_out_time = rec_data.get("check_out") or rec_data.get("check_out_time")
        duration = rec_data.get("working_duration") or rec_data.get("duration")
        work_mode = rec_data.get("work_mode", work_mode)
        status_str = rec_data.get("status", status_str)
        is_late = rec_data.get("is_late", is_late)
        late_reason = rec_data.get("late_reason", late_reason)

    try:
        clean_eid = emp_id.strip()
        rec = session.query(Attendance).filter(
            Attendance.employee_id == clean_eid,
            Attendance.date == att_date,
        ).first()

        now_dt = datetime.now(timezone.utc)
        if rec:
            if check_in_time and check_in_time != "--":
                rec.check_in_time = check_in_time
            if check_out_time and check_out_time != "--":
                rec.check_out_time = check_out_time
            if duration and duration != "--":
                rec.duration = duration
            if work_mode:
                rec.work_mode = work_mode
            if status_str:
                rec.status = status_str
            rec.is_late = is_late
            if late_reason:
                rec.late_reason = late_reason
                rec.late_reason_submitted_at = now_dt
            rec.updated_at = now_dt
        else:
            rec = Attendance(
                employee_id=clean_eid,
                date=att_date,
                check_in_time=check_in_time,
                check_out_time=check_out_time,
                duration=duration or ("In Progress" if not check_out_time else "0h 0m"),
                work_mode=work_mode,
                status=status_str,
                is_late=is_late,
                late_reason=late_reason,
                late_reason_submitted_at=now_dt if late_reason else None,
            )
            session.add(rec)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        logger.warning(f"[SyncService] Attendance PostgreSQL sync failed: {e}")
        return False
    finally:
        if should_close:
            session.close()
