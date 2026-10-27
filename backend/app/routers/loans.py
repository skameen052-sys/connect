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
    employee_name: Optional[str] = None
    employee_email: Optional[str] = None
    department: Optional[str] = None
    loan_type: str = Field(..., min_length=2)
    principal_amount: float = Field(..., gt=0)
    term_months: int = Field(..., ge=1, le=60)
    reason: str = Field(..., min_length=3)


class LoanStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(APPROVED|REJECTED|CLOSED|ACTIVE)$")
    rejection_reason: Optional[str] = None
    approved_remarks: Optional[str] = None


@router.get("", response_model=List[dict])
def list_loans(employee_id: Optional[str] = None, current_user: Any = Depends(get_current_user)):
    """List loan applications. Filtered for employees to only see their own applications."""
    role = str(getattr(current_user, "role", "employee")).lower()
    caller_emp_id = str(getattr(current_user, "employee_id", "") or getattr(current_user, "employeeId", "") or getattr(current_user, "id", "") or "").strip()
    caller_email = str(getattr(current_user, "email", "") or "").strip().lower()

    all_loans = FirestoreService.get_all("employee_loans")
    employees = FirestoreService.get_all("employees")

    if role == "employee" or employee_id:
        candidate_ids = set()
        if employee_id:
            candidate_ids.add(str(employee_id).strip().lower())
        if caller_emp_id:
            candidate_ids.add(caller_emp_id.lower())
        if caller_email:
            candidate_ids.add(caller_email)

        # Cross-reference with employee directory to expand candidate identifiers
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

        matched_loans = []
        for l in all_loans:
            l_eid = str(l.get("employee_id") or "").strip().lower()
            l_eid2 = str(l.get("employeeId") or "").strip().lower()
            l_email = str(l.get("employee_email") or l.get("email") or "").strip().lower()
            l_doc_id = str(l.get("employee_doc_id") or "").strip().lower()

            if (l_eid and l_eid in candidate_ids) or \
               (l_eid2 and l_eid2 in candidate_ids) or \
               (l_email and l_email in candidate_ids) or \
               (l_doc_id and l_doc_id in candidate_ids):
                matched_loans.append(l)

        all_loans = matched_loans

    # Enrich metadata for employee_name and department
    emp_map = {}
    for e in employees:
        if e.get("id"): emp_map[str(e["id"]).lower()] = e
        if e.get("employeeId"): emp_map[str(e["employeeId"]).lower()] = e
        if e.get("employee_id"): emp_map[str(e["employee_id"]).lower()] = e
        if e.get("email"): emp_map[str(e["email"]).lower()] = e

    for l in all_loans:
        eid = str(l.get("employee_id") or l.get("employeeId") or "").lower()
        l_email = str(l.get("employee_email") or "").lower()
        emp = emp_map.get(eid) or emp_map.get(l_email) or {}
        l["employee_name"] = l.get("employee_name") or emp.get("name") or emp.get("full_name") or emp.get("fullName") or "Employee"
        l["department"] = l.get("department") or emp.get("department") or emp.get("dept") or "Engineering"

    return sorted(all_loans, key=lambda x: str(x.get("created_at", "")), reverse=True)


@router.post("/apply", status_code=status.HTTP_201_CREATED)
def apply_for_loan(payload: LoanApplyRequest, current_user: Any = Depends(get_current_user)):
    """Apply for a new loan or salary advance."""
    role = str(getattr(current_user, "role", "employee")).lower()
    caller_emp_id = str(getattr(current_user, "employee_id", "") or getattr(current_user, "employeeId", "") or getattr(current_user, "id", "") or "").strip()
    caller_email = str(getattr(current_user, "email", "") or "").strip().lower()
    caller_name = str(getattr(current_user, "name", "") or getattr(current_user, "fullName", "") or getattr(current_user, "full_name", "") or "").strip()

    target_emp_id = payload.employee_id or caller_emp_id or "EMP-1001"

    # Cross-reference with employees directory
    employees = FirestoreService.get_all("employees")
    matched_emp = next((
        e for e in employees
        if str(e.get("employeeId") or "").strip().lower() == target_emp_id.lower()
        or str(e.get("employee_id") or "").strip().lower() == target_emp_id.lower()
        or str(e.get("id") or "").strip().lower() == target_emp_id.lower()
        or str(e.get("uid") or "").strip().lower() == target_emp_id.lower()
        or (caller_email and str(e.get("email") or "").strip().lower() == caller_email)
        or (payload.employee_email and str(e.get("email") or "").strip().lower() == payload.employee_email.lower())
    ), {})

    canonical_eid = matched_emp.get("employeeId") or matched_emp.get("employee_id") or matched_emp.get("id") or target_emp_id
    canonical_name = payload.employee_name or matched_emp.get("name") or matched_emp.get("fullName") or matched_emp.get("full_name") or caller_name or "Employee"
    canonical_email = payload.employee_email or matched_emp.get("email") or caller_email
    canonical_dept = payload.department or matched_emp.get("department") or matched_emp.get("dept") or "Engineering"
    emp_doc_id = str(matched_emp.get("id") or "")

    # Calculate monthly installment
    monthly_emi = round_curr(payload.principal_amount / payload.term_months)
    now_iso = datetime.now(timezone.utc).isoformat()

    new_loan = {
        "employee_id": canonical_eid,
        "employeeId": canonical_eid,
        "employee_name": canonical_name,
        "employee_email": canonical_email,
        "department": canonical_dept,
        "employee_doc_id": emp_doc_id,
        "loan_type": payload.loan_type,
        "principal_amount": float(payload.principal_amount),
        "term_months": int(payload.term_months),
        "monthly_installment": monthly_emi,
        "remaining_balance": float(payload.principal_amount),
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
    if new_status in ["APPROVE", "APPROVED"]:
        new_status = "APPROVED"
    elif new_status in ["REJECT", "REJECTED"]:
        new_status = "REJECTED"

    update_data = {
        "status": new_status,
        "approved_by": approver if new_status == "APPROVED" else loan.get("approved_by"),
        "approved_at": now_iso if new_status == "APPROVED" else loan.get("approved_at"),
        "approved_remarks": payload.approved_remarks or loan.get("approved_remarks"),
        "rejection_reason": payload.rejection_reason if new_status == "REJECTED" else None,
        "rejected_by": approver if new_status == "REJECTED" else loan.get("rejected_by"),
        "rejected_at": now_iso if new_status == "REJECTED" else loan.get("rejected_at"),
        "updated_at": now_iso,
    }

    FirestoreService.update("employee_loans", str(loan_id), update_data)
    loan.update(update_data)
    return {"message": f"Loan application {new_status.lower()} successfully.", "data": loan}


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
