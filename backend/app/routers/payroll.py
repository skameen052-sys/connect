"""
Payroll API Router
Manages automated monthly payroll batch calculations, exception reviews,
multi-stage approvals, finalization locks, and immutability controls.
"""

from typing import List, Optional, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.dependencies.auth import get_current_user, get_current_admin
from app.services.firestore_service import FirestoreService
from app.services.payroll_engine import PayrollEngine, round_curr

router = APIRouter(prefix="/payroll", tags=["Payroll Engine"])


class CalculatePayrollRequest(BaseModel):
    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2020, le=2050)
    custom_payroll_days: Optional[int] = Field(default=None, ge=20, le=31)
    notes: Optional[str] = None


class PayrollActionRequest(BaseModel):
    notes: Optional[str] = None


@router.get("/runs", response_model=List[dict])
def list_payroll_runs(current_user: Any = Depends(get_current_admin)):
    """List all monthly payroll calculation batches."""
    runs = FirestoreService.get_all("payroll_runs")
    # Sort descending by year and month
    def sort_key(r):
        return (int(r.get("year", 0)), int(r.get("month", 0)))
    sorted_runs = sorted(runs, key=sort_key, reverse=True)
    return sorted_runs


@router.get("/runs/{run_id}")
def get_payroll_run(run_id: str, current_user: Any = Depends(get_current_admin)):
    """Retrieve full payroll batch details including all employee line items."""
    run = FirestoreService.get_by_id("payroll_runs", str(run_id))
    if not run:
        # Try finding in list by string or int id
        all_runs = FirestoreService.get_all("payroll_runs")
        for r in all_runs:
            if str(r.get("id") or r.get("_firestore_id")) == str(run_id):
                run = r
                break

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payroll batch '{run_id}' was not found.",
        )

    return run


@router.post("/calculate", status_code=status.HTTP_201_CREATED)
def calculate_monthly_payroll(payload: CalculatePayrollRequest, current_user: Any = Depends(get_current_admin)):
    """
    Executes automated attendance-driven payroll calculation engine for the designated month/year.
    Validates attendance punches, approved leaves, LOP, statutory PF/ESI, and active loan deductions.
    """
    admin_id = str(getattr(current_user, "id", None) or getattr(current_user, "uid", "admin"))
    admin_email = getattr(current_user, "email", "admin@arshith.com")

    try:
        run = PayrollEngine.process_monthly_payroll_run(
            year=payload.year,
            month=payload.month,
            user_id=admin_id,
            user_email=admin_email,
            notes=payload.notes or "",
            custom_payroll_days=payload.custom_payroll_days,
        )
        return {
            "message": f"Payroll calculation completed for {payload.month:02d}/{payload.year}.",
            "run": run,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Calculation engine encountered an error: {str(e)}",
        )


