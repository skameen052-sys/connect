import os
from datetime import datetime, date, timezone
from typing import List, Optional, Any, Tuple, Dict
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, JSONResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, func
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.firebase import is_firebase_live, get_storage_bucket
from app.db.session import get_db
from app.models.attendance import Attendance
from app.models.attendance_photo import AttendancePhoto
from app.models.employee import Employee
from app.models.office_timing import OfficeTiming
from app.models.user import User
from app.schemas.attendance import (
    AttendanceRecordUpdate,
    AttendanceTodayStatusResponse,
    OfficeLocationResponse,
    LocationValidationRequest,
    LateReasonSubmissionRequest,
)
from app.dependencies.auth import get_current_user, get_current_admin, get_current_employee
from app.services.attendance_service import (
    get_attendance_today,
    get_attendance_now,
    format_duration_str,
    validate_and_save_attendance_photo,
    upload_to_firebase_storage,
    resolve_photo_path,
    cleanup_photo_file,
    calculate_haversine_distance_meters,
    verify_wfo_geofence,
    get_employee_authorized_work_mode,
    get_attendance_storage_dir,
)
from app.services.firestore_service import FirestoreService
from app.services.sync_service import sync_attendance_to_postgres

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/attendance", tags=["Attendance"])


def _parse_time_str(val: Any) -> str:
    """Parse Timestamp, datetime, or time string to standard human-readable format."""
    if not val:
        return "--"
    if hasattr(val, "strftime"):
        return val.strftime("%I:%M %p")
    if hasattr(val, "isoformat"):
        return val.isoformat()
    s = str(val).strip()
    if not s or s == "None":
        return "--"
    if "T" in s:
        try:
            dt = datetime.fromisoformat(s)
            return dt.strftime("%I:%M %p")
        except Exception:
            return s
    return s


def format_attendance_response(att: Any, emp: Optional[Any] = None) -> dict:
    """Format attendance record from either dict (Firestore) or ORM model (PostgreSQL)."""
    if isinstance(att, dict):
        emp_id = att.get("employee_id") or att.get("employeeId") or ""
        emp_name = att.get("employeeName") or att.get("name")
        if not emp_name:
            if isinstance(emp, dict):
                emp_name = emp.get("name") or emp.get("full_name") or emp.get("fullName")
            elif emp is not None:
                emp_name = getattr(emp, "name", None) or getattr(emp, "full_name", None)
        if not emp_name:
            emp_name = "Employee"

        emp_dept = att.get("department")
        if not emp_dept:
            if isinstance(emp, dict):
                emp_dept = emp.get("department")
            elif emp is not None:
                emp_dept = getattr(emp, "department", None)
        if not emp_dept:
            emp_dept = "Operations"

        date_val = att.get("date", "")
        if isinstance(date_val, (date, datetime)):
            date_str = date_val.isoformat()
            weekday_name = date_val.strftime("%A")
        else:
            date_str = str(date_val)
            try:
                weekday_name = date.fromisoformat(date_str).strftime("%A")
            except Exception:
                weekday_name = ""

        storage_path = (
            att.get("checkInPhotoPath")
            or att.get("check_in_photo_storage_path")
            or att.get("checkInPhotoStoragePath")
            or att.get("check_in_photo_key")
        )

        has_photo = bool(
            att.get("hasCheckInPhoto")
            or storage_path
            or att.get("check_in_photo_url")
            or att.get("checkInPhotoUrl")
            or att.get("photoUrl")
            or att.get("photoCaptured")
        )

        photo_url = att.get("check_in_photo_url") or att.get("checkInPhotoUrl") or att.get("photoUrl")
        if not photo_url and has_photo:
            photo_url = f"/api/attendance/{att.get('id')}/photo/check-in"

        emp_uid = att.get("employee_uid") or att.get("employeeUid")
        if not emp_uid and isinstance(emp, dict):
            emp_uid = emp.get("uid") or emp.get("id")

        raw_checkin = att.get("check_in_time") or att.get("checkIn") or "--"
        raw_checkout = att.get("check_out_time") or att.get("checkOut") or "--"

        checkin_str = _parse_time_str(raw_checkin) if raw_checkin != "--" else "--"
        checkout_str = _parse_time_str(raw_checkout) if raw_checkout != "--" else "--"

        return {
            "id": att.get("id"),
            "employeeId": emp_id,
            "employeeName": emp_name,
            "department": emp_dept,
            "date": date_str,
            "day": weekday_name,
            "checkIn": checkin_str,
            "checkOut": checkout_str,
            "workMode": att.get("work_mode") or att.get("workMode") or "WFO",
            "status": att.get("status", "Present"),
            "duration": att.get("duration") or "--",
            "isLate": bool(att.get("is_late") or att.get("isLate") or att.get("lateLogin")),
            "lateReason": att.get("late_reason") or att.get("lateReason") or None,
            "lateReasonStatus": att.get("late_reason_status") or att.get("lateReasonStatus") or ("SUBMITTED" if (att.get("late_reason") or att.get("lateReason")) else ("PENDING" if (att.get("is_late") or att.get("isLate") or att.get("lateLogin")) else "NOT_REQUIRED")),
            "lateReasonSubmittedAt": att.get("late_reason_submitted_at") or att.get("lateReasonSubmittedAt") or None,
            "checkInLatitude": att.get("check_in_latitude") or att.get("checkInLatitude"),
            "checkInLongitude": att.get("check_in_longitude") or att.get("checkInLongitude"),
            "checkInLocationAccuracy": att.get("check_in_location_accuracy") or att.get("checkInLocationAccuracy"),
            "checkOutLatitude": att.get("check_out_latitude") or att.get("checkOutLatitude"),
            "checkOutLongitude": att.get("check_out_longitude") or att.get("checkOutLongitude"),
            "hasCheckInPhoto": has_photo,
            "hasCheckOutPhoto": bool(att.get("hasCheckOutPhoto") or att.get("check_out_photo_key")),
            "checkInPhotoPath": storage_path,
            "photoPath": storage_path,
            "checkInPhotoUrl": photo_url,
            "photoUrl": photo_url,
            "employeeUid": emp_uid,
        }

    # SQLAlchemy model handling
    emp_name = emp.full_name if emp else (att.employee.full_name if att.employee else "Employee")
    emp_dept = emp.department if emp else (att.employee.department if att.employee else "Operations")
    weekday_name = att.date.strftime("%A") if att.date else ""
    is_rec_late = bool(att.is_late or (att.status and att.status.lower() == "late"))
    late_reason_val = getattr(att, "late_reason", None)
    late_status_val = "SUBMITTED" if late_reason_val else ("PENDING" if is_rec_late else "NOT_REQUIRED")
    submitted_at_val = getattr(att, "late_reason_submitted_at", None)

    return {
        "id": att.id,
        "employeeId": att.employee_id,
        "employeeName": emp_name,
        "department": emp_dept,
        "date": att.date.isoformat() if att.date else "",
        "day": weekday_name,
        "checkIn": att.check_in_time or "--",
        "checkOut": att.check_out_time or "--",
        "workMode": att.work_mode,
        "status": att.status,
        "duration": att.duration or "--",
        "isLate": is_rec_late,
        "lateReason": late_reason_val or None,
        "lateReasonStatus": late_status_val,
        "lateReasonSubmittedAt": submitted_at_val.isoformat() if submitted_at_val else None,
        "checkInLatitude": att.check_in_latitude,
        "checkInLongitude": att.check_in_longitude,
        "checkInLocationAccuracy": att.check_in_location_accuracy,
        "checkOutLatitude": att.check_out_latitude,
        "checkOutLongitude": att.check_out_longitude,
        "hasCheckInPhoto": bool(
            att.check_in_photo_data is not None
            or att.check_in_photo_key
            or (hasattr(att, "photos") and bool(att.photos))
        ),
        "hasCheckOutPhoto": bool(
            att.check_out_photo_data is not None
            or att.check_out_photo_key
        ),
    }


def is_checkin_late(now: datetime, db: Session = None) -> bool:
    """
    Check if check-in time is past office start time in configured timezone (9:30 AM IST).
    Rule:
    - Before or at 9:30 AM IST: on-time (is_late=False)
    - After 9:30 AM IST: late (is_late=True, mandatory late reason required)
    """
    start_str = "09:30"
    if db is not None:
        try:
            if settings.DATABASE_BACKEND == "firebase":
                timings = FirestoreService.query("office_timings", {"timing_type": "REGULAR"})
                if timings:
                    start_str = timings[0].get("start_time", "09:30")
            else:
                timing = db.query(OfficeTiming).filter(OfficeTiming.timing_type == "REGULAR").first()
                if timing and timing.start_time:
                    start_str = timing.start_time
        except Exception:
            pass

    try:
        sh, sm = [int(p) for p in start_str.split(":")]
        cutoff_minutes = sh * 60 + sm
        current_minutes = now.hour * 60 + now.minute
        return current_minutes > cutoff_minutes
    except Exception:
        return (now.hour * 60 + now.minute) > (9 * 60 + 30)


