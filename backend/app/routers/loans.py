"""
Employee Loans & Salary Advances API Router
Manages loan applications, approvals, monthly EMI calculations, and outstanding balance tracking.
"""

from typing import List, Optional, Any
from datetime import datetime, timezone, date
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.dependencies.auth import get_current_user, get_current_admin
from app.services.firestore_service import FirestoreService
from app.services.payroll_engine import round_curr

router = APIRouter(prefix="/loans", tags=["Loans & Advances"])


class LoanApplyRequest(BaseModel):
    employee_id: Optional[str] = None
    loan_type: str = Field(..., pattern="^(Personal Loan|Salary Advance|Emergency Advance|Education Loan)$")
    principal_amount: float = Field(..., gt=0)
    term_months: int = Field(..., ge=1, le=36)
    reason: str = Field(..., min_length=5)


class LoanStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(APPROVED|REJECTED|CLOSED|ACTIVE)$")
    rejection_reason: Optional[str] = None


@router.get("", response_model=List[dict])
def list_loans(current_user: Any = Depends(get_current_user)):
    """List loan applications. Employees view their own; Admins view all."""
    role = str(getattr(current_user, "role", "employee")).lower()
    caller_emp_id = str(getattr(current_user, "employee_id", "") or getattr(current_user, "employeeId", ""))

    all_loans = FirestoreService.get_all("employee_loans")

    if role == "employee":
        emp_loans = [l for l in all_loans if str(l.get("employee_id") or l.get("employeeId")) == caller_emp_id]
        return sorted(emp_loans, key=lambda x: str(x.get("created_at", "")), reverse=True)

    # Enrich with employee names for admin
    employees = FirestoreService.get_all("employees")
    emp_map = {
        str(e.get("employee_id") or e.get("employeeId") or e.get("id")): e
        for e in employees
    }

    for l in all_loans:
        eid = str(l.get("employee_id") or l.get("employeeId"))
        emp = emp_map.get(eid, {})
        l["employee_name"] = emp.get("name") or emp.get("full_name") or "Employee"
        l["department"] = emp.get("department") or emp.get("dept") or "General"

    return sorted(all_loans, key=lambda x: str(x.get("created_at", "")), reverse=True)


@router.post("/apply", status_code=status.HTTP_201_CREATED)
def apply_for_loan(payload: LoanApplyRequest, current_user: Any = Depends(get_current_user)):
    """Apply for a new loan or salary advance."""
    role = str(getattr(current_user, "role", "employee")).lower()
    caller_emp_id = str(getattr(current_user, "employee_id", "") or getattr(current_user, "employeeId", ""))

    target_emp_id = payload.employee_id if (role != "employee" and payload.employee_id) else caller_emp_id
    if not target_emp_id:
        raise HTTPException(status_code=400, detail="Employee ID could not be identified.")

    # Calculate monthly installment
    monthly_emi = round_curr(payload.principal_amount / payload.term_months)
    now_iso = datetime.now(timezone.utc).isoformat()

    new_loan = {
        "employee_id": target_emp_id,
        "loan_type": payload.loan_type,
        "principal_amount": payload.principal_amount,
        "term_months": payload.term_months,
        "monthly_installment": monthly_emi,
        "remaining_balance": payload.principal_amount,
        "status": "PENDING",
        "reason": payload.reason,
        "applied_date": str(date.today()),
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    created = FirestoreService.create("employee_loans", new_loan)
    return {"message": "Loan application submitted successfully.", "data": created}


@router.patch("/{loan_id}/status")
def update_loan_status(loan_id: str, payload: LoanStatusUpdate, current_user: Any = Depends(get_current_admin)):
    """Approve or reject a loan application."""
    loan = FirestoreService.get_by_id("employee_loans", str(loan_id))
    if not loan:
        raise HTTPException(status_code=404, detail="Loan record not found.")

    now_iso = datetime.now(timezone.utc).isoformat()
    approver = getattr(current_user, "email", "admin")

    new_status = payload.status.upper()
    update_data = {
        "status": "ACTIVE" if new_status == "APPROVED" else new_status,
        "approved_by": approver,
        "approved_at": now_iso if new_status == "APPROVED" else None,
        "rejection_reason": payload.rejection_reason,
        "updated_at": now_iso,
    }

    FirestoreService.update("employee_loans", str(loan_id), update_data)
    loan.update(update_data)
    return {"message": f"Loan status updated to {new_status}.", "data": loan}


@router.get("/{loan_id}/schedule")
def get_loan_repayment_schedule(loan_id: str, current_user: Any = Depends(get_current_user)):
    """Generate simulated or actual repayment schedule for the loan."""
    loan = FirestoreService.get_by_id("employee_loans", str(loan_id))
    if not loan:
        raise HTTPException(status_code=404, detail="Loan record not found.")

    principal = float(loan.get("principal_amount", 0.0))
    months = int(loan.get("term_months", 1))
    emi = float(loan.get("monthly_installment", 0.0))

    schedule = []
    rem = principal
    for i in range(1, months + 1):
        rem = max(0.0, round_curr(rem - emi))
        schedule.append({
            "installment_no": i,
            "due_month": f"Month {i}",
            "amount": emi,
            "remaining_balance": rem,
            "status": "Deducted via Payroll" if rem < float(loan.get("remaining_balance", 0.0)) else "Pending",
        })

    return {
        "loan_id": loan_id,
        "principal": principal,
        "term_months": months,
        "monthly_emi": emi,
        "remaining_balance": loan.get("remaining_balance"),
        "schedule": schedule,
    }
