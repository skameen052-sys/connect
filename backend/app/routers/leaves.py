import logging
from datetime import date, datetime, timezone
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from app.core.config import settings
from app.core.firebase import get_firestore_client, is_firebase_live
from app.db.session import get_db
from app.models.leave import Leave
from app.models.employee import Employee
from app.models.user import User
from app.schemas.leave import LeaveCreateRequest, LeaveStatusUpdateRequest
from app.dependencies.auth import get_current_user, get_current_admin, get_current_employee
from app.services.firestore_service import FirestoreService

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/leaves", tags=["Leaves"])


def calculate_employee_leave_balances(employee_id: str, db: Optional[Session] = None) -> dict:
    """Calculate remaining and total balances for each leave type for the employee."""
    totals = {
        "Casual Leave": 12,
        "Sick Leave": 8,
        "Earned Leave": 15,
    }

    used = {
        "Casual Leave": 0,
        "Sick Leave": 0,
        "Earned Leave": 0,
    }

    if settings.DATABASE_BACKEND == "firebase":
        all_emp_leaves = FirestoreService.query("leaves", {"employee_id": employee_id, "status": "Approved"})
        for l in all_emp_leaves:
            norm = str(l.get("leave_type", "")).strip()
            days = int(l.get("days_count") or l.get("days") or 1)
            if norm in ["Casual Leave", "Casual Leave (CL)", "CL"]:
                used["Casual Leave"] += days
            elif norm in ["Sick Leave", "Sick Leave (SL)", "SL"]:
                used["Sick Leave"] += days
            elif norm in ["Earned Leave", "Earned Leave (EL)", "EL"]:
                used["Earned Leave"] += days
    elif db:
        approved_leaves = (
            db.query(Leave)
            .filter(
                Leave.employee_id == employee_id,
                Leave.status == "Approved",
            )
            .all()
        )
        for l in approved_leaves:
            norm = l.leave_type.strip()
            if norm in ["Casual Leave", "Casual Leave (CL)", "CL"]:
                used["Casual Leave"] += l.days_count
            elif norm in ["Sick Leave", "Sick Leave (SL)", "SL"]:
                used["Sick Leave"] += l.days_count
            elif norm in ["Earned Leave", "Earned Leave (EL)", "EL"]:
                used["Earned Leave"] += l.days_count

    return {
        "casualLeave": {
            "name": "Casual Leave",
            "code": "CL",
            "total": totals["Casual Leave"],
            "used": used["Casual Leave"],
            "available": max(0, totals["Casual Leave"] - used["Casual Leave"]),
        },
        "sickLeave": {
            "name": "Sick Leave",
            "code": "SL",
            "total": totals["Sick Leave"],
            "used": used["Sick Leave"],
            "available": max(0, totals["Sick Leave"] - used["Sick Leave"]),
        },
        "earnedLeave": {
            "name": "Earned Leave",
            "code": "EL",
            "total": totals["Earned Leave"],
            "used": used["Earned Leave"],
            "available": max(0, totals["Earned Leave"] - used["Earned Leave"]),
        },
    }


def parse_time_str(time_str: str) -> Optional[datetime]:
    """Helper to parse a time string in standard formats."""
    if not time_str or not isinstance(time_str, str):
        return None
    cleaned = time_str.strip()
    for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M%p", "%I:%M:%S %p", "%I:%M:%S%p"):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            pass
    return None