@router.post("/runs/{run_id}/review")
def review_payroll_run(run_id: str, payload: PayrollActionRequest, current_user: Any = Depends(get_current_admin)):
    """Transitions payroll run from CALCULATED to UNDER_REVIEW."""
    run = FirestoreService.get_by_id("payroll_runs", str(run_id))
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    cur_status = str(run.get("status", "")).upper()
    if cur_status not in ["CALCULATED", "DRAFT"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot move run in status '{cur_status}' to UNDER_REVIEW."
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    reviewer = getattr(current_user, "email", "admin")
    update_data = {
        "status": "UNDER_REVIEW",
        "reviewed_by": reviewer,
        "reviewed_at": now_iso,
        "review_notes": payload.notes,
        "updated_at": now_iso,
    }
    FirestoreService.update("payroll_runs", str(run_id), update_data)
    run.update(update_data)
    return {"message": "Payroll run moved to UNDER_REVIEW status.", "run": run}


@router.post("/runs/{run_id}/approve")
def approve_payroll_run(run_id: str, payload: PayrollActionRequest, current_user: Any = Depends(get_current_admin)):
    """Authorized approval transitioning payroll run to APPROVED."""
    run = FirestoreService.get_by_id("payroll_runs", str(run_id))
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    cur_status = str(run.get("status", "")).upper()
    if cur_status not in ["CALCULATED", "UNDER_REVIEW"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve payroll run in status '{cur_status}'. Must be CALCULATED or UNDER_REVIEW."
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    approver = getattr(current_user, "email", "admin")
    update_data = {
        "status": "APPROVED",
        "approved_by": approver,
        "approved_at": now_iso,
        "approval_notes": payload.notes,
        "updated_at": now_iso,
    }
    FirestoreService.update("payroll_runs", str(run_id), update_data)
    run.update(update_data)
    return {"message": "Payroll run approved successfully.", "run": run}


@router.post("/runs/{run_id}/finalize")
def finalize_payroll_run(run_id: str, payload: PayrollActionRequest, current_user: Any = Depends(get_current_admin)):
    """
    Finalizes and locks the payroll run.
    1. Sets status to FINALIZED (immutable).
    2. Generates individual digital payslip records.
    3. Decrements outstanding balances on employee loans.
    4. Generates salary payment disbursement queue.
    """
    run = FirestoreService.get_by_id("payroll_runs", str(run_id))
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    cur_status = str(run.get("status", "")).upper()
    if cur_status != "APPROVED":
        raise HTTPException(
            status_code=400,
            detail=f"Only APPROVED payroll runs can be finalized. Current status is '{cur_status}'."
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    finalizer = getattr(current_user, "email", "admin")
    details = run.get("details", [])

    # 1. Generate payslips in collection
    month = run.get("month", 1)
    year = run.get("year", 2026)
    month_name = run.get("month_name", "Month")

    for d in details:
        emp_id = str(d.get("employee_id"))
        ps_num = f"PS-{year}{month:02d}-{emp_id}"
        
        payslip_doc = {
            "payslip_number": ps_num,
            "payroll_run_id": str(run_id),
            "employee_id": emp_id,
            "employee_name": d.get("employee_name"),
            "department": d.get("department"),
            "designation": d.get("designation"),
            "month": month,
            "year": year,
            "month_name": month_name,
            "payable_days": d.get("payable_days"),
            "unpaid_days": d.get("unpaid_days"),
            "gross_salary": d.get("gross_salary"),
            "loss_of_pay": d.get("loss_of_pay"),
            "adjusted_gross": d.get("adjusted_gross"),
            "total_deductions": d.get("total_deductions"),
            "net_salary": d.get("net_salary"),
            "detail": d,
            "status": "Generated",
            "generated_at": now_iso,
        }
        FirestoreService.create("payslips", payslip_doc)

        # 2. Decrement loan balance if loan deduction was made
        loan_id = d.get("loan_id")
        loan_ded = float(d.get("loan_deduction", 0.0))
        if loan_id and loan_ded > 0:
            loan_doc = FirestoreService.get_by_id("employee_loans", str(loan_id))
            if loan_doc:
                cur_bal = float(loan_doc.get("remaining_balance", 0.0))
                new_bal = max(0.0, round_curr(cur_bal - loan_ded))
                l_update = {
                    "remaining_balance": new_bal,
                    "updated_at": now_iso,
                }
                if new_bal <= 0:
                    l_update["status"] = "CLOSED"
                FirestoreService.update("employee_loans", str(loan_id), l_update)

        # 3. Create salary payment record
        payment_doc = {
            "payroll_run_id": str(run_id),
            "employee_id": emp_id,
            "employee_name": d.get("employee_name"),
            "amount": d.get("net_salary"),
            "bank_name": d.get("bank_name", "HDFC"),
            "account_number": d.get("account_number", "XXXX"),
            "payment_reference": f"PAY-{year}{month:02d}-{emp_id}",
            "payment_method": "Bank Transfer",
            "status": "Approved",
            "created_at": now_iso,
        }
        FirestoreService.create("salary_payments", payment_doc)

    update_data = {
        "status": "FINALIZED",
        "finalized_by": finalizer,
        "finalized_at": now_iso,
        "finalization_notes": payload.notes,
        "updated_at": now_iso,
    }
    FirestoreService.update("payroll_runs", str(run_id), update_data)
    run.update(update_data)

    return {
        "message": f"Payroll run finalized and locked successfully. Generated {len(details)} payslips and payment records.",
        "run": run,
    }


@router.get("/runs/{run_id}/exceptions")
def get_payroll_exceptions(run_id: str, current_user: Any = Depends(get_current_admin)):
    """Inspect attendance anomalies, high LOP instances, and missing records."""
    run = FirestoreService.get_by_id("payroll_runs", str(run_id))
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    details = run.get("details", [])
    high_lop_cases = [d for d in details if float(d.get("unpaid_days", 0)) >= 3.0]
    zero_pay_cases = [d for d in details if float(d.get("payable_days", 0)) <= 0.0]

    return {
        "run_id": run_id,
        "total_employees": len(details),
        "high_lop_cases": high_lop_cases,
        "zero_pay_cases": zero_pay_cases,
        "all_clear": len(high_lop_cases) == 0 and len(zero_pay_cases) == 0,
    }


@router.delete("/runs/{run_id}")
def delete_payroll_run(run_id: str, current_user: Any = Depends(get_current_admin)):
    """
    Deletes a preliminary DRAFT or CALCULATED payroll run.
    Guards immutability: Rejects deletion if run is FINALIZED or PAID.
    """
    run = FirestoreService.get_by_id("payroll_runs", str(run_id))
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    cur_status = str(run.get("status", "")).upper()
    if cur_status in ["FINALIZED", "PAYMENT_PROCESSING", "PAID"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Integrity Violation: Finalized or disbursed payroll runs cannot be deleted.",
        )

    FirestoreService.delete("payroll_runs", str(run_id))
    return {"message": f"Preliminary payroll batch '{run_id}' deleted successfully."}
