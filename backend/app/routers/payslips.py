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


@router.get("", response_model=List[dict])
def list_payslips(current_user: Any = Depends(get_current_user)):
    """
    List payslips.
    Employees receive only their own payslips.
    Super Admins, HR Admins, and Payroll Admins receive all company payslips.
    """
    role = str(getattr(current_user, "role", "employee")).lower()
    user_emp_id = str(getattr(current_user, "employee_id", "") or getattr(current_user, "employeeId", ""))

    all_payslips = FirestoreService.get_all("payslips")

    if role == "employee":
        # Filter for this employee only
        emp_payslips = [
            p for p in all_payslips
            if str(p.get("employee_id") or p.get("employeeId")) == user_emp_id
        ]
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
    user_emp_id = str(getattr(current_user, "employee_id", "") or getattr(current_user, "employeeId", ""))

    if role == "employee" and str(payslip.get("employee_id")) != user_emp_id:
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
    user_emp_id = str(getattr(current_user, "employee_id", "") or getattr(current_user, "employeeId", ""))

    if role == "employee" and str(payslip.get("employee_id")) != user_emp_id:
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
