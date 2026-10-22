from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.config import settings
from app.db.session import get_db
from app.models.registration_request import RegistrationRequest
from app.models.user import User
from app.models.employee import Employee
from app.schemas.registration_request import RegistrationRequestUpdate, RegistrationRequestResponse
from app.dependencies.auth import get_current_admin
from app.services.firestore_service import FirestoreService
from app.services.sync_service import sync_employee_approval_state

router = APIRouter()


def format_request_response(r: dict) -> dict:
    req_code = r.get("request_code") or r.get("id") or "REQ-0001"
    req_id = r.get("id") or req_code
    full_name = r.get("full_name") or r.get("fullName") or r.get("name") or "Employee"
    emp_id = r.get("employee_id") or r.get("employeeId") or ""
    email = r.get("email") or ""
    phone = r.get("phone") or "--"
    status_str = r.get("status") or "Pending"
    req_date = r.get("requested_date") or r.get("requestedDate") or datetime.now(timezone.utc).date().isoformat()
    if isinstance(req_date, datetime):
        req_date = req_date.date().isoformat()
    elif not isinstance(req_date, str):
        req_date = str(req_date)

    reviewed_at = r.get("reviewed_at") or r.get("reviewedAt")
    if isinstance(reviewed_at, datetime):
        reviewed_at = reviewed_at.isoformat()

    return {
        "id": req_code,
        "requestId": req_id,
        "name": full_name,
        "fullName": full_name,
        "employeeId": emp_id,
        "email": email,
        "phone": phone,
        "status": status_str,
        "requestedDate": req_date,
        "rejectionReason": r.get("rejection_reason") or r.get("rejectionReason"),
        "reviewedBy": r.get("reviewed_by") or r.get("reviewedBy"),
        "reviewedAt": reviewed_at,
    }


