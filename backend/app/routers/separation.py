"""
Resignation & Full-and-Final (FnF) Settlement API Router
Manages separation requests, notice period tracking, clearance checklists,
automated settlement calculations, and statement PDF generation.
"""

from typing import List, Optional, Any
from datetime import datetime, timezone, date
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.dependencies.auth import get_current_user, get_current_admin
from app.services.firestore_service import FirestoreService
from app.services.fnf_engine import FnFEngine

router = APIRouter(prefix="/separation", tags=["Resignation & FnF Settlement"])


class ResignationSubmitRequest(BaseModel):
    employee_id: Optional[str] = None
    reason: str = Field(..., min_length=5)
    intended_last_date: str
    notice_period_days: int = Field(default=30, ge=0)


class ResignationApproveRequest(BaseModel):
    approved_last_working_date: str
    notice_shortfall_days: float = Field(default=0.0, ge=0)
    notes: Optional[str] = None


class FnFCalculateRequest(BaseModel):
    days_worked_in_final_month: float = Field(..., ge=0, le=31)
    accrued_unused_leaves: float = Field(default=0.0, ge=0)
    other_additions: float = Field(default=0.0, ge=0)
    other_deductions: float = Field(default=0.0, ge=0)


@router.get("/requests", response_model=List[dict])
def list_separation_requests(current_user: Any = Depends(get_current_user)):
    """List resignation requests. Employees view their own; Admins view all."""
    role = str(getattr(current_user, "role", "employee")).lower()
    caller_emp_id = str(getattr(current_user, "employee_id", "") or getattr(current_user, "employeeId", ""))

    all_reqs = FirestoreService.get_all("resignations")

    if role == "employee":
        emp_reqs = [r for r in all_reqs if str(r.get("employee_id") or r.get("employeeId")) == caller_emp_id]
        return sorted(emp_reqs, key=lambda x: str(x.get("created_at", "")), reverse=True)

    employees = FirestoreService.get_all("employees")
    emp_map = {
        str(e.get("employee_id") or e.get("employeeId") or e.get("id")): e
        for e in employees
    }

    for r in all_reqs:
        eid = str(r.get("employee_id") or r.get("employeeId"))
        emp = emp_map.get(eid, {})
        r["employee_name"] = emp.get("name") or emp.get("full_name") or "Employee"
        r["department"] = emp.get("department") or emp.get("dept") or "Operations"
        r["designation"] = emp.get("designation") or emp.get("role") or "Staff"

    return sorted(all_reqs, key=lambda x: str(x.get("created_at", "")), reverse=True)