def format_leave_response(leave: Any) -> dict:
    if isinstance(leave, dict):
        l = leave
        applied_str = str(l.get("applied_date") or l.get("applied_on") or date.today().isoformat())
        start_str = str(l.get("start_date") or l.get("from_date") or "")
        end_str = str(l.get("end_date") or l.get("to_date") or "")
        duration_type = l.get("duration_type") or "Full-Day Leave"
        is_hourly = duration_type == "Hourly Leave"
        hours_count = l.get("hours_count")
        days_count = l.get("days_count") or (1 if not is_hourly else 0)
        duration_display = f"{hours_count:g} hr(s)" if (is_hourly and hours_count is not None) else f"{days_count} day(s)"
        leave_code = l.get("leave_code") or l.get("id") or "LV-001"

        return {
            "id": leave_code,
            "request_id": leave_code,
            "requestId": leave_code,
            "leaveId": l.get("id", leave_code),
            "leave_id": l.get("id", leave_code),
            "employee_id": l.get("employee_id"),
            "employeeId": l.get("employee_id"),
            "employee_name": l.get("employee_name"),
            "employeeName": l.get("employee_name"),
            "leave_type": l.get("leave_type"),
            "leaveType": l.get("leave_type"),
            "type": l.get("leave_type"),
            "duration_type": duration_type,
            "durationType": duration_type,
            "start_time": l.get("start_time"),
            "startTime": l.get("start_time"),
            "end_time": l.get("end_time"),
            "endTime": l.get("end_time"),
            "hours_count": hours_count,
            "hoursCount": hours_count,
            "hours": hours_count,
            "duration_display": duration_display,
            "durationDisplay": duration_display,
            "from_date": start_str,
            "fromDate": start_str,
            "startDate": start_str,
            "start_date": start_str,
            "leave_date": start_str,
            "leaveDate": start_str,
            "from": start_str,
            "to_date": end_str,
            "toDate": end_str,
            "endDate": end_str,
            "end_date": end_str,
            "to": end_str,
            "days": days_count,
            "days_count": days_count,
            "daysCount": days_count,
            "reason": l.get("reason"),
            "status": l.get("status", "Pending"),
            "applied_on": applied_str,
            "appliedOn": applied_str,
            "applied_date": applied_str,
            "appliedDate": applied_str,
            "requestDate": applied_str,
            "reviewed_by": l.get("reviewed_by"),
            "reviewedBy": l.get("reviewed_by"),
            "approved_by": l.get("reviewed_by"),
            "approved_at": l.get("approved_at"),
            "approvedAt": l.get("approved_at"),
            "rejection_remarks": l.get("rejection_remarks"),
            "rejectionRemarks": l.get("rejection_remarks"),
            "rejection_reason": l.get("rejection_remarks"),
            "rejectionReason": l.get("rejection_remarks"),
        }

    # SQLAlchemy model
    applied_str = (
        leave.applied_date.isoformat()
        if leave.applied_date
        else (leave.created_at.date().isoformat() if leave.created_at else date.today().isoformat())
    )
    start_str = leave.start_date.isoformat() if leave.start_date else None
    end_str = leave.end_date.isoformat() if leave.end_date else None
    duration_type = leave.duration_type or "Full-Day Leave"
    is_hourly = duration_type == "Hourly Leave"
    duration_display = f"{leave.hours_count:g} hr(s)" if (is_hourly and leave.hours_count is not None) else f"{leave.days_count} day(s)"

    return {
        "id": leave.leave_code,
        "request_id": leave.leave_code,
        "requestId": leave.leave_code,
        "leaveId": leave.id,
        "leave_id": leave.id,
        "employee_id": leave.employee_id,
        "employeeId": leave.employee_id,
        "employee_name": leave.employee_name,
        "employeeName": leave.employee_name,
        "leave_type": leave.leave_type,
        "leaveType": leave.leave_type,
        "type": leave.leave_type,
        "duration_type": duration_type,
        "durationType": duration_type,
        "start_time": leave.start_time,
        "startTime": leave.start_time,
        "end_time": leave.end_time,
        "endTime": leave.end_time,
        "hours_count": leave.hours_count,
        "hoursCount": leave.hours_count,
        "hours": leave.hours_count,
        "duration_display": duration_display,
        "durationDisplay": duration_display,
        "from_date": start_str,
        "fromDate": start_str,
        "startDate": start_str,
        "start_date": start_str,
        "leave_date": start_str,
        "leaveDate": start_str,
        "from": start_str,
        "to_date": end_str,
        "toDate": end_str,
        "endDate": end_str,
        "end_date": end_str,
        "to": end_str,
        "days": leave.days_count,
        "days_count": leave.days_count,
        "daysCount": leave.days_count,
        "reason": leave.reason,
        "status": leave.status,
        "applied_on": applied_str,
        "appliedOn": applied_str,
        "applied_date": applied_str,
        "appliedDate": applied_str,
        "requestDate": applied_str,
        "reviewed_by": leave.reviewed_by,
        "reviewedBy": leave.reviewed_by,
        "approved_by": leave.reviewed_by,
        "approved_at": leave.approved_at.isoformat() if getattr(leave, "approved_at", None) else None,
        "approvedAt": leave.approved_at.isoformat() if getattr(leave, "approved_at", None) else None,
        "rejection_remarks": leave.rejection_remarks,
        "rejectionRemarks": leave.rejection_remarks,
        "rejection_reason": leave.rejection_remarks,
        "rejectionReason": leave.rejection_remarks,
    }


