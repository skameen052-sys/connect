"""
Company & Payroll Settings API Router
Manages organization profile, attendance cutoff rules, payroll calculation denominators,
and statutory contribution ceilings.
"""

from typing import Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.dependencies.auth import get_current_user, get_current_admin
from app.services.firestore_service import FirestoreService

router = APIRouter(prefix="/settings", tags=["Company Settings"])


class CompanySettingsUpdate(BaseModel):
    company_name: str = "Arshith Connect"
    company_email: str = "payroll@arshith.com"
    company_phone: str = "+91 98765 43210"
    company_address: str = "Tech Center, HITEC City, Hyderabad, India"
    daily_rate_denominator: int = Field(default=30, ge=20, le=31)
    attendance_cutoff_day: int = Field(default=25, ge=1, le=31)
    pf_wage_ceiling: float = Field(default=15000.0, ge=0)
    esi_wage_ceiling: float = Field(default=21000.0, ge=0)
    overtime_multiplier: float = Field(default=1.5, ge=1.0)
    currency: str = "INR"
    currency_symbol: str = "₹"


DEFAULT_SETTINGS = {
    "company_name": "Arshith Connect",
    "company_email": "payroll@arshith.com",
    "company_phone": "+91 98765 43210",
    "company_address": "Tech Center, HITEC City, Hyderabad, India",
    "daily_rate_denominator": 30,
    "attendance_cutoff_day": 25,
    "pf_wage_ceiling": 15000.0,
    "esi_wage_ceiling": 21000.0,
    "overtime_multiplier": 1.5,
    "currency": "INR",
    "currency_symbol": "₹",
}


@router.get("", response_model=dict)
def get_company_settings(current_user: Any = Depends(get_current_user)):
    """Retrieve global company and payroll settings."""
    stored = FirestoreService.get_all("settings")
    if stored:
        return stored[0]
    return DEFAULT_SETTINGS


@router.put("")
def update_company_settings(payload: CompanySettingsUpdate, current_user: Any = Depends(get_current_admin)):
    """Update global company and payroll settings."""
    now_iso = datetime.now(timezone.utc).isoformat()
    stored = FirestoreService.get_all("settings")
    doc_data = {
        **payload.model_dump(),
        "updated_by": getattr(current_user, "email", "admin"),
        "updated_at": now_iso,
    }

    if stored:
        doc_id = stored[0].get("id") or stored[0].get("_firestore_id") or "1"
        FirestoreService.update("settings", str(doc_id), doc_data)
        doc_data["id"] = str(doc_id)
    else:
        doc_data["created_at"] = now_iso
        doc_data = FirestoreService.create("settings", doc_data)

    return {"message": "Settings updated successfully.", "data": doc_data}