@router.get("", response_model=List[dict])
@router.get("/records", response_model=List[dict])
@router.get("/history", response_model=List[dict])
def get_attendance_records(
    search: Optional[str] = Query(None),
    workMode: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    record_date: Optional[str] = Query(None, alias="date"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get all attendance records across both mobile and web via Firestore or PostgreSQL."""
    if settings.DATABASE_BACKEND == "firebase":
        top_records = FirestoreService.list_all("attendance")
        cg_records = FirestoreService.collection_group("records")

        all_emps = {}
        for e in FirestoreService.list_all("employees"):
            for k in ("employee_id", "employeeId", "id", "uid", "_firestore_id"):
                val = e.get(k)
                if val:
                    all_emps[str(val)] = e
            if e.get("email"):
                all_emps[str(e["email"]).lower().strip()] = e

        merged = {}
        for r in top_records:
            emp_id = r.get("employee_id") or r.get("employeeId") or r.get("employee_uid") or ""
            dt = str(r.get("date", "")).strip()
            key = f"{emp_id}_{dt}"
            merged[key] = r

        for cr in cg_records:
            eid = cr.get("employeeId") or cr.get("employee_id") or cr.get("uid") or ""
            dt = str(cr.get("date", "")).strip()
            key = f"{eid}_{dt}"
            emp = all_emps.get(str(eid)) or all_emps.get(str(cr.get("email", "")).lower().strip()) or {}
            real_emp_id = emp.get("employeeId") or emp.get("employee_id") or eid
            real_key = f"{real_emp_id}_{dt}"

            if real_key not in merged and key not in merged:
                real_name = emp.get("name") or emp.get("fullName") or emp.get("full_name") or cr.get("name") or "Employee"
                real_dept = emp.get("department") or "Operations"
                check_in_str = _parse_time_str(cr.get("checkIn") or cr.get("check_in_time"))
                check_out_str = _parse_time_str(cr.get("checkOut") or cr.get("check_out_time"))

                merged[real_key] = {
                    "id": f"{real_emp_id}_{dt}",
                    "employee_id": real_emp_id,
                    "employeeId": real_emp_id,
                    "employee_uid": eid,
                    "employeeUid": eid,
                    "employeeName": real_name,
                    "name": real_name,
                    "department": real_dept,
                    "date": dt,
                    "check_in_time": check_in_str,
                    "check_out_time": check_out_str,
                    "work_mode": cr.get("workMode") or cr.get("work_mode") or "WFO",
                    "status": cr.get("status", "Present"),
                    "is_late": bool(cr.get("lateLogin") or cr.get("is_late")),
                    "check_in_photo_url": cr.get("checkInPhotoUrl") or cr.get("photoUrl"),
                    "checkInPhotoUrl": cr.get("checkInPhotoUrl") or cr.get("photoUrl"),
                    "hasCheckInPhoto": bool(cr.get("checkInPhotoUrl") or cr.get("photoCaptured")),
                    "duration": cr.get("duration") or "--",
                }
            else:
                target_key = real_key if real_key in merged else key
                if not merged[target_key].get("check_in_photo_url") and cr.get("checkInPhotoUrl"):
                    merged[target_key]["check_in_photo_url"] = cr["checkInPhotoUrl"]
                    merged[target_key]["checkInPhotoUrl"] = cr["checkInPhotoUrl"]
                    merged[target_key]["hasCheckInPhoto"] = True
                if (not merged[target_key].get("check_out_time") or merged[target_key].get("check_out_time") == "--") and cr.get("checkOut"):
                    merged[target_key]["check_out_time"] = _parse_time_str(cr["checkOut"])
                if cr.get("duration") and cr.get("duration") != "--":
                    merged[target_key]["duration"] = cr.get("duration")

        records = list(merged.values())

        filtered = []
        for r in records:
            emp_id = r.get("employee_id") or r.get("employeeId") or r.get("employee_uid") or r.get("employeeUid")
            emp = all_emps.get(str(emp_id), {}) if emp_id else {}
            emp_name = (
                r.get("employeeName")
                or r.get("name")
                or emp.get("name")
                or emp.get("full_name")
                or emp.get("fullName")
                or ""
            )
            emp_dept = r.get("department") or emp.get("department") or ""

            if search:
                s = search.strip().lower()
                if not (s in emp_name.lower() or s in str(emp_id).lower() or s in emp_dept.lower()):
                    continue

            if workMode and workMode not in ["ALL", "All Modes", "All"]:
                if str(r.get("work_mode", "")).strip().upper() != workMode.strip().upper():
                    continue

            if status_filter and status_filter.upper() != "ALL":
                if str(r.get("status", "")).strip().lower() != status_filter.strip().lower():
                    continue

            if record_date:
                if str(r.get("date", "")).strip() != record_date.strip():
                    continue

            filtered.append(format_attendance_response(r, emp))

        filtered.sort(key=lambda x: str(x.get("date", "")), reverse=True)
        return filtered

    # PostgreSQL fallback
    query = db.query(Attendance).join(Employee, Attendance.employee_id == Employee.employee_id)
    if search:
        s = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                Employee.full_name.ilike(s),
                Employee.employee_id.ilike(s),
                Employee.department.ilike(s),
            )
        )
    if workMode and workMode not in ["ALL", "All Modes", "All"]:
        query = query.filter(Attendance.work_mode == workMode.strip())
    if status_filter and status_filter.upper() != "ALL":
        query = query.filter(Attendance.status.ilike(status_filter.strip()))
    if record_date:
        try:
            d = date.fromisoformat(record_date)
            query = query.filter(Attendance.date == d)
        except ValueError:
            pass

    records = query.order_by(desc(Attendance.date), desc(Attendance.id)).all()
    return [format_attendance_response(r) for r in records]


@router.get("/me", response_model=List[dict])
def get_my_attendance_history(
    month: Optional[str] = Query(None),
    workMode: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    employee=Depends(get_current_employee),
):
    """Get personal attendance records for the authenticated employee across mobile and web."""
    emp_id = getattr(employee, "employee_id", None) or getattr(employee, "employeeId", None)

    if settings.DATABASE_BACKEND == "firebase":
        emp_uid = str(getattr(employee, "uid", None) or getattr(employee, "id", None) or emp_id)
        records_top = FirestoreService.query("attendance", {"employee_id": emp_id})
        cg_records = FirestoreService.collection_group("records")

        merged = {}
        for r in records_top:
            dt = str(r.get("date", "")).strip()
            merged[dt] = r

        for cr in cg_records:
            c_eid = str(cr.get("employeeId") or cr.get("employee_id") or cr.get("uid") or "")
            if c_eid in [str(emp_id), str(emp_uid)]:
                dt = str(cr.get("date", "")).strip()
                if dt not in merged:
                    merged[dt] = {
                        "id": f"{emp_id}_{dt}",
                        "employee_id": emp_id,
                        "employeeId": emp_id,
                        "employee_uid": emp_uid,
                        "date": dt,
                        "check_in_time": _parse_time_str(cr.get("checkIn") or cr.get("check_in_time")),
                        "check_out_time": _parse_time_str(cr.get("checkOut") or cr.get("check_out_time")),
                        "work_mode": cr.get("workMode") or cr.get("work_mode") or "WFO",
                        "status": cr.get("status", "Present"),
                        "is_late": bool(cr.get("lateLogin") or cr.get("is_late")),
                        "check_in_photo_url": cr.get("checkInPhotoUrl"),
                        "checkInPhotoUrl": cr.get("checkInPhotoUrl"),
                        "hasCheckInPhoto": bool(cr.get("checkInPhotoUrl") or cr.get("photoCaptured")),
                        "duration": cr.get("duration") or "--",
                    }

        records = list(merged.values())
        filtered = []
        for r in records:
            if workMode and workMode != "All":
                if str(r.get("work_mode", "")).strip().upper() != workMode.strip().upper():
                    continue
            filtered.append(format_attendance_response(r, employee))
        filtered.sort(key=lambda x: str(x.get("date", "")), reverse=True)
        return filtered

    # PostgreSQL fallback
    query = db.query(Attendance).filter(Attendance.employee_id == emp_id)
    if workMode and workMode != "All":
        query = query.filter(Attendance.work_mode == workMode)

    records = query.order_by(desc(Attendance.date), desc(Attendance.id)).all()
    return [format_attendance_response(r, employee) for r in records]


@router.get("/office-location", response_model=OfficeLocationResponse)
def get_office_location():
    """
    Authoritative company office location and geofence parameters.
    Reads dynamically from Firestore office_config or falls back to backend settings.
    """
    if settings.DATABASE_BACKEND == "firebase":
        conf = FirestoreService.get_by_id("office_config", "main_office")
        if conf:
            return OfficeLocationResponse(
                officeName=conf.get("officeName", settings.COMPANY_OFFICE_NAME or "HQ Office"),
                address=conf.get("officeAddress", settings.COMPANY_OFFICE_ADDRESS or "Bengaluru, Karnataka"),
                latitude=conf.get("latitude", settings.COMPANY_OFFICE_LATITUDE),
                longitude=conf.get("longitude", settings.COMPANY_OFFICE_LONGITUDE),
                radiusMeters=conf.get("radiusMeters", settings.OFFICE_GEOFENCE_RADIUS_METERS),
                maxAccuracyMeters=conf.get("maxAccuracyMeters", settings.MAX_GPS_ACCURACY_METERS),
                timezone=conf.get("timezone", settings.ATTENDANCE_TIMEZONE),
            )

    return OfficeLocationResponse(
        officeName=settings.COMPANY_OFFICE_NAME,
        address=settings.COMPANY_OFFICE_ADDRESS,
        latitude=settings.COMPANY_OFFICE_LATITUDE,
        longitude=settings.COMPANY_OFFICE_LONGITUDE,
        radiusMeters=settings.OFFICE_GEOFENCE_RADIUS_METERS,
        maxAccuracyMeters=settings.MAX_GPS_ACCURACY_METERS,
        timezone=settings.ATTENDANCE_TIMEZONE,
    )


@router.post("/validate-location")
def validate_location(
    data: LocationValidationRequest,
    db: Session = Depends(get_db),
    employee=Depends(get_current_employee),
):
    """
    Authoritative backend pre-validation of employee GPS coordinates against configured office geofence.
    """
    target_mode = (data.workMode or "WFO").strip().upper()
    if "WFH" in target_mode:
        target_mode = "WFH"
    elif "WFO" in target_mode:
        target_mode = "WFO"
    else:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "valid": False,
                "code": "INVALID_WORK_MODE",
                "message": "Invalid work mode. Supported values are 'WFO' and 'WFH'.",
            },
        )

    if target_mode == "WFH":
        return {
            "valid": True,
            "workMode": "WFH",
            "isInsideOffice": True,
            "message": "Work From Home attendance permitted without office geofence restriction.",
            "distanceMeters": None,
            "allowedRadiusMeters": settings.OFFICE_GEOFENCE_RADIUS_METERS,
        }

    if data.latitude is None or data.longitude is None or data.accuracy is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "valid": False,
                "code": "MISSING_COORDINATES",
                "message": "GPS coordinates are required for Work From Office (WFO) verification.",
                "workMode": "WFO",
            },
        )

    report = verify_wfo_geofence(data.latitude, data.longitude, data.accuracy)
    if not report["valid"]:
        if report["code"] == "OUTSIDE_OFFICE_GEOFENCE":
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "valid": False,
                    "code": "OUTSIDE_OFFICE_GEOFENCE",
                    "message": report["message"],
                    "distanceMeters": report["distanceMeters"],
                    "allowedRadiusMeters": report["allowedRadiusMeters"],
                    "workMode": "WFO",
                },
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "valid": False,
                    "code": report["code"],
                    "message": report["message"],
                    "accuracy": report["accuracy"],
                    "maxAllowedAccuracy": report["maxAllowedAccuracy"],
                    "workMode": "WFO",
                },
            )

    return {
        "valid": True,
        "workMode": "WFO",
        "isInsideOffice": True,
        "distanceMeters": report["distanceMeters"],
        "allowedRadiusMeters": report["allowedRadiusMeters"],
        "message": report["message"],
    }


@router.get("/today", response_model=AttendanceTodayStatusResponse)
@router.get("/today-status", response_model=AttendanceTodayStatusResponse)
def get_today_attendance_status(
    db: Session = Depends(get_db),
    employee=Depends(get_current_employee),
):
    """Retrieve today's live check-in and punch state for the logged-in employee."""
    emp_id = getattr(employee, "employee_id", None) or getattr(employee, "employeeId", None)
    today = get_attendance_today()
    today_iso = today.isoformat()

    auth_mode = "WFO"
    try:
        auth_mode = get_employee_authorized_work_mode(employee)
    except Exception:
        auth_mode = "WFO"

    if settings.DATABASE_BACKEND == "firebase":
        records = FirestoreService.query("attendance", {"employee_id": emp_id, "date": today_iso})
        if not records:
            records = FirestoreService.query("attendance", {"employeeId": emp_id, "date": today_iso})
        if not records:
            direct_doc = FirestoreService.get_by_id("attendance", f"{emp_id}_{today_iso}")
            if direct_doc:
                records = [direct_doc]
        record = records[0] if records else None

        emp_uid = str(getattr(employee, "uid", None) or getattr(employee, "id", None) or emp_id)
        cg_today = FirestoreService.collection_group("records", [("date", "==", today_iso)])
        mobile_rec = None
        for cr in cg_today:
            c_eid = str(cr.get("employeeId") or cr.get("employee_id") or cr.get("uid") or "")
            if c_eid in [str(emp_id), str(emp_uid)]:
                mobile_rec = cr
                break

        if not record and mobile_rec:
            record = {
                "id": f"{emp_id}_{today_iso}",
                "employee_id": emp_id,
                "date": today_iso,
                "check_in_time": _parse_time_str(mobile_rec.get("checkIn") or mobile_rec.get("check_in_time")),
                "check_out_time": _parse_time_str(mobile_rec.get("checkOut") or mobile_rec.get("check_out_time")),
                "work_mode": mobile_rec.get("workMode") or mobile_rec.get("work_mode") or auth_mode,
                "status": mobile_rec.get("status", "Present"),
                "is_late": bool(mobile_rec.get("lateLogin") or mobile_rec.get("is_late")),
                "hasCheckInPhoto": bool(mobile_rec.get("checkInPhotoUrl") or mobile_rec.get("photoCaptured")),
                "check_in_photo_url": mobile_rec.get("checkInPhotoUrl"),
                "duration": mobile_rec.get("duration") or "--",
            }
        elif record and mobile_rec:
            mob_out = mobile_rec.get("checkOut") or mobile_rec.get("check_out_time")
            if mob_out and (not record.get("check_out_time") or record.get("check_out_time") == "--"):
                out_str = _parse_time_str(mob_out)
                record["check_out_time"] = out_str
                record["status"] = "Completed"
                if mobile_rec.get("duration") and mobile_rec.get("duration") != "--":
                    record["duration"] = mobile_rec["duration"]
                FirestoreService.update("attendance", record.get("id") or f"{emp_id}_{today_iso}", {
                    "check_out_time": out_str,
                    "status": "Completed",
                    "duration": record.get("duration", "--"),
                    "is_completed": True,
                })

        if record:
            sync_attendance_to_postgres(
                emp_id=emp_id,
                att_date=today,
                check_in_time=record.get("check_in_time"),
                check_out_time=record.get("check_out_time"),
                duration=record.get("duration"),
                work_mode=record.get("work_mode", "WFO"),
                status_str=record.get("status", "Present"),
                is_late=bool(record.get("is_late")),
                db=db,
            )

        if not record:
            return AttendanceTodayStatusResponse(
                id=None,
                hasRecord=False,
                isCheckedIn=False,
                isCompleted=False,
                checkInTime="--",
                checkOutTime="--",
                workMode=auth_mode,
                authorizedWorkMode=auth_mode,
                workingDuration="--",
                status="Not Checked In",
                date=today_iso,
                isLate=False,
                checkInTimestamp=None,
                checkOutTimestamp=None,
                checkInLatitude=None,
                checkInLongitude=None,
                checkInLocationAccuracy=None,
                hasCheckInPhoto=False,
                hasCheckOutPhoto=False,
                canCheckIn=True,
                canCheckOut=False,
            )

        is_completed = bool(record.get("check_out_time"))
        is_checked_in = bool(record.get("check_in_time") and not is_completed)
        status_display = "Completed" if is_completed else record.get("status", "Present")
        is_rec_late = bool(record.get("is_late") or record.get("isLate") or record.get("lateLogin"))
        late_reason_val = record.get("late_reason") or record.get("lateReason")
        late_status_val = record.get("late_reason_status") or record.get("lateReasonStatus")
        if not late_status_val:
            if late_reason_val:
                late_status_val = "SUBMITTED"
            elif is_rec_late:
                late_status_val = "PENDING"
            else:
                late_status_val = "NOT_REQUIRED"

        return AttendanceTodayStatusResponse(
            id=record.get("id"),
            hasRecord=True,
            isCheckedIn=is_checked_in,
            isCompleted=is_completed,
            checkInTime=record.get("check_in_time") or "--",
            checkOutTime=record.get("check_out_time") or "--",
            workMode=record.get("work_mode", auth_mode),
            authorizedWorkMode=auth_mode,
            workingDuration=record.get("duration") or "--",
            status=status_display,
            date=today_iso,
            isLate=is_rec_late,
            lateReason=late_reason_val or None,
            lateReasonStatus=late_status_val,
            lateReasonSubmittedAt=record.get("late_reason_submitted_at") or record.get("lateReasonSubmittedAt") or None,
            checkInTimestamp=record.get("check_in_timestamp"),
            checkOutTimestamp=record.get("check_out_timestamp"),
            checkInLatitude=record.get("check_in_latitude"),
            checkInLongitude=record.get("check_in_longitude"),
            hasCheckInPhoto=bool(
                record.get("hasCheckInPhoto")
                or record.get("check_in_photo_key")
                or record.get("check_in_photo_storage_path")
                or record.get("check_in_photo_url")
            ),
            hasCheckOutPhoto=bool(record.get("hasCheckOutPhoto") or record.get("check_out_photo_key")),
            canCheckIn=False,
            canCheckOut=is_checked_in,
        )

    # PostgreSQL fallback
    record = (
        db.query(Attendance)
        .filter(Attendance.employee_id == emp_id, Attendance.date == today)
        .first()
    )

    if not record:
        return AttendanceTodayStatusResponse(
            id=None,
            hasRecord=False,
            isCheckedIn=False,
            isCompleted=False,
            checkInTime="--",
            checkOutTime="--",
            workMode=auth_mode,
            authorizedWorkMode=auth_mode,
            workingDuration="--",
            status="Not Checked In",
            date=today_iso,
            isLate=False,
            lateReason=None,
            lateReasonStatus="NOT_REQUIRED",
            lateReasonSubmittedAt=None,
            checkInTimestamp=None,
            checkOutTimestamp=None,
            checkInLatitude=None,
            checkInLongitude=None,
            checkInLocationAccuracy=None,
            hasCheckInPhoto=False,
            hasCheckOutPhoto=False,
            canCheckIn=True,
            canCheckOut=False,
        )

    is_completed = bool(record.check_out_time)
    is_checked_in = bool(record.check_in_time and not is_completed)
    status_display = "Completed" if is_completed else record.status
    is_rec_late = bool(record.is_late or (record.status and record.status.lower() == "late"))
    late_reason_val = getattr(record, "late_reason", None)
    late_status_val = "SUBMITTED" if late_reason_val else ("PENDING" if is_rec_late else "NOT_REQUIRED")
    submitted_at_val = getattr(record, "late_reason_submitted_at", None)

    return AttendanceTodayStatusResponse(
        id=record.id,
        hasRecord=True,
        isCheckedIn=is_checked_in,
        isCompleted=is_completed,
        checkInTime=record.check_in_time or "--",
        checkOutTime=record.check_out_time or "--",
        workMode=record.work_mode,
        authorizedWorkMode=auth_mode,
        workingDuration=record.duration or "--",
        status=status_display,
        date=today_iso,
        isLate=is_rec_late,
        lateReason=late_reason_val or None,
        lateReasonStatus=late_status_val,
        lateReasonSubmittedAt=submitted_at_val.isoformat() if submitted_at_val else None,
        checkInTimestamp=record.check_in_timestamp.isoformat() if record.check_in_timestamp else None,
        checkOutTimestamp=record.check_out_timestamp.isoformat() if record.check_out_timestamp else None,
        checkInLatitude=record.check_in_latitude,
        checkInLongitude=record.check_in_longitude,
        hasCheckInPhoto=bool(
            record.check_in_photo_data is not None
            or record.check_in_photo_key
            or (hasattr(record, "photos") and bool(record.photos))
        ),
        hasCheckOutPhoto=bool(record.check_out_photo_data is not None or record.check_out_photo_key),
        canCheckIn=False,
        canCheckOut=is_checked_in,
    )



def resolve_employee_for_attendance(
    current_user: Any,
    param_emp_id: Optional[str] = None,
    db: Optional[Session] = None,
) -> Tuple[Any, str, str]:
    """
    Authoritative resolution of employee profile for attendance check-in, check-out, and status.
    Returns: (employee_record_dict_or_object, canonical_employee_id, canonical_uid)
    """
    user_role = str(getattr(current_user, "role", "employee")).strip().lower()
    user_id = getattr(current_user, "id", None) or getattr(current_user, "uid", None)
    user_email = str(getattr(current_user, "email", "")).strip().lower()

    # 1. Admin punch-in on behalf of employee
    if user_role == "admin":
        if not param_emp_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employee ID is required for administrative attendance actions.",
            )
        emp_id = str(param_emp_id).strip()
        if settings.DATABASE_BACKEND == "firebase":
            emp = FirestoreService.get_by_id("employees", emp_id)
            if not emp:
                matches = FirestoreService.query("employees", {"employee_id": emp_id})
                if not matches:
                    matches = FirestoreService.query("employees", {"employeeId": emp_id})
                if not matches:
                    matches = FirestoreService.query("employees", {"uid": emp_id})
                if not matches:
                    matches = FirestoreService.query("employees", {"email": emp_id.lower()})
                emp = matches[0] if matches else None
            if not emp:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Target employee '{emp_id}' could not be identified.",
                )
            emp_uid = str(emp.get("uid") or emp.get("id") or emp_id)
            canonical_emp_id = str(emp.get("employee_id") or emp.get("employeeId") or emp_id)
            return emp, canonical_emp_id, emp_uid
        else:
            emp = db.query(Employee).filter(
                (Employee.employee_id == emp_id) |
                (Employee.email == emp_id.lower())
            ).first() if db else None
            if not emp:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Target employee '{emp_id}' could not be identified.",
                )
            return emp, emp.employee_id, str(emp.user_id or emp.employee_id)

    # 2. Employee attendance actions
    if user_role != "employee":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employee access required to punch attendance.",
        )

    # Check status from current_user
    status_val = str(
        getattr(current_user, "status", None)
        or getattr(current_user, "approval_status", "active")
    ).strip().lower()

    if status_val in ["pending", "under_review", "pending_approval"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your registration is pending Admin approval. Please wait until your account is approved.",
        )
    if status_val == "rejected":
        reason = getattr(current_user, "rejection_reason", None)
        detail_msg = "Your registration request was not approved. Please contact company administration."
        if reason:
            detail_msg += f" Reason: {reason}"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail_msg,
        )
    if getattr(current_user, "is_active", True) is False or status_val in ["inactive", "disabled", "suspended"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your employee account is currently inactive. Please contact administration.",
        )

    user_emp_code = str(
        getattr(current_user, "employee_id", None)
        or getattr(current_user, "employeeId", None)
        or (param_emp_id if param_emp_id else "")
        or ""
    ).strip()

    if settings.DATABASE_BACKEND == "firebase":
        emp = None
        # Step A: Lookup by UID document ID (Android canonical format)
        if user_id:
            emp = FirestoreService.get_by_id("employees", str(user_id))
        # Step B: Lookup by employeeId document ID
        if not emp and user_emp_code:
            emp = FirestoreService.get_by_id("employees", str(user_emp_code))
        # Step C: Lookup by email field
        if not emp and user_email:
            matches = FirestoreService.query("employees", {"email": user_email})
            if matches:
                emp = matches[0]
        # Step D: Lookup by uid field
        if not emp and user_id:
            matches = FirestoreService.query("employees", {"uid": str(user_id)})
            if matches:
                emp = matches[0]
        # Step E: Lookup by user_id field
        if not emp and user_id:
            matches = FirestoreService.query("employees", {"user_id": user_id})
            if matches:
                emp = matches[0]
        # Step F: Lookup by employeeId field
        if not emp and user_emp_code:
            matches = FirestoreService.query("employees", {"employeeId": str(user_emp_code)})
            if matches:
                emp = matches[0]
        # Step G: Lookup by employee_id field
        if not emp and user_emp_code:
            matches = FirestoreService.query("employees", {"employee_id": str(user_emp_code)})
            if matches:
                emp = matches[0]
        # Step H: Case-insensitive email query fallback
        if not emp and user_email:
            all_emps = FirestoreService.list_all("employees")
            for e in all_emps:
                if str(e.get("email", "")).lower().strip() == user_email:
                    emp = e
                    break

        # Fallback for authenticated, approved users whose employee profile document was missing
        if not emp:
            user_doc = None
            if user_id:
                user_doc = FirestoreService.get_by_id("users", str(user_id))
            if not user_doc and user_email:
                u_matches = FirestoreService.query("users", {"email": user_email})
                if u_matches:
                    user_doc = u_matches[0]

            req_matches = FirestoreService.query("registration_requests", {"email": user_email}) if user_email else []
            target_req = req_matches[0] if req_matches else None

            # Check if pending or rejected in user_doc / target_req
            u_status = str(
                (user_doc.get("status") or user_doc.get("approval_status") if user_doc else None)
                or (target_req.get("status") if target_req else None)
                or ""
            ).strip().lower()

            if u_status in ["pending", "under_review", "pending_approval"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Your registration is pending Admin approval. Please wait until your account is approved.",
                )
            if u_status == "rejected":
                reason = (user_doc.get("rejection_reason") if user_doc else None) or (target_req.get("rejection_reason") if target_req else None)
                detail_msg = "Your registration request was not approved. Please contact company administration."
                if reason:
                    detail_msg += f" Reason: {reason}"
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=detail_msg,
                )

            if not user_doc and not target_req:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee profile not found.")

            # Verify the record is actually approved
            is_record_approved = (
                (user_doc and str(user_doc.get("status", "") or user_doc.get("approval_status", "")).strip().lower() in ["approved", "active"])
                or (target_req and str(target_req.get("status", "")).strip().lower() in ["approved", "active"])
            )
            if not is_record_approved:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Your registration is pending Admin approval. Please wait until your account is approved.",
                )

            # If authenticated user is approved, synthesize and persist employee profile to employees collection
            canonical_id = str(user_id or (user_doc.get("id") if user_doc else None) or "emp_user")
            canonical_code = (
                user_emp_code
                or (str(user_doc.get("employeeId") or user_doc.get("employee_id") or "") if user_doc else "")
                or (str(target_req.get("employeeId") or target_req.get("employee_id") or "") if target_req else "")
                or f"AFI-{canonical_id[:6].upper()}"
            )
            emp_name = (
                (user_doc.get("name") or user_doc.get("fullName") if user_doc else None)
                or (target_req.get("full_name") or target_req.get("name") if target_req else None)
                or getattr(current_user, "name", None)
                or "Employee"
            )
            phone = (
                (target_req.get("phone") if target_req else None)
                or (user_doc.get("phone") if user_doc else None)
                or "--"
            )
            dept = (user_doc.get("department") if user_doc else None) or (target_req.get("department") if target_req else None) or "Operations"
            desig = (user_doc.get("designation") if user_doc else None) or (target_req.get("designation") if target_req else None) or "Operations Associate"
            now_iso = datetime.now(timezone.utc).isoformat()

            emp = {
                "id": canonical_id,
                "uid": canonical_id,
                "user_id": canonical_id,
                "employeeId": canonical_code,
                "employee_id": canonical_code,
                "name": emp_name,
                "fullName": emp_name,
                "full_name": emp_name,
                "email": user_email,
                "phone": phone,
                "role": "Employee",
                "department": dept,
                "designation": desig,
                "status": "approved",
                "shift": "General (09:30 AM - 06:30 PM)",
                "location": "HQ Office",
                "createdAt": now_iso,
                "created_at": now_iso,
                "updated_at": now_iso,
            }
            try:
                FirestoreService.save("employees", canonical_id, emp)
                logger.info(f"[Attendance] Successfully synchronized approved employee profile into 'employees' collection: {canonical_id} ({user_email})")
            except Exception as save_err:
                logger.warning(f"[Attendance] Could not persist employee document: {save_err}")

        # Final validation of resolved emp object
        emp_status = str(emp.get("status", "active")).strip().lower()
        if emp_status in ["pending", "under_review", "pending_approval"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your registration is pending Admin approval. Please wait until your account is approved.",
            )
        if emp_status == "rejected":
            reason = emp.get("rejection_reason") or emp.get("rejectionReason")
            msg = "Your registration request was not approved. Please contact company administration."
            if reason:
                msg += f" Reason: {reason}"
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=msg,
            )
        if emp_status in ["inactive", "disabled", "suspended"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your employee account is currently inactive. Please contact administration.",
            )

        resolved_id = str(emp.get("employee_id") or emp.get("employeeId") or user_emp_code or user_id)
        resolved_uid = str(emp.get("uid") or emp.get("id") or user_id or resolved_id)
        return emp, resolved_id, resolved_uid

    else:
        # PostgreSQL Backend
        emp = None
        if user_id:
            emp = db.query(Employee).filter(Employee.user_id == user_id).first() if db else None
        if not emp and user_email:
            emp = db.query(Employee).filter(func.lower(func.trim(Employee.email)) == user_email).first() if db else None
        if not emp and user_emp_code:
            emp = db.query(Employee).filter(func.upper(func.trim(Employee.employee_id)) == user_emp_code.upper()).first() if db else None

        if not emp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee profile not found.")

        emp_status = str(emp.status or "Active").strip().lower()
        if emp_status in ["pending"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your registration is pending Admin approval. Please wait until your account is approved.",
            )
        if emp_status in ["rejected"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your registration request was not approved. Please contact company administration.",
            )
        if emp_status in ["inactive"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your employee account is currently inactive. Please contact administration.",
            )

        resolved_id = emp.employee_id
        resolved_uid = str(emp.user_id or emp.employee_id)
        return emp, resolved_id, resolved_uid