@router.get("", response_model=List[dict])
def list_registration_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin),
):
    """List staff signup onboarding requests across both mobile and web (Admin only)."""
    if settings.DATABASE_BACKEND == "firebase":
        raw_employees = FirestoreService.list_all("employees")
        raw_requests = FirestoreService.list_all("registration_requests")

        merged = {}

        # 1. Process employees collection (authoritative source for mobile signups)
        for emp in raw_employees:
            st = str(emp.get("status", "")).strip()
            emp_code = emp.get("employeeId") or emp.get("employee_id") or emp.get("uid") or emp.get("id") or ""
            email = str(emp.get("email", "")).strip().lower()
            name = emp.get("name") or emp.get("fullName") or emp.get("full_name") or "Employee"
            phone = emp.get("phone") or "--"
            req_date = emp.get("createdAt") or emp.get("created_at") or datetime.now(timezone.utc).date().isoformat()
            if isinstance(req_date, datetime):
                req_date = req_date.date().isoformat()
            elif isinstance(req_date, str) and "T" in req_date:
                req_date = req_date.split("T")[0]

            key = email if email else (str(emp_code).strip().upper() if emp_code else str(doc_id))

            # Map status into display status
            if st.lower() in ("approved", "active"):
                ui_status = "Approved"
            elif st.lower() == "rejected":
                ui_status = "Rejected"
            elif st.lower() == "pending":
                ui_status = "Pending"
            else:
                ui_status = st.capitalize() if st else "Pending"

            doc_id = emp.get("_firestore_id") or emp.get("uid") or emp.get("id") or emp_code

            reviewed_at = emp.get("reviewedAt") or emp.get("reviewed_at") or emp.get("approvedAt") or emp.get("approved_at")
            if isinstance(reviewed_at, datetime):
                reviewed_at = reviewed_at.isoformat()

            merged[key] = {
                "id": str(doc_id),
                "requestId": str(doc_id),
                "name": name,
                "fullName": name,
                "employeeId": str(emp.get("employeeId") or emp.get("employee_id") or emp_code),
                "email": email,
                "phone": phone,
                "status": ui_status,
                "raw_status": st,
                "requestedDate": str(req_date),
                "rejectionReason": emp.get("rejectionReason") or emp.get("rejection_reason"),
                "reviewedBy": emp.get("reviewedBy") or emp.get("reviewed_by") or emp.get("approvedBy") or emp.get("approved_by"),
                "reviewedAt": reviewed_at,
                "_source": "employees",
                "_firestore_id": emp.get("_firestore_id") or str(doc_id),
                "uid": emp.get("uid") or emp.get("_firestore_id"),
            }

        # 2. Merge registration_requests collection
        for r in raw_requests:
            emp_code = str(r.get("employee_id") or r.get("employeeId") or "").strip().upper()
            email = str(r.get("email", "")).strip().lower()
            key = email if email else (emp_code if emp_code else str(r.get("id", "")))

            if key in merged:
                if not merged[key].get("rejectionReason") and (r.get("rejection_reason") or r.get("rejectionReason")):
                    merged[key]["rejectionReason"] = r.get("rejection_reason") or r.get("rejectionReason")
                if not merged[key].get("reviewedBy") and (r.get("reviewed_by") or r.get("reviewedBy")):
                    merged[key]["reviewedBy"] = r.get("reviewed_by") or r.get("reviewedBy")
                if not merged[key].get("reviewedAt") and (r.get("reviewed_at") or r.get("reviewedAt")):
                    merged[key]["reviewedAt"] = r.get("reviewed_at") or r.get("reviewedAt")
            else:
                formatted = format_request_response(r)
                merged[key] = formatted

        filtered = []
        for item in merged.values():
            st = str(item.get("status", "Pending")).upper()
            if status_filter:
                sf = status_filter.upper()
                if sf == "PENDING" and st != "PENDING":
                    continue
                elif sf == "APPROVED" and st != "APPROVED":
                    continue
                elif sf == "REJECTED" and st != "REJECTED":
                    continue
                elif sf == "PROCESSED" and st == "PENDING":
                    continue
            filtered.append(item)

        filtered.sort(key=lambda x: str(x.get("requestedDate", "")), reverse=True)
        return filtered

    # PostgreSQL fallback
    query = db.query(RegistrationRequest)
    if status_filter:
        sf = status_filter.upper()
        if sf == "PENDING":
            query = query.filter(RegistrationRequest.status == "Pending")
        elif sf in ("PROCESSED", "APPROVED", "REJECTED"):
            if sf == "PROCESSED":
                query = query.filter(RegistrationRequest.status != "Pending")
            elif sf == "APPROVED":
                query = query.filter(RegistrationRequest.status == "Approved")
            elif sf == "REJECTED":
                query = query.filter(RegistrationRequest.status == "Rejected")

    requests = query.order_by(desc(RegistrationRequest.requested_date), desc(RegistrationRequest.id)).all()
    return [
        format_request_response({
            "id": r.id,
            "request_code": r.request_code,
            "full_name": r.full_name,
            "employee_id": r.employee_id,
            "email": r.email,
            "phone": r.phone,
            "status": r.status,
            "requested_date": r.requested_date,
            "rejection_reason": r.rejection_reason,
            "reviewed_by": r.reviewed_by,
            "reviewed_at": r.reviewed_at,
        })
        for r in requests
    ]


