"""
Salary Payments API Router
Tracks payment disbursement statuses, generates corporate bank transfer files (NEFT/RTGS),
and records transaction UTR payment confirmations.
"""

from typing import List, Optional, Any
from datetime import datetime, timezone, date
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.dependencies.auth import get_current_user, get_current_admin
from app.services.firestore_service import FirestoreService
from app.services.bank_export import generate_bank_payment_csv

router = APIRouter(prefix="/payments", tags=["Salary Payments"])


class BankExportRequest(BaseModel):
    payroll_run_id: str


class PaymentConfirmationRequest(BaseModel):
    payment_ids: List[str]
    transaction_reference: str = Field(..., min_length=4)
    payment_date: Optional[str] = None
    status: str = Field(default="Paid")
    notes: Optional[str] = None


@router.get("/all")
def list_all_payments(current_user: Any = Depends(get_current_admin)):
    """List all payment disbursement records across payroll runs."""
    payments = FirestoreService.get_all("salary_payments")
    return sorted(payments, key=lambda x: str(x.get("created_at", "")), reverse=True)


@router.get("/runs/{run_id}")
def get_payments_for_run(run_id: str, current_user: Any = Depends(get_current_admin)):
    """List payment disbursement line items for a specific payroll run."""
    payments = FirestoreService.get_all("salary_payments")
    matching = [p for p in payments if str(p.get("payroll_run_id")) == str(run_id)]
    return matching


@router.post("/export-bank-file")
def export_bank_payment_file(payload: BankExportRequest, current_user: Any = Depends(get_current_admin)):
    """
    Exports a standard CSV file for corporate banking bulk transfer upload (NEFT / RTGS).
    """
    run = FirestoreService.get_by_id("payroll_runs", str(payload.payroll_run_id))
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    details = run.get("details", [])
    if not details:
        raise HTTPException(status_code=400, detail="No employee line items found in this payroll batch.")

    csv_data = generate_bank_payment_csv(run, details)
    month = run.get("month", 1)
    year = run.get("year", 2026)
    filename = f"Bank_Disbursement_Batch_{year}_{month:02d}.csv"

    # Update payroll run status to PAYMENT_PROCESSING if currently FINALIZED
    if str(run.get("status", "")).upper() == "FINALIZED":
        FirestoreService.update("payroll_runs", str(payload.payroll_run_id), {
            "status": "PAYMENT_PROCESSING",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\"",
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.post("/record-confirmation")
def record_payment_confirmation(payload: PaymentConfirmationRequest, current_user: Any = Depends(get_current_admin)):
    """
    Records transaction reference (UTR number) and confirms bank disbursement.
    Updates payment records and parent payroll run status to PAID / PARTIALLY_PAID.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    pay_date = payload.payment_date or str(date.today())
    confirmer = getattr(current_user, "email", "admin")

    affected_run_ids = set()

    for pid in payload.payment_ids:
        p_doc = FirestoreService.get_by_id("salary_payments", str(pid))
        if p_doc:
            FirestoreService.update("salary_payments", str(pid), {
                "status": payload.status,
                "transaction_reference": payload.transaction_reference,
                "payment_date": pay_date,
                "confirmed_by": confirmer,
                "confirmed_at": now_iso,
                "notes": payload.notes,
                "updated_at": now_iso,
            })
            if p_doc.get("payroll_run_id"):
                affected_run_ids.add(str(p_doc.get("payroll_run_id")))

    # Check and update parent payroll run status
    for run_id in affected_run_ids:
        all_payments = FirestoreService.get_all("salary_payments")
        run_payments = [p for p in all_payments if str(p.get("payroll_run_id")) == str(run_id)]
        
        all_paid = all(str(p.get("status", "")).lower() == "paid" for p in run_payments)
        any_paid = any(str(p.get("status", "")).lower() == "paid" for p in run_payments)

        if all_paid and len(run_payments) > 0:
            new_status = "PAID"
        elif any_paid:
            new_status = "PARTIALLY_PAID"
        else:
            new_status = "PAYMENT_PROCESSING"

        FirestoreService.update("payroll_runs", str(run_id), {
            "status": new_status,
            "disbursed_at": now_iso,
            "updated_at": now_iso,
        })

    return {
        "message": f"Recorded payment confirmations for {len(payload.payment_ids)} employee records.",
        "transaction_reference": payload.transaction_reference,
    }