@router.post("/check-in", status_code=status.HTTP_200_OK)
async def check_in(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Record daily attendance punch-in.
    Validates work mode, geofence (for WFO), camera photo upload to Cloud Storage,
    and commits record and photo metadata to Cloud Firestore.
    """
    user_role = getattr(current_user, "role", "employee")
    user_id = getattr(current_user, "id", None)
    user_email = getattr(current_user, "email", "")

    # 1. Parse request (multipart/form-data or json)
    content_type = request.headers.get("content-type", "").lower()
    photo_file = None
    lat_val = None
    lon_val = None
    acc_val = None
    requested_work_mode = None
    param_emp_id = None

    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        photo_file = form.get("photo") or form.get("file") or form.get("image") or form.get("photo_data") or form.get("photoData")
        lat_val = form.get("latitude")
        lon_val = form.get("longitude")
        acc_val = form.get("accuracy")
        requested_work_mode = form.get("workMode")
        param_emp_id = form.get("employeeId")
        late_reason_param = form.get("lateReason") or form.get("late_reason")
    else:
        try:
            body = await request.json()
            photo_file = (
                body.get("photo")
                or body.get("image")
                or body.get("photoData")
                or body.get("photo_data")
                or body.get("photoBase64")
                or body.get("file")
            )
            lat_val = body.get("latitude")
            lon_val = body.get("longitude")
            acc_val = body.get("accuracy")
            requested_work_mode = body.get("workMode")
            param_emp_id = body.get("employeeId")
            late_reason_param = body.get("lateReason") or body.get("late_reason")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid request format. Expected multipart/form-data or application/json.",
            )

    # 2. Resolve employee identity
    emp, emp_id, emp_uid = resolve_employee_for_attendance(
        current_user=current_user,
        param_emp_id=param_emp_id,
        db=db,
    )

    if not emp_id or not emp:
        raise HTTPException(status_code=404, detail="Target employee could not be identified.")

    # 3. Work mode resolution
    work_mode = "WFO"
    if requested_work_mode:
        clean_req_mode = str(requested_work_mode).strip().upper()
        if "WFH" in clean_req_mode:
            work_mode = "WFH"
        elif "WFO" in clean_req_mode:
            work_mode = "WFO"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_WORK_MODE", "message": "Invalid work mode. Must be 'WFO' or 'WFH'."},
            )

    today = get_attendance_today()
    today_iso = today.isoformat()
    now_local = get_attendance_now()
    now_utc = datetime.now(timezone.utc)
    time_str = now_local.strftime("%I:%M %p")

    # 4. Daily lock validation
    if settings.DATABASE_BACKEND == "firebase":
        existing_records = FirestoreService.query("attendance", {"employee_id": emp_id, "date": today_iso})
        existing = existing_records[0] if existing_records else None
    else:
        existing = db.query(Attendance).filter(Attendance.employee_id == emp_id, Attendance.date == today).first()

    if existing:
        chk_out = existing.get("check_out_time") if isinstance(existing, dict) else existing.check_out_time
        chk_in = existing.get("check_in_time") if isinstance(existing, dict) else existing.check_in_time
        st = existing.get("status") if isinstance(existing, dict) else existing.status
        if chk_out or st == "Completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Attendance already completed for today. New check-in is not permitted until tomorrow.",
            )
        if chk_in:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already checked in for today.",
            )

    # 5. GPS location validation
    lat, lon, acc = None, None, None
    if work_mode == "WFO":
        if lat_val is None or lon_val is None or acc_val is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GPS coordinates (latitude, longitude, accuracy) are required for Work From Office (WFO) check-in.",
            )
        try:
            lat = float(lat_val)
            lon = float(lon_val)
            acc = float(acc_val)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Latitude, longitude, and accuracy must be valid decimal numbers.",
            )

        geofence_report = verify_wfo_geofence(lat, lon, acc)
        if not geofence_report["valid"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN if geofence_report["code"] == "OUTSIDE_OFFICE_GEOFENCE" else status.HTTP_400_BAD_REQUEST,
                detail=geofence_report,
            )
    else:
        if lat_val is not None and lon_val is not None and str(lat_val).strip() != "":
            try:
                lat = float(lat_val)
                lon = float(lon_val)
                acc = float(acc_val) if acc_val is not None else 0.0
            except (ValueError, TypeError):
                pass

    # 6. Validate photograph
    if photo_file is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attendance selfie photograph is strictly required for check-in verification.",
        )

    storage_key, photo_bytes, photo_mime = await validate_and_save_attendance_photo(
        photo_file,
        photo_type="check_in",
        attendance_date=today,
    )

    # 7. Evaluate lateness
    late = is_checkin_late(now_local, db)
    att_status = "Late" if late else "Present"

    clean_late_reason = str(late_reason_param or "").strip()
    if late and not clean_late_reason:
        cleanup_photo_file(storage_key)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "LATE_REASON_REQUIRED",
                "message": "Check-in time is after 9:30 AM IST. A valid late check-in reason is mandatory before check-in can be completed.",
                "isLate": True,
            },
        )

    # 8. Upload to Cloud Storage for Firebase and persist in Cloud Firestore
    emp_name = (
        emp.get("name") or emp.get("full_name") or emp.get("fullName") or "Employee"
    ) if isinstance(emp, dict) else getattr(emp, "name", getattr(emp, "full_name", "Employee"))
    emp_dept = emp.get("department", "Operations") if isinstance(emp, dict) else getattr(emp, "department", "Operations")

    if settings.DATABASE_BACKEND == "firebase":
        record_id = f"{emp_id}_{today_iso}"

        # Upload photo to Firebase Storage
        storage_path, photo_url = upload_to_firebase_storage(
            photo_bytes=photo_bytes,
            mime_type=photo_mime,
            employee_id=emp_id,
            attendance_record_id=record_id,
            photo_type="check-in",
            employee_uid=emp_uid,
            attendance_date=today_iso,
        )

        # Cleanup temporary local validation photo file now that it is safely uploaded
        cleanup_photo_file(storage_key)

        attendance_doc = {
            "id": record_id,
            "employee_id": emp_id,
            "employeeId": emp_id,
            "employee_uid": emp_uid,
            "employeeUid": emp_uid,
            "employeeName": emp_name,
            "name": emp_name,
            "department": emp_dept,
            "date": today_iso,
            "check_in_time": time_str,
            "check_in_timestamp": now_utc.isoformat(),
            "work_mode": work_mode,
            "status": att_status,
            "is_late": late,
            "isLate": late,
            "late_reason": clean_late_reason if (late and clean_late_reason) else None,
            "lateReason": clean_late_reason if (late and clean_late_reason) else None,
            "late_reason_status": "SUBMITTED" if (late and clean_late_reason) else ("PENDING" if late else "NOT_REQUIRED"),
            "lateReasonStatus": "SUBMITTED" if (late and clean_late_reason) else ("PENDING" if late else "NOT_REQUIRED"),
            "late_reason_submitted_at": now_utc.isoformat() if (late and clean_late_reason) else None,
            "lateReasonSubmittedAt": now_utc.isoformat() if (late and clean_late_reason) else None,
            "duration": "In Progress",
            "check_in_latitude": lat,
            "check_in_longitude": lon,
            "check_in_location_accuracy": acc,
            "office_location_verified": (work_mode == "WFO"),
            "check_in_photo_key": storage_path,
            "check_in_photo_storage_path": storage_path,
            "checkInPhotoPath": storage_path,
            "check_in_photo_url": photo_url,
            "checkInPhotoUrl": photo_url,
            "photoUrl": photo_url,
            "imageUploadStatus": "SUCCESS",
            "imageUploadTimestamp": now_utc.isoformat(),
            "hasCheckInPhoto": True,
            "hasCheckOutPhoto": False,
            "created_at": now_utc.isoformat(),
            "updated_at": now_utc.isoformat(),
        }
        FirestoreService.save("attendance", record_id, attendance_doc)

        # Record photo document in attendance_photos
        photo_doc = {
            "id": f"PHOTO_{record_id}_check_in",
            "attendance_id": record_id,
            "employee_id": emp_id,
            "employee_uid": emp_uid,
            "photo_type": "check_in",
            "mime_type": photo_mime,
            "file_size_bytes": len(photo_bytes),
            "storage_path": storage_path,
            "storage_url": photo_url,
            "created_at": now_utc.isoformat(),
        }
        FirestoreService.save("attendance_photos", f"PHOTO_{record_id}_check_in", photo_doc)

        # Mirror check-in to attendance/{emp_uid}/records/{today_iso} for mobile synchronization
        FirestoreService.save_subdocument(
            collection="attendance",
            doc_id=emp_uid,
            subcollection="records",
            subdoc_id=today_iso,
            data={
                "employeeId": emp_uid,
                "email": user_email,
                "date": today_iso,
                "checkIn": now_utc.isoformat(),
                "status": att_status,
                "workMode": work_mode,
                "lateLogin": late,
                "isLate": late,
                "lateReason": clean_late_reason if (late and clean_late_reason) else "",
                "lateReasonStatus": "SUBMITTED" if (late and clean_late_reason) else ("PENDING" if late else "NOT_REQUIRED"),
                "lateReasonSubmittedAt": now_utc.isoformat() if (late and clean_late_reason) else None,
                "checkInPhotoUrl": photo_url,
                "photoCaptured": bool(photo_url),
            }
        )

        FirestoreService.add_audit_log(
            actor_uid=emp_id,
            action="ATTENDANCE_CHECK_IN",
            target_record=record_id,
            metadata={"work_mode": work_mode, "status": att_status, "photo_uploaded": True, "storage_path": storage_path},
        )

        return {
            "id": record_id,
            "success": True,
            "message": f"Checked in successfully as {work_mode} ({att_status})",
            "checkIn": time_str,
            "checkInTime": time_str,
            "workMode": work_mode,
            "status": att_status,
            "isLate": late,
            "lateReason": clean_late_reason if (late and clean_late_reason) else None,
            "lateReasonStatus": "SUBMITTED" if (late and clean_late_reason) else ("PENDING" if late else "NOT_REQUIRED"),
            "lateReasonSubmittedAt": now_utc.isoformat() if (late and clean_late_reason) else None,
            "timestamp": now_utc.isoformat(),
            "hasCheckInPhoto": True,
            "photoUrl": photo_url,
            "checkInLatitude": lat,
            "checkInLongitude": lon,
            "checkInLocationAccuracy": acc,
            "canCheckIn": False,
            "canCheckOut": True,
            "attendance": attendance_doc,
        }

    # PostgreSQL fallback
    try:
        if existing:
            existing.check_in_time = time_str
            existing.check_in_timestamp = now_utc
            existing.check_in_photo_key = storage_key
            existing.check_in_photo_data = photo_bytes
            existing.check_in_photo_mime = photo_mime
            existing.check_in_latitude = lat
            existing.check_in_longitude = lon
            existing.check_in_location_accuracy = acc
            existing.work_mode = work_mode
            existing.status = att_status
            existing.is_late = late
            existing.late_reason = clean_late_reason if (late and clean_late_reason) else None
            existing.late_reason_submitted_at = now_utc if (late and clean_late_reason) else None
            existing.duration = "In Progress"
            record = existing
        else:
            record = Attendance(
                employee_id=emp_id,
                date=today,
                check_in_time=time_str,
                check_in_timestamp=now_utc,
                check_in_photo_key=storage_key,
                check_in_photo_data=photo_bytes,
                check_in_photo_mime=photo_mime,
                check_in_latitude=lat,
                check_in_longitude=lon,
                check_in_location_accuracy=acc,
                work_mode=work_mode,
                status=att_status,
                is_late=late,
                late_reason=clean_late_reason if (late and clean_late_reason) else None,
                late_reason_submitted_at=now_utc if (late and clean_late_reason) else None,
                duration="In Progress",
            )
            db.add(record)

        db.flush()
        db.commit()
        db.refresh(record)

        return {
            "id": record.id,
            "success": True,
            "message": f"Checked in successfully as {work_mode} ({att_status})",
            "checkIn": time_str,
            "checkInTime": time_str,
            "workMode": work_mode,
            "status": att_status,
            "isLate": late,
            "lateReason": clean_late_reason if (late and clean_late_reason) else None,
            "lateReasonStatus": "SUBMITTED" if (late and clean_late_reason) else ("PENDING" if late else "NOT_REQUIRED"),
            "lateReasonSubmittedAt": now_utc.isoformat() if (late and clean_late_reason) else None,
            "timestamp": now_utc.isoformat(),
            "hasCheckInPhoto": True,
            "checkInLatitude": lat,
            "checkInLongitude": lon,
            "checkInLocationAccuracy": acc,
            "canCheckIn": False,
            "canCheckOut": True,
        }
    except Exception as e:
        db.rollback()
        cleanup_photo_file(storage_key)
        logger.error(f"Error persisting check-in for {emp_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database transaction failed during attendance record creation.",
        )


@router.post("/check-out", status_code=status.HTTP_200_OK)
async def check_out(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Record daily attendance punch-out and lock attendance for the remainder of today.
    """
    user_role = str(getattr(current_user, "role", "employee") or "employee").strip().lower()
    user_id = getattr(current_user, "id", None) or getattr(current_user, "uid", None)
    user_email = str(getattr(current_user, "email", "") or "").strip().lower()

    # Read optional JSON body if present
    body = {}
    try:
        body = await request.json()
    except Exception:
        body = {}

    body_emp_id = str(body.get("employeeId") or body.get("employee_id") or "").strip()

    emp_id = None
    if user_role == "admin":
        emp_id = body_emp_id or None
        if not emp_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employee ID is required for administrative check-out.",
            )
    else:
        # 1. Check if authenticated employee entity already carries an employee identifier
        emp_id = getattr(current_user, "employee_id", None) or getattr(current_user, "employeeId", None)

        # 2. Check if employee identifier was provided in request body
        if not emp_id and body_emp_id:
            emp_id = body_emp_id

        # 3. Resolve from database
        if settings.DATABASE_BACKEND == "firebase":
            emp = None
            if user_id:
                emp = FirestoreService.get_by_id("employees", str(user_id))
            if not emp and user_email:
                matches = FirestoreService.query("employees", {"email": user_email})
                if matches:
                    emp = matches[0]
            if not emp and user_id:
                matches = FirestoreService.query("employees", {"uid": str(user_id)})
                if matches:
                    emp = matches[0]
            if not emp and user_id:
                matches = FirestoreService.query("employees", {"user_id": user_id})
                if matches:
                    emp = matches[0]
                elif str(user_id).isdigit():
                    matches = FirestoreService.query("employees", {"user_id": int(user_id)})
                    if matches:
                        emp = matches[0]

            if emp:
                emp_id = emp.get("employee_id") or emp.get("employeeId") or emp.get("id")

            if not emp_id and user_id and (str(user_id).startswith("AFI") or str(user_id).startswith("EMP")):
                emp_id = str(user_id)
        else:
            emp = None
            if user_id:
                emp = db.query(Employee).filter(Employee.user_id == user_id).first()
            if not emp and user_email:
                emp = db.query(Employee).filter(Employee.email == user_email).first()
            if not emp and body_emp_id:
                emp = db.query(Employee).filter(Employee.employee_id == body_emp_id).first()

            if emp:
                emp_id = emp.employee_id
            elif body_emp_id:
                emp_id = body_emp_id

    if not emp_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee ID could not be determined.",
        )

    today = get_attendance_today()
    today_iso = today.isoformat()
    now_local = get_attendance_now()
    now_utc = datetime.now(timezone.utc)
    out_time_str = now_local.strftime("%I:%M %p")

    if settings.DATABASE_BACKEND == "firebase":
        records = FirestoreService.query("attendance", {"employee_id": emp_id, "date": today_iso})
        if not records:
            records = FirestoreService.query("attendance", {"employeeId": emp_id, "date": today_iso})
        record = records[0] if records else None

        if not record:
            record = FirestoreService.get_by_id("attendance", f"{emp_id}_{today_iso}")

        if not record:
            emp_uid_lookup = str(getattr(current_user, "uid", None) or getattr(current_user, "id", None) or emp_id)
            cg_today = FirestoreService.collection_group("records", [("date", "==", today_iso)])
            for cr in cg_today:
                c_eid = str(cr.get("employeeId") or cr.get("employee_id") or cr.get("uid") or "")
                if c_eid in [str(emp_id), str(emp_uid_lookup)]:
                    record = cr
                    break

        chk_in = (record.get("check_in_time") or record.get("checkIn") or "") if record else ""
        chk_out = (record.get("check_out_time") or record.get("checkOut") or "") if record else ""

        if not record or not chk_in or chk_in == "--":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot check out without an active check-in for today.",
            )
        if chk_out and chk_out != "--":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Attendance already completed and locked for today.",
            )

        # Calculate working duration using server-authoritative timestamps
        dur_secs = 0
        in_ts = record.get("check_in_timestamp") or record.get("checkInTimestamp") or record.get("checkIn")
        in_dt = None
        if isinstance(in_ts, datetime):
            in_dt = in_ts
        elif isinstance(in_ts, str) and in_ts:
            try:
                in_dt = datetime.fromisoformat(in_ts.replace("Z", "+00:00"))
            except Exception:
                in_dt = None

        if in_dt:
            if in_dt.tzinfo is None:
                in_dt = in_dt.replace(tzinfo=timezone.utc)
            dur_secs = int((now_utc - in_dt).total_seconds())

        if dur_secs <= 0 and chk_in and chk_in != "--":
            try:
                parsed_time = datetime.strptime(str(chk_in).strip().upper(), "%I:%M %p").time()
                in_local = datetime.combine(today, parsed_time)
                dur_secs = int((now_local.replace(tzinfo=None) - in_local).total_seconds())
            except Exception:
                pass

        dur_secs = max(0, dur_secs)
        duration_str = format_duration_str(dur_secs)

        doc_id = record.get("id") or record.get("_firestore_id") or f"{emp_id}_{today_iso}"
        update_data = {
            "check_out_time": out_time_str,
            "check_out_timestamp": now_utc.isoformat(),
            "duration": duration_str,
            "status": "Completed",
            "is_completed": True,
            "canCheckIn": False,
            "canCheckOut": False,
        }
        FirestoreService.update("attendance", doc_id, update_data)
        FirestoreService.update("attendances", doc_id, update_data)

        # Mirror checkout to mobile subcollection
        emp_uid = str(record.get("employee_uid") or record.get("employeeUid") or user_id or emp_id)
        FirestoreService.update_subdocument(
            collection="attendance",
            doc_id=emp_uid,
            subcollection="records",
            subdoc_id=today_iso,
            updates={
                "checkOut": now_utc.isoformat(),
                "checkOutTime": out_time_str,
                "duration": duration_str,
                "status": "Completed",
            },
        )

        FirestoreService.add_audit_log(
            actor_uid=emp_id,
            action="ATTENDANCE_CHECK_OUT",
            target_record=doc_id,
            metadata={"check_out": out_time_str, "duration": duration_str},
        )

        return {
            "id": doc_id,
            "success": True,
            "message": f"Checked out successfully at {out_time_str}. Daily duration: {duration_str}",
            "checkOut": out_time_str,
            "checkOutTime": out_time_str,
            "duration": duration_str,
            "workingDuration": duration_str,
            "status": "Completed",
            "isCompleted": True,
            "isCheckedIn": False,
            "canCheckIn": False,
            "canCheckOut": False,
            "attendance": {
                "id": doc_id,
                "employeeId": emp_id,
                "employee_id": emp_id,
                "date": today_iso,
                "checkIn": chk_in,
                "checkInTime": chk_in,
                "checkOut": out_time_str,
                "checkOutTime": out_time_str,
                "duration": duration_str,
                "workingDuration": duration_str,
                "status": "Completed",
                "workMode": record.get("work_mode") or record.get("workMode") or "WFO",
            },
        }

    # PostgreSQL fallback
    record = db.query(Attendance).filter(Attendance.employee_id == emp_id, Attendance.date == today).first()
    if not record or not record.check_in_time or record.check_in_time == "--":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot check out without an active check-in for today.",
        )
    if record.check_out_time and record.check_out_time != "--":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Attendance already completed and locked for today.",
        )

    dur_secs = 0
    if record.check_in_timestamp:
        in_dt = record.check_in_timestamp
        if in_dt.tzinfo is None:
            in_dt = in_dt.replace(tzinfo=timezone.utc)
        dur_secs = int((now_utc - in_dt).total_seconds())

    if dur_secs <= 0 and record.check_in_time and record.check_in_time != "--":
        try:
            parsed_time = datetime.strptime(record.check_in_time.strip().upper(), "%I:%M %p").time()
            in_local = datetime.combine(today, parsed_time)
            dur_secs = int((now_local.replace(tzinfo=None) - in_local).total_seconds())
        except Exception:
            pass

    dur_secs = max(0, dur_secs)
    duration_str = format_duration_str(dur_secs)

    record.check_out_time = out_time_str
    record.check_out_timestamp = now_utc
    record.duration = duration_str
    record.status = "Completed"
    db.commit()
    db.refresh(record)

    return {
        "id": record.id,
        "success": True,
        "message": f"Checked out successfully at {out_time_str}. Daily duration: {duration_str}",
        "checkOut": out_time_str,
        "checkOutTime": out_time_str,
        "duration": duration_str,
        "workingDuration": duration_str,
        "status": "Completed",
        "isCompleted": True,
        "isCheckedIn": False,
        "canCheckIn": False,
        "canCheckOut": False,
        "attendance": {
            "id": record.id,
            "employeeId": emp_id,
            "employee_id": emp_id,
            "date": today_iso,
            "checkIn": record.check_in_time,
            "checkInTime": record.check_in_time,
            "checkOut": out_time_str,
            "checkOutTime": out_time_str,
            "duration": duration_str,
            "workingDuration": duration_str,
            "status": "Completed",
            "workMode": record.work_mode or "WFO",
        },
    }