@router.post("/submit", status_code=status.HTTP_201_CREATED)
def submit_resignation(payload: ResignationSubmitRequest, current_user: Any = Depends(get_current_user)):
    """Submit an employee resignation application."""
    role = str(getattr(current_user, "role", "employee")).lower()
    caller_emp_id = str(getattr(current_user, "employee_id", "") or getattr(current_user, "employeeId", ""))

    target_emp_id = payload.employee_id if (role != "employee" and payload.employee_id) else caller_emp_id
    if not target_emp_id:
        raise HTTPException(status_code=400, detail="Employee ID could not be identified.")

    now_iso = datetime.now(timezone.utc).isoformat()
    doc = {
        "employee_id": target_emp_id,
        "reason": payload.reason,
        "resignation_date": str(date.today()),
        "intended_last_date": payload.intended_last_date,
        "notice_period_days": payload.notice_period_days,
        "status": "SUBMITTED",
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    created = FirestoreService.create("resignations", doc)
    return {"message": "Resignation submitted successfully.", "data": created}


@router.patch("/{separation_id}/approve")
def approve_resignation(separation_id: str, payload: ResignationApproveRequest, current_user: Any = Depends(get_current_admin)):
    """Approve employee resignation and set the official last working date."""
    resignation = FirestoreService.get_by_id("resignations", str(separation_id))
    if not resignation:
        raise HTTPException(status_code=404, detail="Resignation record not found.")

    now_iso = datetime.now(timezone.utc).isoformat()
    approver = getattr(current_user, "email", "admin")

    update_data = {
        "status": "APPROVED",
        "last_working_date": payload.approved_last_working_date,
        "notice_shortfall_days": payload.notice_shortfall_days,
        "approved_by": approver,
        "approved_at": now_iso,
        "notes": payload.notes,
        "updated_at": now_iso,
    }

    FirestoreService.update("resignations", str(separation_id), update_data)
    resignation.update(update_data)
    return {"message": "Resignation approved. Proceed to FnF settlement calculation.", "data": resignation}


@router.post("/{separation_id}/calculate-fnf")
def calculate_separation_settlement(separation_id: str, payload: FnFCalculateRequest, current_user: Any = Depends(get_current_admin)):
    """
    Computes Full & Final settlement for the resigned employee.
    Includes final month prorated pay, leave encashment, gratuity, notice recovery, and loan netting.
    """
    resignation = FirestoreService.get_by_id("resignations", str(separation_id))
    if not resignation:
        raise HTTPException(status_code=404, detail="Resignation record not found.")

    emp_id = str(resignation.get("employee_id"))
    employees = FirestoreService.get_all("employees")
    emp = next((e for e in employees if str(e.get("employee_id") or e.get("id")) == emp_id), {})

    # Fetch active salary structure
    structures = FirestoreService.get_all("salary_structures")
    struct = next((s for s in structures if str(s.get("employee_id")) == emp_id and s.get("is_active", True)), None)
    
    basic = float(struct.get("basic_salary", 20000.0) if struct else 20000.0)
    gross = float(struct.get("gross_salary", 32000.0) if struct else 32000.0)

    # Calculate years of service
    joining_str = str(emp.get("joining_date") or emp.get("joining") or "2024-01-01")
    try:
        j_date = datetime.strptime(joining_str, "%Y-%m-%d").date()
        years_service = max(0.5, (date.today() - j_date).days / 365.25)
    except Exception:
        years_service = 1.0

    # Check outstanding loans
    all_loans = FirestoreService.get_all("employee_loans")
    emp_loans = [l for l in all_loans if str(l.get("employee_id")) == emp_id and str(l.get("status", "")).upper() == "ACTIVE"]
    loan_bal = sum(float(l.get("remaining_balance", 0.0)) for l in emp_loans)

    shortfall = float(resignation.get("notice_shortfall_days", 0.0))

    calc = FnFEngine.calculate_fnf(
        gross_salary=gross,
        basic_salary=basic,
        days_worked_in_final_month=payload.days_worked_in_final_month,
        accrued_unused_leaves=payload.accrued_unused_leaves,
        years_of_service=years_service,
        notice_period_shortfall_days=shortfall,
        outstanding_loan_balance=loan_bal,
        other_additions=payload.other_additions,
        other_deductions=payload.other_deductions,
    )

    now_iso = datetime.now(timezone.utc).isoformat()
    fnf_record = {
        "separation_id": str(separation_id),
        "employee_id": emp_id,
        "employee_name": emp.get("name") or emp.get("full_name") or "Employee",
        "settlement_calculation": calc,
        "status": "SETTLED",
        "calculated_by": getattr(current_user, "email", "admin"),
        "calculated_at": now_iso,
    }

    FirestoreService.update("resignations", str(separation_id), {
        "status": "SETTLED",
        "fnf_settlement": calc,
        "updated_at": now_iso,
    })

    # Close any active loans
    for l in emp_loans:
        FirestoreService.update("employee_loans", str(l.get("id")), {
            "status": "CLOSED",
            "remaining_balance": 0.0,
            "closed_reason": "Settled via FnF",
            "updated_at": now_iso,
        })

    # Update employee status to Resigned
    FirestoreService.update("employees", emp_id, {
        "status": "Resigned",
        "resigned_at": now_iso,
        "updated_at": now_iso,
    })

    return {
        "message": "Full & Final settlement successfully computed and settled.",
        "calculation": calc,
    }


@router.get("/{separation_id}/statement")
def download_fnf_statement_pdf(separation_id: str, current_user: Any = Depends(get_current_user)):
    """Download official Full & Final settlement statement PDF."""
    resignation = FirestoreService.get_by_id("resignations", str(separation_id))
    if not resignation:
        raise HTTPException(status_code=404, detail="Resignation record not found.")

    emp_id = str(resignation.get("employee_id"))
    employees = FirestoreService.get_all("employees")
    emp = next((e for e in employees if str(e.get("employee_id") or e.get("id")) == emp_id), {})

    calc = resignation.get("fnf_settlement")
    if not calc:
        raise HTTPException(status_code=400, detail="FnF settlement has not yet been computed for this resignation.")

    try:
        pdf_bytes = FnFEngine.generate_fnf_statement_pdf(emp, calc, resignation)
        filename = f"FnF_Statement_{emp_id}.pdf"
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
            detail=f"Failed to generate FnF statement: {str(e)}",
        )