@router.patch("/{request_id}/approve", response_model=dict)
def approve_registration_request(
    request_id: str,
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin),
):
    """Admin approves pending employee registration request across mobile and web."""
    now_iso = datetime.now(timezone.utc).isoformat()
    admin_email = getattr(admin_user, "email", "admin@arshith.com")
    admin_id = getattr(admin_user, "id", 1)

    if settings.DATABASE_BACKEND == "firebase":
        target_emp = FirestoreService.get_by_id("employees", request_id)
        target_req = FirestoreService.get_by_id("registration_requests", request_id)

        if not target_emp and target_req:
            clean_email = str(target_req.get("email", "")).lower().strip()
            emps = FirestoreService.query("employees", {"email": clean_email})
            if emps:
                target_emp = emps[0]
            elif target_req.get("employee_id"):
                emps = FirestoreService.query("employees", {"employee_id": target_req["employee_id"]})
                if emps:
                    target_emp = emps[0]

        if not target_emp and not target_req:
            raise HTTPException(status_code=404, detail=f"Registration request '{request_id}' not found")

        # 1. Update Employee document in Firestore
        emp_doc_id = None
        clean_email = ""
        emp_code = ""
        emp_name = "Employee"
        phone = "--"

        if target_emp:
            emp_doc_id = target_emp.get("_firestore_id") or target_emp.get("uid") or target_emp.get("id") or target_emp.get("employee_id")
            clean_email = str(target_emp.get("email", "")).lower().strip()
            emp_code = str(target_emp.get("employeeId") or target_emp.get("employee_id") or "")
            emp_name = target_emp.get("name") or target_emp.get("fullName") or target_emp.get("full_name") or "Employee"
            phone = target_emp.get("phone") or "--"
        elif target_req:
            clean_email = str(target_req.get("email", "")).lower().strip()
            emp_code = str(target_req.get("employee_id") or target_req.get("employeeId") or "")
            emp_name = target_req.get("full_name") or target_req.get("fullName") or "Employee"
            phone = target_req.get("phone") or "--"

        req_doc_id = (target_req.get("request_code") if target_req else None) or (target_emp.get("request_code") if target_emp else None) or f"REQ-{emp_code}"

        # Synchronize approval across all Firestore documents and PostgreSQL
        sync_employee_approval_state(clean_email, "approved", admin_email, db=db)

        FirestoreService.add_audit_log(
            actor_uid=admin_email,
            action="EMPLOYEE_REGISTRATION_APPROVED",
            target_record=emp_code or request_id,
            metadata={"request_id": request_id, "email": clean_email, "approved_status": "approved"},
        )

        return format_request_response({
            "id": request_id,
            "requestId": request_id,
            "request_code": req_doc_id,
            "full_name": emp_name,
            "name": emp_name,
            "employee_id": emp_code,
            "email": clean_email,
            "phone": phone,
            "status": "Approved",
            "requested_date": str(target_emp.get("createdAt") if target_emp else now_iso).split("T")[0],
            "reviewed_by": admin_email,
            "reviewed_at": now_iso,
        })

    # PostgreSQL fallback
    req = (
        db.query(RegistrationRequest)
        .filter(
            (RegistrationRequest.request_code == request_id)
            | (RegistrationRequest.employee_id == request_id)
            | (RegistrationRequest.id == int(request_id) if request_id.isdigit() else False)
        )
        .first()
    )
    if not req:
        raise HTTPException(status_code=404, detail="Registration request not found")

    if req.status == "Approved":
        raise HTTPException(status_code=400, detail="This registration request has already been approved")

    now = datetime.now(timezone.utc)
    req.status = "Approved"
    req.reviewed_by = admin_email
    req.reviewed_at = now
    req.rejection_reason = None

    clean_email = req.email.lower().strip()
    user = db.query(User).filter(User.email == clean_email).first()
    if user:
        user.approval_status = "APPROVED"
        user.is_active = True
        user.reviewed_by_id = admin_id
        user.reviewed_at = now
        user.rejection_reason = None

    emp = db.query(Employee).filter(
        (Employee.email == clean_email) | (Employee.employee_id == req.employee_id.strip())
    ).first()
    if emp:
        emp.status = "Active"

    db.commit()
    db.refresh(req)
    return format_request_response({
        "id": req.id,
        "request_code": req.request_code,
        "full_name": req.full_name,
        "employee_id": req.employee_id,
        "email": req.email,
        "phone": req.phone,
        "status": req.status,
        "requested_date": req.requested_date,
        "rejection_reason": req.rejection_reason,
        "reviewed_by": req.reviewed_by,
        "reviewed_at": req.reviewed_at,
    })