@router.get("/{attendance_id}/photo")
@router.get("/{attendance_id}/photo/{photo_type}")
def get_attendance_photo(
    attendance_id: str,
    photo_type: str = "check-in",
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Retrieve attendance photo with strict caller authorization.
    Serves from Cloud Storage for Firebase, local storage, or database bytes.
    """
    caller_role = getattr(current_user, "role", "employee")
    caller_email = getattr(current_user, "email", "")

    if settings.DATABASE_BACKEND == "firebase":
        rec = FirestoreService.get_by_id("attendance", attendance_id)
        if not rec:
            all_att = FirestoreService.list_all("attendance")
            for a in all_att:
                if str(a.get("id")) == str(attendance_id):
                    rec = a
                    break
        if not rec:
            raise HTTPException(status_code=404, detail="Attendance record not found.")

        # Permission check: Caller must be admin or the owner
        record_emp_id = rec.get("employee_id")
        if caller_role != "admin":
            emps = FirestoreService.query("employees", {"email": caller_email})
            if not emps or emps[0].get("employee_id") != record_emp_id:
                raise HTTPException(status_code=403, detail="Forbidden: You cannot view other employees' photos.")

        # 1. Check if Cloud Storage has the photo
        storage_path = rec.get("check_in_photo_storage_path") or rec.get("checkInPhotoStoragePath")
        if is_firebase_live() and storage_path:
            bucket = get_storage_bucket()
            if bucket:
                try:
                    blob = bucket.blob(storage_path)
                    if blob.exists():
                        photo_bytes = blob.download_as_bytes()
                        return Response(
                            content=photo_bytes,
                            media_type="image/jpeg",
                            headers={"Cache-Control": "private, max-age=3600"},
                        )
                except Exception as e:
                    logger.warning(f"Failed to stream from Cloud Storage: {e}")

        # 2. Check local file storage fallback
        storage_key = rec.get("check_in_photo_key")
        if storage_key:
            try:
                abs_path, mime_type = resolve_photo_path(storage_key)
                return FileResponse(abs_path, media_type=mime_type, headers={"Cache-Control": "private, max-age=3600"})
            except Exception:
                pass

        # Check rec_dir
        base = get_attendance_storage_dir()
        candidate = os.path.join(base, str(record_emp_id), str(attendance_id), f"{photo_type}.jpg")
        if os.path.exists(candidate):
            return FileResponse(candidate, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})

        raise HTTPException(status_code=404, detail="Attendance photo not found.")

    # PostgreSQL fallback
    record = (
        db.query(Attendance)
        .filter(Attendance.id == int(attendance_id) if attendance_id.isdigit() else False)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found.")

    if caller_role != "admin":
        emp = db.query(Employee).filter(Employee.email == caller_email).first()
        if not emp or record.employee_id != emp.employee_id:
            raise HTTPException(status_code=403, detail="Forbidden: You cannot view other employees' photos.")

    if record.check_in_photo_data:
        return Response(
            content=record.check_in_photo_data,
            media_type=record.check_in_photo_mime or "image/jpeg",
            headers={"Cache-Control": "private, max-age=3600"},
        )

    if record.check_in_photo_key:
        abs_path, mime_type = resolve_photo_path(record.check_in_photo_key)
        return FileResponse(abs_path, media_type=mime_type, headers={"Cache-Control": "private, max-age=3600"})

    raise HTTPException(status_code=404, detail="No photo recorded for this attendance entry.")


@router.post("/late-reason", status_code=status.HTTP_200_OK)
@router.post("/{attendance_id}/late-reason", status_code=status.HTTP_200_OK)
def submit_late_reason(
    payload: LateReasonSubmissionRequest,
    attendance_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Submit mandatory reason for late check-in.
    Validates authenticated user, late status, rejects empty/whitespace input,
    and prevents duplicate or unauthorized submissions.
    """
    clean_reason = (payload.reason or "").strip()
    if not clean_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Late arrival reason cannot be empty or whitespace.",
        )

    user_role = getattr(current_user, "role", "employee")
    user_id = getattr(current_user, "id", None)
    user_email = getattr(current_user, "email", "")

    # 1. Resolve employee identity from session
    emp_id = None
    emp_uid = None
    if user_role == "employee":
        emp, emp_id, emp_uid = resolve_employee_for_attendance(
            current_user=current_user,
            db=db,
        )
    elif user_role == "admin":
        emp_id = None
        emp_uid = None
    else:
        raise HTTPException(status_code=403, detail="Employee access required.")

    target_id = attendance_id or payload.attendanceId
    today_iso = get_attendance_today().isoformat()
    now_utc = datetime.now(timezone.utc)

    # 2. Resolve target attendance record
    if settings.DATABASE_BACKEND == "firebase":
        rec = None
        if target_id:
            rec = FirestoreService.get_by_id("attendance", str(target_id))
            if not rec:
                all_att = FirestoreService.list_all("attendance")
                for a in all_att:
                    if str(a.get("id")) == str(target_id):
                        rec = a
                        break

        if not rec and emp_id:
            recs = FirestoreService.query("attendance", {"employee_id": emp_id, "date": today_iso})
            if not recs:
                recs = FirestoreService.query("attendance", {"employeeId": emp_id, "date": today_iso})
            if not recs and emp_uid:
                recs = FirestoreService.query("attendance", {"employee_uid": emp_uid, "date": today_iso})
            rec = recs[0] if recs else None

        if not rec:
            raise HTTPException(status_code=404, detail="No attendance record found for this check-in.")

        rec_emp_id = str(rec.get("employee_id") or rec.get("employeeId") or "")
        rec_emp_uid = str(rec.get("employee_uid") or rec.get("employeeUid") or "")
        if user_role == "employee":
            if emp_id and rec_emp_id != str(emp_id) and rec_emp_uid != str(emp_uid):
                raise HTTPException(status_code=403, detail="You can only submit a late reason for your own attendance record.")

        is_rec_late = bool(rec.get("is_late") or rec.get("isLate") or rec.get("status") == "Late" or rec.get("lateLogin"))
        if not is_rec_late:
            raise HTTPException(status_code=400, detail="Late reason is not required for an on-time check-in.")

        existing_reason = rec.get("late_reason") or rec.get("lateReason")
        if existing_reason and str(existing_reason).strip():
            raise HTTPException(status_code=409, detail="Late reason has already been submitted for this attendance record.")

        rec_key = str(rec.get("id") or target_id or f"{emp_id}_{today_iso}")
        updates = {
            "late_reason": clean_reason,
            "lateReason": clean_reason,
            "late_reason_status": "SUBMITTED",
            "lateReasonStatus": "SUBMITTED",
            "late_reason_submitted_at": now_utc.isoformat(),
            "lateReasonSubmittedAt": now_utc.isoformat(),
            "updated_at": now_utc.isoformat(),
        }
        FirestoreService.update("attendance", rec_key, updates)
        rec.update(updates)

        if emp_uid:
            try:
                rec_date = str(rec.get("date") or today_iso).strip()
                FirestoreService.update_subdocument(
                    "attendance",
                    emp_uid,
                    "records",
                    rec_date,
                    {
                        "lateReason": clean_reason,
                        "lateReasonStatus": "SUBMITTED",
                        "lateReasonSubmittedAt": now_utc.isoformat(),
                    }
                )
            except Exception as e:
                logger.warning(f"Could not mirror lateReason to subdoc: {e}")

        FirestoreService.add_audit_log(
            actor_uid=emp_id or str(user_id),
            action="ATTENDANCE_LATE_REASON_SUBMITTED",
            target_record=rec_key,
            metadata={"late_reason": clean_reason},
        )

        return {
            "success": True,
            "message": "Late arrival reason recorded successfully.",
            "attendanceId": rec_key,
            "lateReason": clean_reason,
            "lateReasonStatus": "SUBMITTED",
            "lateReasonSubmittedAt": now_utc.isoformat(),
        }

    # PostgreSQL fallback
    record = None
    if target_id and str(target_id).isdigit():
        record = db.query(Attendance).filter(Attendance.id == int(target_id)).first()

    if not record and emp_id:
        record = db.query(Attendance).filter(
            Attendance.employee_id == emp_id,
            Attendance.date == get_attendance_today(),
        ).first()

    if not record:
        raise HTTPException(status_code=404, detail="No attendance record found for this check-in.")

    if user_role == "employee" and record.employee_id != emp_id:
        raise HTTPException(status_code=403, detail="You can only submit a late reason for your own attendance record.")

    if not (record.is_late or (record.status and record.status.lower() == "late")):
        raise HTTPException(status_code=400, detail="Late reason is not required for an on-time check-in.")

    if record.late_reason and record.late_reason.strip():
        raise HTTPException(status_code=409, detail="Late reason has already been submitted for this attendance record.")

    record.late_reason = clean_reason
    record.late_reason_submitted_at = now_utc
    db.commit()
    db.refresh(record)

    return {
        "success": True,
        "message": "Late arrival reason recorded successfully.",
        "attendanceId": str(record.id),
        "lateReason": clean_reason,
        "lateReasonStatus": "SUBMITTED",
        "lateReasonSubmittedAt": now_utc.isoformat(),
    }


