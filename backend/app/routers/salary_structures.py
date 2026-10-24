"""
Salary Structures API Router
Manages employee salary structures (Basic, HRA, Allowances, PF, ESI, PT, TDS),
salary revision history, and component lookups.
"""

from typing import List, Optional, Any
from datetime import datetime, timezone, date
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.dependencies.auth import get_current_user, get_current_admin
from app.services.firestore_service import FirestoreService
from app.services.payroll_engine import round_curr

router = APIRouter(prefix="/salary-structures", tags=["Salary Structures"])


class SalaryStructureCreate(BaseModel):
    employee_id: str
    basic_salary: float = Field(..., gt=0)
    hra: float = Field(default=0.0, ge=0)
    other_allowances: float = Field(default=0.0, ge=0)
    special_allowance: float = Field(default=0.0, ge=0)
    pf_applicable: bool = True
    pf_wage_base: Optional[float] = 15000.0
    esi_applicable: bool = False
    professional_tax: float = 200.0
    tds_monthly: float = 0.0
    effective_date: Optional[str] = None
    reason: Optional[str] = "Initial Structure / Revision"


@router.get("", response_model=List[dict])
def list_salary_structures(current_user: Any = Depends(get_current_admin)):
    """List all configured employee salary structures (Admins / HR / Payroll only)."""
    structures = FirestoreService.get_all("salary_structures")
    employees = FirestoreService.get_all("employees")
    emp_map = {
        str(e.get("employee_id") or e.get("employeeId") or e.get("id")): e
        for e in employees
    }

    result = []
    for s in structures:
        eid = str(s.get("employee_id") or s.get("employeeId") or "")
        emp = emp_map.get(eid, {})
        emp_name = emp.get("name") or emp.get("full_name") or emp.get("fullName") or "Employee"
        dept = emp.get("department") or emp.get("dept") or "Operations"
        desig = emp.get("designation") or emp.get("role") or "Staff"

        basic = float(s.get("basic_salary", 0.0))
        hra = float(s.get("hra", 0.0))
        allow = float(s.get("other_allowances", 0.0) or s.get("special_allowance", 0.0))
        gross = round_curr(basic + hra + allow)

        result.append({
            "id": s.get("id") or s.get("_firestore_id"),
            "employee_id": eid,
            "employee_name": emp_name,
            "department": dept,
            "designation": desig,
            "basic_salary": basic,
            "hra": hra,
            "other_allowances": allow,
            "gross_salary": gross,
            "pf_applicable": s.get("pf_applicable", True),
            "pf_wage_base": s.get("pf_wage_base", 15000.0),
            "esi_applicable": s.get("esi_applicable", False),
            "professional_tax": s.get("professional_tax", 200.0),
            "tds_monthly": s.get("tds_monthly", 0.0),
            "effective_date": s.get("effective_date", str(date.today())),
            "is_active": s.get("is_active", True),
        })

    return result


@router.get("/{employee_id}")
def get_employee_salary_structure(employee_id: str, current_user: Any = Depends(get_current_user)):
    """
    Get salary structure for a specific employee.
    Employees may only view their own structure. Admins can view any.
    """
    caller_role = str(getattr(current_user, "role", "employee")).lower()
    caller_emp_id = str(getattr(current_user, "employee_id", "") or getattr(current_user, "employeeId", ""))

    if caller_role == "employee" and caller_emp_id != str(employee_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employees are restricted to viewing their own salary structure.",
        )

    structures = FirestoreService.get_all("salary_structures")
    matching = [
        s for s in structures
        if str(s.get("employee_id") or s.get("employeeId")) == str(employee_id) and s.get("is_active", True)
    ]

    if not matching:
        # Default synthesized structure if not yet explicitly saved
        return {
            "employee_id": employee_id,
            "basic_salary": 20000.0,
            "hra": 8000.0,
            "other_allowances": 4000.0,
            "gross_salary": 32000.0,
            "pf_applicable": True,
            "pf_wage_base": 18000.0,
            "esi_applicable": False,
            "professional_tax": 200.0,
            "tds_monthly": 0.0,
            "is_active": True,
            "is_default": True,
        }

    return matching[0]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_or_update_salary_structure(payload: SalaryStructureCreate, current_user: Any = Depends(get_current_admin)):
    """Create or revise an employee's salary structure."""
    gross = round_curr(payload.basic_salary + payload.hra + payload.other_allowances + payload.special_allowance)
    now_iso = datetime.now(timezone.utc).isoformat()
    eff_date = payload.effective_date or str(date.today())

    # Deactivate existing active structures for this employee and record in history
    structures = FirestoreService.get_all("salary_structures")
    existing_id = None
    for s in structures:
        if str(s.get("employee_id") or s.get("employeeId")) == str(payload.employee_id) and s.get("is_active", True):
            existing_id = s.get("id") or s.get("_firestore_id")
            # Log revision record
            rev_record = {
                "employee_id": payload.employee_id,
                "previous_gross": s.get("gross_salary"),
                "new_gross": gross,
                "reason": payload.reason,
                "revised_by": getattr(current_user, "email", "admin"),
                "revised_at": now_iso,
            }
            FirestoreService.create("salary_revisions", rev_record)
            FirestoreService.update("salary_structures", str(existing_id), {"is_active": False, "updated_at": now_iso})

    new_doc = {
        "employee_id": payload.employee_id,
        "basic_salary": payload.basic_salary,
        "hra": payload.hra,
        "other_allowances": payload.other_allowances,
        "special_allowance": payload.special_allowance,
        "gross_salary": gross,
        "pf_applicable": payload.pf_applicable,
        "pf_wage_base": payload.pf_wage_base or 15000.0,
        "esi_applicable": payload.esi_applicable,
        "professional_tax": payload.professional_tax,
        "tds_monthly": payload.tds_monthly,
        "effective_date": eff_date,
        "is_active": True,
        "created_by": getattr(current_user, "email", "admin"),
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    created = FirestoreService.create("salary_structures", new_doc)
    return {"message": "Salary structure configured successfully", "data": created}


@router.get("/{employee_id}/history")
def get_salary_revision_history(employee_id: str, current_user: Any = Depends(get_current_admin)):
    """Retrieve salary revision audit history for an employee."""
    all_revs = FirestoreService.get_all("salary_revisions")
    emp_revs = [r for r in all_revs if str(r.get("employee_id")) == str(employee_id)]
    return sorted(emp_revs, key=lambda x: str(x.get("revised_at", "")), reverse=True)
