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
    {"name": "Engineering", "code": "ENG", "description": "Software Architecture, Development & QA"},
    {"name": "Human Resources", "code": "HR", "description": "Talent Acquisition, People Operations & Compliance"},
    {"name": "Finance & Payroll", "code": "FIN", "description": "Accounting, Payroll Disbursement & Taxation"},
    {"name": "Product & Design", "code": "PROD", "description": "Product Strategy & UI/UX Design"},
    {"name": "Marketing & Sales", "code": "MKT", "description": "Growth, Business Development & Client Relations"},
    {"name": "Operations", "code": "OPS", "description": "Workforce Logistics & Facilities"},
]

DEFAULT_DESIGNATIONS = [
    {"title": "Senior Software Engineer", "department": "Engineering", "level": "Senior"},
    {"title": "Full-Stack Developer", "department": "Engineering", "level": "Mid"},
    {"title": "QA Test Engineer", "department": "Engineering", "level": "Mid"},
    {"title": "HR Manager", "department": "Human Resources", "level": "Lead"},
    {"title": "Payroll Specialist", "department": "Finance & Payroll", "level": "Mid"},
    {"title": "Product Designer (UI/UX)", "department": "Product & Design", "level": "Mid"},
    {"title": "Operations Coordinator", "department": "Operations", "level": "Junior"},
]


@router.get("/departments", response_model=List[dict])
def list_departments(current_user: Any = Depends(get_current_user)):
    """List all company departments with employee counts."""
    depts = FirestoreService.get_all("departments")
    if not depts:
        # Seed defaults
        now_iso = datetime.now(timezone.utc).isoformat()
        for d in DEFAULT_DEPARTMENTS:
            doc = {**d, "created_at": now_iso}
            FirestoreService.create("departments", doc)
        depts = FirestoreService.get_all("departments")

    # Count employees per department
    employees = FirestoreService.get_all("employees")
    dept_counts = {}
    for e in employees:
        dept_name = e.get("department") or e.get("dept") or "General"
        dept_counts[dept_name] = dept_counts.get(dept_name, 0) + 1

    for d in depts:
        d["employee_count"] = dept_counts.get(d.get("name"), 0)

    return depts


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
    """List all designations and job titles."""
    desigs = FirestoreService.get_all("designations")
    if not desigs:
        now_iso = datetime.now(timezone.utc).isoformat()
        for d in DEFAULT_DESIGNATIONS:
            doc = {**d, "created_at": now_iso}
            FirestoreService.create("designations", doc)
        desigs = FirestoreService.get_all("designations")

    if department:
        desigs = [d for d in desigs if str(d.get("department")).lower() == department.lower()]

    return desigs


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