@router.patch("/{record_id}", response_model=dict)
def update_attendance_record(
    record_id: str,
    data: AttendanceRecordUpdate,
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin),
):
    """Edit attendance record details (Admin only)."""
    if settings.DATABASE_BACKEND == "firebase":
        rec = FirestoreService.get_by_id("attendance", record_id)
        if not rec:
            all_att = FirestoreService.list_all("attendance")
            for a in all_att:
                if str(a.get("id")) == str(record_id):
                    rec = a
                    break
        if not rec:
            raise HTTPException(status_code=404, detail="Attendance record not found.")

        updates = {}
        if data.status:
            updates["status"] = data.status
            updates["is_late"] = data.status.lower() == "late"
        if data.workMode:
            updates["work_mode"] = data.workMode
        if data.checkIn:
            updates["check_in_time"] = data.checkIn
        if data.checkOut:
            updates["check_out_time"] = data.checkOut
        if data.lateReason is not None:
            updates["late_reason"] = data.lateReason
            updates["lateReason"] = data.lateReason
            updates["late_reason_status"] = "SUBMITTED" if data.lateReason else "PENDING"
            updates["lateReasonStatus"] = "SUBMITTED" if data.lateReason else "PENDING"

        doc_key = rec.get("id") or record_id
        FirestoreService.update("attendance", doc_key, updates)
        rec.update(updates)
        return format_attendance_response(rec)

    # PostgreSQL fallback
    record = (
        db.query(Attendance)
        .filter(Attendance.id == int(record_id) if record_id.isdigit() else False)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found.")

    if data.status:
        record.status = data.status
        record.is_late = data.status.lower() == "late"
    if data.workMode:
        record.work_mode = data.workMode
    if data.checkIn:
        record.check_in_time = data.checkIn
    if data.checkOut:
        record.check_out_time = data.checkOut
    if data.lateReason is not None:
        record.late_reason = data.lateReason

    db.commit()
    db.refresh(record)
    return format_attendance_response(record)


@router.get("/summary")
def get_attendance_summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get headline attendance summary metrics for today."""
    today = get_attendance_today()
    today_iso = today.isoformat()

    if settings.DATABASE_BACKEND == "firebase":
        records = FirestoreService.query("attendance", {"date": today_iso})
        total_present = len([r for r in records if r.get("status") in ["Present", "Late", "Completed"]])
        wfo = len([r for r in records if r.get("work_mode") == "WFO" and r.get("status") in ["Present", "Late", "Completed"]])
        wfh = len([r for r in records if r.get("work_mode") == "WFH" and r.get("status") in ["Present", "Late", "Completed"]])
        late = len([r for r in records if r.get("is_late") or r.get("status") == "Late"])
        return {
            "totalPresent": total_present,
            "wfo": wfo,
            "wfh": wfh,
            "late": late,
        }

    # PostgreSQL fallback
    records = db.query(Attendance).filter(Attendance.date == today).all()
    total_present = len([r for r in records if r.status in ["Present", "Late", "Completed"]])
    wfo = len([r for r in records if r.work_mode == "WFO" and r.status in ["Present", "Late", "Completed"]])
    wfh = len([r for r in records if r.work_mode == "WFH" and r.status in ["Present", "Late", "Completed"]])
    late = len([r for r in records if r.is_late or r.status == "Late"])

    return {
        "totalPresent": total_present,
        "wfo": wfo,
        "wfh": wfh,
        "late": late,
    }