@router.get("", response_model=List[dict])
def list_leaves(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List leave requests across mobile and web (Admins see all; employees see their own)."""
    user_role = getattr(current_user, "role", "employee")
    user_email = getattr(current_user, "email", "")
    user_id = getattr(current_user, "id", None)

    if settings.DATABASE_BACKEND == "firebase":
        top_leaves = FirestoreService.list_all("leaves")
        cg_requests = FirestoreService.collection_group("requests")

        merged = {}
        for l in top_leaves:
            code = l.get("leave_code") or l.get("id") or ""
            merged[str(code)] = l

        for req in cg_requests:
            req_id = req.get("id") or req.get("_firestore_id") or ""
            key = str(req.get("leave_code") or req_id)
            if key not in merged:
                emp_code = req.get("employeeId") or req.get("employee_id") or ""
                applied_date_val = req.get("appliedAt") or req.get("applied_date") or date.today().isoformat()
                if hasattr(applied_date_val, "isoformat"):
                    applied_date_val = applied_date_val.isoformat()
                elif hasattr(applied_date_val, "toDate"):
                    applied_date_val = applied_date_val.toDate().isoformat()

                start_d = str(req.get("fromDate") or req.get("from_date") or req.get("startDate") or "")
                end_d = str(req.get("toDate") or req.get("to_date") or req.get("endDate") or start_d)

                emp_name = req.get("employeeName") or req.get("name") or ""
                if not emp_name or emp_name == "Employee":
                    if emp_code:
                        emps = FirestoreService.query("employees", {"employee_id": emp_code})
                        if not emps:
                            emps = FirestoreService.query("employees", {"uid": emp_code})
                        if not emps and req.get("email"):
                            emps = FirestoreService.query("employees", {"email": req.get("email")})
                        if emps:
                            emp_name = emps[0].get("full_name") or emps[0].get("fullName") or emps[0].get("name") or "Employee"
                            real_code = emps[0].get("employee_id") or emps[0].get("employeeId")
                            if real_code and len(str(emp_code)) > 15:
                                emp_code = real_code
                if not emp_name:
                    emp_name = "Employee"

                merged[key] = {
                    "id": key,
                    "leave_code": key,
                    "employee_id": emp_code,
                    "employeeId": emp_code,
                    "employee_name": emp_name,
                    "employeeName": emp_name,
                    "leave_type": req.get("leaveType") or req.get("leave_type") or "Casual Leave",
                    "leaveType": req.get("leaveType") or req.get("leave_type") or "Casual Leave",
                    "duration_type": req.get("duration") or req.get("durationType") or "Full-Day Leave",
                    "start_date": start_d,
                    "from_date": start_d,
                    "fromDate": start_d,
                    "end_date": end_d,
                    "to_date": end_d,
                    "toDate": end_d,
                    "reason": req.get("reason", ""),
                    "status": (req.get("status") or "Pending").capitalize(),
                    "applied_date": str(applied_date_val).split("T")[0],
                    "reviewed_by": req.get("reviewedBy") or req.get("reviewed_by"),
                    "reviewed_at": str(req.get("reviewedAt") or ""),
                }

        all_leaves = list(merged.values())
        if user_role == "admin":
            leaves = all_leaves
        else:
            emps = FirestoreService.query("employees", {"email": user_email})
            emp_id = emps[0].get("employee_id") if emps else ""
            emp_uid = emps[0].get("uid") if emps else ""
            leaves = [
                l for l in all_leaves
                if str(l.get("employee_id")) in [str(emp_id), str(emp_uid), user_email]
                or str(l.get("employeeId")) in [str(emp_id), str(emp_uid), user_email]
            ]
        leaves.sort(key=lambda x: str(x.get("applied_date", "")), reverse=True)
        return [format_leave_response(l) for l in leaves]

    # PostgreSQL fallback
    if current_user.role == "admin":
        leaves = db.query(Leave).order_by(desc(Leave.applied_date), desc(Leave.id)).all()
    else:
        emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
        if not emp:
            emp = db.query(Employee).filter(Employee.email == current_user.email).first()
        emp_id = emp.employee_id if emp else ""
        leaves = (
            db.query(Leave)
            .filter(Leave.employee_id == emp_id)
            .order_by(desc(Leave.applied_date), desc(Leave.id))
            .all()
        )

    return [format_leave_response(l) for l in leaves]


@router.get("/balances", response_model=dict)
def get_my_leave_balances(
    db: Session = Depends(get_db),
    employee=Depends(get_current_employee),
):
    """Retrieve personal leave balances for the authenticated employee."""
    emp_id = getattr(employee, "employee_id", None) or getattr(employee, "employeeId", None)
    return calculate_employee_leave_balances(emp_id, db)


@router.get("/me", response_model=List[dict])
def get_my_leaves(
    db: Session = Depends(get_db),
    employee=Depends(get_current_employee),
):
    """Retrieve leave applications for the current employee."""
    emp_id = getattr(employee, "employee_id", None) or getattr(employee, "employeeId", None)
    emp_uid = str(getattr(employee, "uid", None) or getattr(employee, "id", None) or emp_id)

    if settings.DATABASE_BACKEND == "firebase":
        top_leaves = FirestoreService.query("leaves", {"employee_id": emp_id})
        cg_requests = FirestoreService.collection_group("requests")

        merged = {}
        for l in top_leaves:
            code = l.get("leave_code") or l.get("id") or ""
            merged[str(code)] = l

        for req in cg_requests:
            c_eid = str(req.get("employeeId") or req.get("employee_id") or "")
            if c_eid in [str(emp_id), str(emp_uid)]:
                req_id = req.get("id") or req.get("_firestore_id") or ""
                key = str(req.get("leave_code") or req_id)
                if key not in merged:
                    applied_date_val = req.get("appliedAt") or req.get("applied_date") or date.today().isoformat()
                    start_d = str(req.get("fromDate") or req.get("from_date") or req.get("startDate") or "")
                    end_d = str(req.get("toDate") or req.get("to_date") or req.get("endDate") or start_d)
                    merged[key] = {
                        "id": key,
                        "leave_code": key,
                        "employee_id": emp_id,
                        "employee_name": req.get("employeeName") or req.get("name") or "Employee",
                        "leave_type": req.get("leaveType") or req.get("leave_type") or "Casual Leave",
                        "duration_type": req.get("duration") or req.get("durationType") or "Full-Day Leave",
                        "start_date": start_d,
                        "from_date": start_d,
                        "end_date": end_d,
                        "to_date": end_d,
                        "reason": req.get("reason", ""),
                        "status": (req.get("status") or "Pending").capitalize(),
                        "applied_date": str(applied_date_val).split("T")[0],
                    }

        leaves = list(merged.values())
        leaves.sort(key=lambda x: str(x.get("applied_date", "")), reverse=True)
        return [format_leave_response(l) for l in leaves]

    # PostgreSQL fallback
    leaves = (
        db.query(Leave)
        .filter(or_(Leave.employee_id == employee.employee_id, Leave.employee_id == employee.email))
        .order_by(desc(Leave.applied_date), desc(Leave.id))
        .all()
    )
    return [format_leave_response(l) for l in leaves]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=dict)
def apply_leave(
    payload: LeaveCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Submit a leave application supporting Full-Day and Hourly durations."""
    user_role = getattr(current_user, "role", "employee")
    user_email = getattr(current_user, "email", "")
    user_id = getattr(current_user, "id", None)

    if user_role != "employee":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employee access required to apply for leave.",
        )

    if settings.DATABASE_BACKEND == "firebase":
        emps = FirestoreService.query("employees", {"email": user_email})
        if not emps and user_id:
            emps = FirestoreService.query("employees", {"user_id": user_id})
        if not emps:
            raise HTTPException(status_code=404, detail="Employee profile not found.")
        emp = emps[0]
        emp_id = emp.get("employee_id") or emp.get("employeeId")
        emp_name = emp.get("full_name") or emp.get("fullName") or "Employee"
    else:
        emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
        if not emp:
            emp = db.query(Employee).filter(Employee.email == current_user.email).first()
        if not emp:
            raise HTTPException(status_code=404, detail="Employee profile not found.")
        emp_id = emp.employee_id
        emp_name = emp.full_name

    # 1. Validate Leave Type
    raw_type = (payload.leaveType or payload.leave_type or payload.type or "").strip()
    if not raw_type:
        raise HTTPException(status_code=400, detail="Please select a leave type.")

    if raw_type.lower() in ["casual leave", "casual leave (cl)", "cl"]:
        canonical_type = "Casual Leave"
    elif raw_type.lower() in ["sick leave", "sick leave (sl)", "sl"]:
        canonical_type = "Sick Leave"
    elif raw_type.lower() in ["earned leave", "earned leave (el)", "el"]:
        canonical_type = "Earned Leave"
    else:
        canonical_type = raw_type

    # 2. Duration Type
    raw_duration = payload.durationType if payload.durationType is not None else payload.duration_type
    duration_val = (str(raw_duration).strip() if raw_duration else "Full-Day Leave")
    duration_type = "Hourly Leave" if "hour" in duration_val.lower() else "Full-Day Leave"
    is_hourly = duration_type == "Hourly Leave"

    # 3. Reason
    reason_str = (payload.reason or "").strip()
    if not reason_str:
        raise HTTPException(status_code=400, detail="Please enter a reason for your leave.")

    if is_hourly:
        leave_date_val = payload.leaveDate or payload.leave_date or payload.startDate or payload.start_date or payload.from_date
        if not leave_date_val:
            raise HTTPException(status_code=400, detail="Please select a leave date.")
        s_date = str(leave_date_val).strip()
        e_date = s_date
        start_time_val = (payload.startTime or payload.start_time or "").strip()
        end_time_val = (payload.endTime or payload.end_time or "").strip()
        if not start_time_val or not end_time_val:
            raise HTTPException(status_code=400, detail="Start Time and End Time are required for hourly leave.")
        hours_count = 2.0  # default duration estimate
        days_count = 0
    else:
        start_val = payload.startDate or payload.start_date or payload.from_date
        end_val = payload.endDate or payload.end_date or payload.to_date
        if not start_val or not end_val:
            raise HTTPException(status_code=400, detail="Start date and end date are required.")
        s_date = str(start_val).strip()
        e_date = str(end_val).strip()
        start_time_val = None
        end_time_val = None
        hours_count = None
        try:
            d1 = date.fromisoformat(s_date)
            d2 = date.fromisoformat(e_date)
            days_count = max(1, (d2 - d1).days + 1)
        except Exception:
            days_count = 1

    import random
    code = f"LV-{random.randint(1000, 9999)}"
    now_iso = datetime.now(timezone.utc).isoformat()
    today_iso = date.today().isoformat()

    if settings.DATABASE_BACKEND == "firebase":
        leave_doc = {
            "id": code,
            "leave_code": code,
            "employee_id": emp_id,
            "employee_name": emp_name,
            "leave_type": canonical_type,
            "start_date": s_date,
            "end_date": e_date,
            "days_count": days_count,
            "duration_type": duration_type,
            "start_time": start_time_val,
            "end_time": end_time_val,
            "hours_count": hours_count,
            "reason": reason_str,
            "status": "Pending",
            "applied_date": today_iso,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        FirestoreService.save("leaves", code, leave_doc)

        emp_uid = str(emp.get("uid") or emp.get("id") or emp_id)
        FirestoreService.save_subdocument(
            collection="leaves",
            doc_id=emp_uid,
            subcollection="requests",
            subdoc_id=code,
            data={
                "id": code,
                "leaveCode": code,
                "employeeId": emp_uid,
                "employeeName": emp_name,
                "leaveType": canonical_type,
                "duration": duration_type,
                "fromDate": s_date,
                "toDate": e_date,
                "reason": reason_str,
                "status": "Pending",
                "appliedAt": now_iso,
            }
        )

        FirestoreService.add_audit_log(
            actor_uid=emp_id,
            action="LEAVE_APPLIED",
            target_record=code,
            metadata={"type": canonical_type, "duration": duration_type},
        )

        # Dual-write to PostgreSQL database for cross-platform data synchronization
        try:
            pg_leave = Leave(
                leave_code=code,
                employee_id=emp_id,
                employee_name=emp_name,
                leave_type=canonical_type,
                start_date=date.fromisoformat(s_date),
                end_date=date.fromisoformat(e_date),
                days_count=days_count,
                duration_type=duration_type,
                start_time=start_time_val,
                end_time=end_time_val,
                hours_count=hours_count,
                reason=reason_str,
                status="Pending",
                applied_date=date.today(),
            )
            db.add(pg_leave)
            db.commit()
        except Exception as e:
            logger.warning(f"Dual-write leave to PostgreSQL failed: {e}")
            db.rollback()

        return format_leave_response(leave_doc)

    # PostgreSQL fallback
    new_leave = Leave(
        leave_code=code,
        employee_id=emp_id,
        employee_name=emp_name,
        leave_type=canonical_type,
        start_date=date.fromisoformat(s_date),
        end_date=date.fromisoformat(e_date),
        days_count=days_count,
        duration_type=duration_type,
        start_time=start_time_val,
        end_time=end_time_val,
        hours_count=hours_count,
        reason=reason_str,
        status="Pending",
        applied_date=date.today(),
    )
    db.add(new_leave)
    db.commit()
    db.refresh(new_leave)
    return format_leave_response(new_leave)


@router.patch("/{leave_id}", response_model=dict)
def update_leave_status(
    leave_id: str,
    payload: LeaveStatusUpdateRequest,
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin),
):
    """Approve or reject leave request across mobile and web (Admin only)."""
    admin_email = getattr(admin_user, "email", "admin@arshith.com")
    now_iso = datetime.now(timezone.utc).isoformat()
    remarks = payload.rejectionRemarks or payload.rejection_remarks or payload.rejection_reason

    # 1. Normalize and validate status
    raw_status = (payload.status or "").strip()
    if raw_status.lower() == "approved":
        canonical_status = "Approved"
    elif raw_status.lower() == "rejected":
        canonical_status = "Rejected"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Status must be 'Approved' or 'Rejected'."
        )

    if settings.DATABASE_BACKEND == "firebase":
        leave = FirestoreService.get_by_id("leaves", leave_id)
        if not leave:
            raise HTTPException(status_code=404, detail=f"Leave request '{leave_id}' not found.")

        current_status = str(leave.get("status") or "Pending").strip().capitalize()
        if current_status in ["Approved", "Rejected"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Leave request '{leave_id}' is already {current_status} and cannot be processed again."
            )

        doc_key = str(leave.get("leave_code") or leave.get("id") or leave_id)
        emp_uid = str(leave.get("_parent_id") or leave.get("employee_uid") or leave.get("employee_id") or leave.get("employeeId") or "")

        subdoc_updates = {
            "status": canonical_status,
            "reviewed_by": admin_email,
            "reviewedBy": admin_email,
            "reviewed_at": now_iso,
            "reviewedAt": now_iso,
            "updated_at": now_iso,
        }
        if canonical_status == "Approved":
            subdoc_updates["approved_at"] = now_iso
            subdoc_updates["approvedAt"] = now_iso
            subdoc_updates["approved_by"] = admin_email
            subdoc_updates["rejection_remarks"] = None
            subdoc_updates["rejectionRemarks"] = None
            subdoc_updates["rejection_reason"] = None
            subdoc_updates["rejectionReason"] = None
        else:
            rej_val = remarks or "Rejected by Administrator"
            subdoc_updates["rejection_remarks"] = rej_val
            subdoc_updates["rejectionRemarks"] = rej_val
            subdoc_updates["rejection_reason"] = rej_val
            subdoc_updates["rejectionReason"] = rej_val

        # 1. If _doc_path is known, update subcollection directly in Firestore
        if leave.get("_doc_path"):
            fs = get_firestore_client()
            if is_firebase_live() and fs is not None:
                try:
                    from app.services.firestore_service import _serialize_dict
                    fs.document(leave["_doc_path"]).update(_serialize_dict(subdoc_updates))
                except Exception as e:
                    logger.error(f"Error updating subcollection doc at {leave['_doc_path']}: {e}")

        # 2. Update subdocument via helper
        if emp_uid:
            sub_id = leave.get("_firestore_id") or doc_key
            FirestoreService.update_subdocument(
                collection="leaves",
                doc_id=emp_uid,
                subcollection="requests",
                subdoc_id=sub_id,
                updates=subdoc_updates,
            )

        # 3. Update or save top-level leaves document
        top_doc = {
            **leave,
            **subdoc_updates,
            "id": doc_key,
            "leave_code": leave.get("leave_code") or doc_key,
            "status": canonical_status,
        }
        FirestoreService.save("leaves", doc_key, top_doc)
        leave.update(top_doc)

        # 4. Sync local fallback database if applicable
        from app.services.firestore_service import _load_local_db, _save_local_db
        db_local = _load_local_db()
        cg_key = "cg_requests"
        if cg_key in db_local:
            for i, item in enumerate(db_local[cg_key]):
                if str(item.get("id")) == str(leave_id) or str(item.get("leave_code")) == str(leave_id):
                    db_local[cg_key][i].update(subdoc_updates)
                    break
            _save_local_db(db_local)

        FirestoreService.add_audit_log(
            actor_uid=admin_email,
            action=f"LEAVE_{canonical_status.upper()}",
            target_record=doc_key,
            metadata={"status": canonical_status, "remarks": remarks},
        )

        # Dual-write update to PostgreSQL database
        try:
            pg_leave = db.query(Leave).filter(
                (Leave.leave_code == doc_key) | 
                (Leave.leave_code == leave_id) | 
                (Leave.id == int(leave_id) if leave_id.isdigit() else False)
            ).first()
            if pg_leave:
                pg_leave.status = canonical_status
                pg_leave.reviewed_by = admin_email
                if canonical_status == "Approved":
                    pg_leave.approved_at = datetime.now(timezone.utc)
                    pg_leave.rejection_remarks = None
                else:
                    pg_leave.rejection_remarks = remarks or "Rejected by Administrator"
                db.commit()
        except Exception as e:
            logger.warning(f"Dual-write leave update to PostgreSQL failed: {e}")
            db.rollback()

        return format_leave_response(leave)

    # PostgreSQL fallback
    leave = (
        db.query(Leave)
        .filter((Leave.leave_code == leave_id) | (Leave.id == int(leave_id) if leave_id.isdigit() else False))
        .first()
    )
    if not leave:
        raise HTTPException(status_code=404, detail=f"Leave request '{leave_id}' not found.")

    current_status = str(leave.status or "Pending").strip().capitalize()
    if current_status in ["Approved", "Rejected"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Leave request '{leave_id}' is already {current_status} and cannot be processed again."
        )

    leave.status = canonical_status
    leave.reviewed_by = admin_email
    if canonical_status == "Approved":
        leave.approved_at = datetime.now(timezone.utc)
        leave.rejection_remarks = None
    else:
        leave.rejection_remarks = remarks or "Rejected by Administrator"

    db.commit()
    db.refresh(leave)
    return format_leave_response(leave)
