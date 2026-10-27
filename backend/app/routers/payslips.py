"""
Payslips API Router
Enables digital payslip retrieval, access authorization, and dynamic PDF downloads.
"""

from typing import List, Optional, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.core.config import settings
from app.dependencies.auth import get_current_user, get_current_admin
from app.services.firestore_service import FirestoreService
from app.services.payslip_pdf import generate_payslip_pdf

router = APIRouter(prefix="/payslips", tags=["Payslips"])


def _get_caller_candidate_ids(current_user: Any) -> set:
    """Expands caller identity across UID, employeeId, employee_id, and email."""
    caller_emp_id = str(getattr(current_user, "employee_id", "") or getattr(current_user, "employeeId", "") or "").strip().lower()
    caller_email = str(getattr(current_user, "email", "") or "").strip().lower()
    caller_uid = str(getattr(current_user, "uid", "") or getattr(current_user, "id", "") or "").strip().lower()

    candidate_ids = set()
    if caller_emp_id: candidate_ids.add(caller_emp_id)
    if caller_email: candidate_ids.add(caller_email)
    if caller_uid: candidate_ids.add(caller_uid)

    employees = FirestoreService.get_all("employees")
    for emp in employees:
        e_id = str(emp.get("id") or "").strip().lower()
        e_eid = str(emp.get("employeeId") or "").strip().lower()
        e_eid2 = str(emp.get("employee_id") or "").strip().lower()
        e_mail = str(emp.get("email") or "").strip().lower()

        if (e_id and e_id in candidate_ids) or \
           (e_eid and e_eid in candidate_ids) or \
           (e_eid2 and e_eid2 in candidate_ids) or \
           (e_mail and e_mail in candidate_ids):
            if e_id: candidate_ids.add(e_id)
            if e_eid: candidate_ids.add(e_eid)
            if e_eid2: candidate_ids.add(e_eid2)
            if e_mail: candidate_ids.add(e_mail)

    return candidate_ids


def _is_payslip_authorized_for_user(payslip: dict, current_user: Any) -> bool:
    """Verifies whether caller has legitimate access to this payslip."""
    role = str(getattr(current_user, "role", "employee")).lower()
    if role != "employee":
        return True

    candidate_ids = _get_caller_candidate_ids(current_user)
    p_eid = str(payslip.get("employee_id") or "").strip().lower()
    p_eid2 = str(payslip.get("employeeId") or "").strip().lower()
    p_mail = str(payslip.get("employee_email") or payslip.get("email") or "").strip().lower()
    p_doc = str(payslip.get("employee_doc_id") or "").strip().lower()
    p_detail_eid = str((payslip.get("detail") or {}).get("employee_id") or "").strip().lower()
    p_detail_eid2 = str((payslip.get("detail") or {}).get("employeeId") or "").strip().lower()

    return bool(
        (p_eid and p_eid in candidate_ids) or \
        (p_eid2 and p_eid2 in candidate_ids) or \
        (p_mail and p_mail in candidate_ids) or \
        (p_doc and p_doc in candidate_ids) or \
        (p_detail_eid and p_detail_eid in candidate_ids) or \
        (p_detail_eid2 and p_detail_eid2 in candidate_ids)
    )


@router.get("", response_model=List[dict])
def list_payslips(current_user: Any = Depends(get_current_user)):
    """
    List payslips.
    Employees receive only their own payslips with full candidate expansion.
    Super Admins, HR Admins, and Payroll Admins receive all company payslips.
    """
    role = str(getattr(current_user, "role", "employee")).lower()
    all_payslips = FirestoreService.get_all("payslips")

    if role == "employee":
        emp_payslips = [p for p in all_payslips if _is_payslip_authorized_for_user(p, current_user)]
        return sorted(emp_payslips, key=lambda x: (int(x.get("year", 0)), int(x.get("month", 0))), reverse=True)

    # Admin view
    return sorted(all_payslips, key=lambda x: (int(x.get("year", 0)), int(x.get("month", 0))), reverse=True)


@router.get("/{payslip_id}")
def get_payslip(payslip_id: str, current_user: Any = Depends(get_current_user)):
    """Retrieve detailed payslip metadata and itemized breakdown."""
    payslip = FirestoreService.get_by_id("payslips", str(payslip_id))
    if not payslip:
        # Check by payslip_number or id
        all_p = FirestoreService.get_all("payslips")
        for p in all_p:
            if str(p.get("id") or p.get("_firestore_id") or p.get("payslip_number")) == str(payslip_id):
                payslip = p
                break

    if not payslip:
        raise HTTPException(status_code=404, detail="Payslip record not found.")

    role = str(getattr(current_user, "role", "employee")).lower()
    if role == "employee" and not _is_payslip_authorized_for_user(payslip, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized: You can only view your own payslips.",
        )

    return payslip


@router.get("/{payslip_id}/download")
def download_payslip_pdf(payslip_id: str, current_user: Any = Depends(get_current_user)):
    """
    Dynamically renders and streams the professional branded PDF payslip.
    """
    payslip = FirestoreService.get_by_id("payslips", str(payslip_id))
    if not payslip:
        all_p = FirestoreService.get_all("payslips")
        for p in all_p:
            if str(p.get("id") or p.get("_firestore_id") or p.get("payslip_number")) == str(payslip_id):
                payslip = p
                break

    if not payslip:
        raise HTTPException(status_code=404, detail="Payslip record not found.")

    role = str(getattr(current_user, "role", "employee")).lower()
    if role == "employee" and not _is_payslip_authorized_for_user(payslip, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized: You can only download your own payslip.",
        )

    detail = payslip.get("detail", payslip)
    run_info = {
        "month": payslip.get("month", 1),
        "month_name": payslip.get("month_name", "Month"),
        "year": payslip.get("year", 2026),
    }

    try:
        pdf_bytes = generate_payslip_pdf(detail, run_info)
        emp_id = payslip.get("employee_id", "EMP")
        month = payslip.get("month", 1)
        year = payslip.get("year", 2026)
        filename = f"Payslip_{year}_{month:02d}_{emp_id}.pdf"

        # Update download status
        FirestoreService.update("payslips", str(payslip.get("id") or payslip_id), {
            "status": "Downloaded",
            "last_downloaded_at": datetime.now(timezone.utc).isoformat(),
        })

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\"",
                "Access-Control-Expose-Headers": "Content-Disposition",
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate payslip PDF: {str(e)}",
        )
