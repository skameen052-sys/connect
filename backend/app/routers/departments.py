"""
Departments & Designations API Router
Manages organizational structure, departments, job titles, and hierarchies.
"""

from typing import List, Optional, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.dependencies.auth import get_current_user, get_current_admin
from app.services.firestore_service import FirestoreService

router = APIRouter(tags=["Departments & Designations"])


class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=2)
    code: Optional[str] = None
    description: Optional[str] = None
    head_of_department: Optional[str] = None


class DesignationCreate(BaseModel):
    title: str = Field(..., min_length=2)
    department: str
    level: Optional[str] = "Mid"
    description: Optional[str] = None


DEFAULT_DEPARTMENTS = [
    {"name": "Human Resources", "code": "HR", "description": "Talent Acquisition, People Operations & Compliance", "order": 1},
    {"name": "Web Developer", "code": "WEB", "description": "Web Application Architecture, Development & QA", "order": 2},
    {"name": "Python Developer", "code": "PY", "description": "Python Backend Services, APIs & Automation", "order": 3},
    {"name": "Finance & Payroll", "code": "FIN", "description": "Accounting, Payroll Disbursement & Taxation", "order": 4},
]

DEFAULT_DESIGNATIONS = [
    {"title": "HR Manager", "department": "Human Resources", "level": "Lead"},
    {"title": "Senior Web Developer", "department": "Web Developer", "level": "Senior"},
    {"title": "Full-Stack Web Developer", "department": "Web Developer", "level": "Mid"},
    {"title": "Frontend Developer", "department": "Web Developer", "level": "Mid"},
    {"title": "Python Developer", "department": "Python Developer", "level": "Mid"},
    {"title": "Senior Python Backend Engineer", "department": "Python Developer", "level": "Senior"},
    {"title": "Payroll Specialist", "department": "Finance & Payroll", "level": "Mid"},
]

ORDER_MAP = {
    "human resources": 1,
    "web developer": 2,
    "python developer": 3,
    "finance & payroll": 4,
}


@router.get("/departments", response_model=List[dict])
def list_departments(current_user: Any = Depends(get_current_user)):
    """List company departments in strict order: Human Resources, Web Developer, Python Developer, Finance & Payroll."""
    depts = FirestoreService.get_all("departments")
    if not depts:
        now_iso = datetime.now(timezone.utc).isoformat()
        for d in DEFAULT_DEPARTMENTS:
            doc = {**d, "created_at": now_iso}
            FirestoreService.create("departments", doc)
        depts = FirestoreService.get_all("departments")

    # Filter strictly to the 4 requested departments
    filtered_depts = [d for d in depts if d.get("name", "").strip().lower() in ORDER_MAP]

    # Count employees per department with alias normalization
    employees = FirestoreService.get_all("employees")
    dept_counts = {}
    for e in employees:
        raw_dept = str(e.get("department") or e.get("dept") or "General").strip()
        if raw_dept.lower() == "engineering":
            dept_name = "Web Developer"
        elif raw_dept.lower() in ["product & design", "product and design"]:
            dept_name = "Python Developer"
        else:
            dept_name = raw_dept
        dept_counts[dept_name] = dept_counts.get(dept_name, 0) + 1

    for d in filtered_depts:
        d_name = d.get("name", "")
        d["employee_count"] = dept_counts.get(d_name, 0)

    # Sort strictly by the requested order:
    # 1. Human Resources, 2. Web Developer, 3. Python Developer, 4. Finance & Payroll
    filtered_depts.sort(key=lambda d: ORDER_MAP.get(d.get("name", "").strip().lower(), 99))

    return filtered_depts


@router.post("/departments", status_code=status.HTTP_201_CREATED)
def create_department(payload: DepartmentCreate, current_user: Any = Depends(get_current_admin)):
    """Create a new department."""
    now_iso = datetime.now(timezone.utc).isoformat()
    doc = {
        **payload.model_dump(),
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    created = FirestoreService.create("departments", doc)
    return {"message": "Department created successfully.", "data": created}


@router.get("/designations", response_model=List[dict])
def list_designations(department: Optional[str] = None, current_user: Any = Depends(get_current_user)):
    """List designations for active departments ordered consistently."""
    desigs = FirestoreService.get_all("designations")
    if not desigs:
        now_iso = datetime.now(timezone.utc).isoformat()
        for d in DEFAULT_DESIGNATIONS:
            doc = {**d, "created_at": now_iso}
            FirestoreService.create("designations", doc)
        desigs = FirestoreService.get_all("designations")

    # Filter to designations under the active departments
    valid_desigs = [d for d in desigs if str(d.get("department", "")).strip().lower() in ORDER_MAP]

    if department:
        valid_desigs = [d for d in valid_desigs if str(d.get("department")).lower() == department.lower()]

    valid_desigs.sort(key=lambda d: (ORDER_MAP.get(str(d.get("department", "")).strip().lower(), 99), str(d.get("title"))))
    return valid_desigs


@router.post("/designations", status_code=status.HTTP_201_CREATED)
def create_designation(payload: DesignationCreate, current_user: Any = Depends(get_current_admin)):
    """Create a new job designation."""
    now_iso = datetime.now(timezone.utc).isoformat()
    doc = {
        **payload.model_dump(),
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    created = FirestoreService.create("designations", doc)
    return {"message": "Designation created successfully.", "data": created}
