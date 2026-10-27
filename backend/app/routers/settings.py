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
    daily_rate_denominator: int = Field(default=26, ge=20, le=31)
    sundays_per_month: int = Field(default=4, ge=0, le=6)
    festival_holidays_paid: bool = Field(default=True)
    attendance_cutoff_day: int = Field(default=25, ge=1, le=31)
    pf_wage_ceiling: float = Field(default=15000.0, ge=0)
    esi_wage_ceiling: float = Field(default=21000.0, ge=0)
    pf_rate: float = Field(default=0.12, ge=0.0, le=0.5)
    overtime_multiplier: float = Field(default=1.5, ge=1.0)
    currency: str = "INR"
    currency_symbol: str = "₹"


DEFAULT_SETTINGS = {
    "id": "company_settings",
    "company_name": "Arshith Connect",
    "company_email": "payroll@arshith.com",
    "company_phone": "+91 98765 43210",
    "company_address": "Tech Center, HITEC City, Hyderabad, India",
    "daily_rate_denominator": 26,
    "sundays_per_month": 4,
    "festival_holidays_paid": True,
    "attendance_cutoff_day": 25,
    "pf_wage_ceiling": 15000.0,
    "esi_wage_ceiling": 21000.0,
    "pf_rate": 0.12,
    "overtime_multiplier": 1.5,
    "currency": "INR",
    "currency_symbol": "₹",
}


@router.get("", response_model=dict)
def get_company_settings(current_user: Any = Depends(get_current_user)):
    """Retrieve global company and payroll settings."""
    stored = FirestoreService.get_by_id("settings", "company_settings")
    if stored and "company_name" in stored:
        merged = {**DEFAULT_SETTINGS, **stored}
        return merged

    all_settings = FirestoreService.get_all("settings")
    for s in all_settings:
        s_id = str(s.get("id") or s.get("_firestore_id") or "")
        if s_id != "officeTimings" and ("company_name" in s or "daily_rate_denominator" in s):
            merged = {**DEFAULT_SETTINGS, **s}
            return merged

    # First time initialization
    FirestoreService.save("settings", "company_settings", DEFAULT_SETTINGS)
    return DEFAULT_SETTINGS


@router.put("")
def update_company_settings(payload: CompanySettingsUpdate, current_user: Any = Depends(get_current_admin)):
    """Update global company and payroll settings."""
    now_iso = datetime.now(timezone.utc).isoformat()
    doc_data = {
        **DEFAULT_SETTINGS,
        **payload.model_dump(),
        "id": "company_settings",
        "updated_by": getattr(current_user, "email", "admin"),
        "updated_at": now_iso,
    }

    saved = FirestoreService.save("settings", "company_settings", doc_data)
    return {"message": "Company & Payroll settings updated successfully.", "data": saved or doc_data}