@router.patch("/{request_id}/reject", response_model=dict)
def reject_registration_request(
    request_id: str,
    data: Optional[RegistrationRequestUpdate] = None,
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin),
):
    """Admin rejects pending employee registration request."""
    reason = (data.get_reason() if data else None) or "Registration rejected by administration."
    now_iso = datetime.now(timezone.utc).isoformat()
    admin_email = getattr(admin_user, "email", "admin@arshith.com")
    admin_id = getattr(admin_user, "id", 1)

    if settings.DATABASE_BACKEND == "firebase":
        target_emp = FirestoreService.get_by_id("employees", request_id)
        target_req = FirestoreService.get_by_id("registration_requests", request_id)

        if not target_emp and target_req:
            clean_email = str(target_req.get("email", "")).lower().strip()
            emps = FirestoreService.query("employees", {"email": clean_email})
            if emps:
                target_emp = emps[0]
            elif target_req.get("employee_id"):
                emps = FirestoreService.query("employees", {"employee_id": target_req["employee_id"]})
                if emps:
                    target_emp = emps[0]

        if not target_emp and not target_req:
            raise HTTPException(status_code=404, detail=f"Registration request '{request_id}' not found")

        # 1. Update Employee document in Firestore to lowercase "rejected"
        emp_doc_id = None
        clean_email = ""
        emp_code = ""
        emp_name = "Employee"
        phone = "--"

        if target_emp:
            emp_doc_id = target_emp.get("_firestore_id") or target_emp.get("uid") or target_emp.get("id") or target_emp.get("employee_id")
            clean_email = str(target_emp.get("email", "")).lower().strip()
            emp_code = str(target_emp.get("employeeId") or target_emp.get("employee_id") or "")
            emp_name = target_emp.get("name") or target_emp.get("fullName") or target_emp.get("full_name") or "Employee"
            phone = target_emp.get("phone") or "--"
        elif target_req:
            clean_email = str(target_req.get("email", "")).lower().strip()
            emp_code = str(target_req.get("employee_id") or target_req.get("employeeId") or "")
            emp_name = target_req.get("full_name") or target_req.get("fullName") or "Employee"
            phone = target_req.get("phone") or "--"

        req_doc_id = (target_req.get("request_code") if target_req else None) or (target_emp.get("request_code") if target_emp else None) or f"REQ-{emp_code}"

        # Synchronize rejection across all Firestore documents and PostgreSQL
        sync_employee_approval_state(clean_email, "rejected", admin_email, rejection_reason=reason, db=db)

        FirestoreService.add_audit_log(
            actor_uid=admin_email,
            action="EMPLOYEE_REGISTRATION_REJECTED",
            target_record=emp_code or request_id,
            metadata={"request_id": request_id, "reason": reason, "status": "rejected"},
        )

        return format_request_response({
            "id": request_id,
            "requestId": request_id,
            "request_code": req_doc_id,
            "full_name": emp_name,
            "name": emp_name,
            "employee_id": emp_code,
            "email": clean_email,
            "phone": phone,
            "status": "Rejected",
            "requested_date": str(target_emp.get("createdAt") if target_emp else now_iso).split("T")[0],
            "reviewed_by": admin_email,
            "reviewed_at": now_iso,
            "rejection_reason": reason,
        })

    # PostgreSQL fallback
    req = (
        db.query(RegistrationRequest)
        .filter(
            (RegistrationRequest.request_code == request_id)
            | (RegistrationRequest.employee_id == request_id)
            | (RegistrationRequest.id == int(request_id) if request_id.isdigit() else False)
        )
        .first()
    )
    if not req:
        raise HTTPException(status_code=404, detail="Registration request not found")

    if req.status == "Rejected":
        raise HTTPException(status_code=400, detail="This registration request has already been rejected")

    now = datetime.now(timezone.utc)
    req.status = "Rejected"
    req.reviewed_by = admin_email
    req.reviewed_at = now
    req.rejection_reason = reason

    clean_email = req.email.lower().strip()
    user = db.query(User).filter(User.email == clean_email).first()
    if user:
        user.approval_status = "REJECTED"
        user.is_active = False
        user.reviewed_by_id = admin_id
        user.reviewed_at = now
        user.rejection_reason = reason

    emp = db.query(Employee).filter(
        (Employee.email == clean_email) | (Employee.employee_id == req.employee_id.strip())
    ).first()
    if emp:
        emp.status = "Inactive"

    db.commit()
    db.refresh(req)
    return format_request_response({
        "id": req.id,
        "request_code": req.request_code,
        "full_name": req.full_name,
        "employee_id": req.employee_id,
        "email": req.email,
        "phone": req.phone,
        "status": req.status,
        "requested_date": req.requested_date,
        "rejection_reason": req.rejection_reason,
        "reviewed_by": req.reviewed_by,
        "reviewed_at": req.reviewed_at,
    })


@router.patch("/{request_id}", response_model=dict)
def update_registration_status(
    request_id: str,
    data: RegistrationRequestUpdate,
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin),
):
    """Backward-compatible general status update (calls approve or reject)."""
    if data.status == "Approved":
        return approve_registration_request(request_id=request_id, db=db, admin_user=admin_user)
    elif data.status == "Rejected":
        return reject_registration_request(request_id=request_id, data=data, db=db, admin_user=admin_user)
    else:
        raise HTTPException(status_code=400, detail="Status must be 'Approved' or 'Rejected'")
