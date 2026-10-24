"""
Recruitment & Onboarding API Router
Manages job openings, candidate pipeline tracking, offer letters,
and automated conversion of hired candidates to employee records.
"""

from typing import List, Optional, Any
from datetime import datetime, timezone, date
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.dependencies.auth import get_current_user, get_current_admin
from app.services.firestore_service import FirestoreService

router = APIRouter(prefix="/recruitment", tags=["Recruitment & Onboarding"])


class JobOpeningCreate(BaseModel):
    title: str = Field(..., min_length=3)
    department: str
    location: str = "HQ Office"
    employment_type: str = "Full-time"
    vacancies: int = Field(default=1, ge=1)
    description: str
    requirements: Optional[str] = None


class CandidateCreate(BaseModel):
    job_id: str
    full_name: str = Field(..., min_length=2)
    email: str
    phone: str
    experience_years: float = Field(default=0.0, ge=0)
    current_ctc: Optional[float] = 0.0
    expected_ctc: Optional[float] = 0.0
    notice_period_days: Optional[int] = 30
    resume_url: Optional[str] = None
    notes: Optional[str] = None


class StageUpdateRequest(BaseModel):
    stage: str = Field(..., pattern="^(Applied|Screening|Interview|Offered|Hired|Rejected)$")
    notes: Optional[str] = None


class CandidateConvertRequest(BaseModel):
    employee_id: str
    designation: str
    department: str
    joining_date: str
    basic_salary: float = Field(default=25000.0, gt=0)
    hra: float = Field(default=10000.0, ge=0)
    other_allowances: float = Field(default=5000.0, ge=0)


@router.get("/jobs", response_model=List[dict])
def list_jobs(current_user: Any = Depends(get_current_user)):
    """List open job requisitions."""
    jobs = FirestoreService.get_all("recruitment_jobs")
    return sorted(jobs, key=lambda x: str(x.get("created_at", "")), reverse=True)


@router.post("/jobs", status_code=status.HTTP_201_CREATED)
def create_job(payload: JobOpeningCreate, current_user: Any = Depends(get_current_admin)):
    """Create a new job posting."""
    now_iso = datetime.now(timezone.utc).isoformat()
    doc = {
        **payload.model_dump(),
        "status": "OPEN",
        "created_by": getattr(current_user, "email", "admin"),
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    created = FirestoreService.create("recruitment_jobs", doc)
    return {"message": "Job opening created successfully.", "data": created}


@router.get("/candidates", response_model=List[dict])
def list_candidates(job_id: Optional[str] = None, current_user: Any = Depends(get_current_admin)):
    """List candidates in the recruitment pipeline."""
    candidates = FirestoreService.get_all("candidates")
    if job_id:
        candidates = [c for c in candidates if str(c.get("job_id")) == str(job_id)]
    return sorted(candidates, key=lambda x: str(x.get("created_at", "")), reverse=True)


@router.post("/candidates", status_code=status.HTTP_201_CREATED)
def register_candidate(payload: CandidateCreate, current_user: Any = Depends(get_current_admin)):
    """Add a candidate application to the pipeline."""
    now_iso = datetime.now(timezone.utc).isoformat()
    doc = {
        **payload.model_dump(),
        "stage": "Applied",
        "applied_date": str(date.today()),
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    created = FirestoreService.create("candidates", doc)
    return {"message": "Candidate added to pipeline.", "data": created}


@router.patch("/candidates/{candidate_id}/stage")
def update_candidate_stage(candidate_id: str, payload: StageUpdateRequest, current_user: Any = Depends(get_current_admin)):
    """Update candidate pipeline stage."""
    candidate = FirestoreService.get_by_id("candidates", str(candidate_id))
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate record not found.")

    now_iso = datetime.now(timezone.utc).isoformat()
    update_data = {
        "stage": payload.stage,
        "stage_notes": payload.notes,
        "stage_updated_at": now_iso,
        "updated_at": now_iso,
    }
    FirestoreService.update("candidates", str(candidate_id), update_data)
    candidate.update(update_data)
    return {"message": f"Candidate moved to stage '{payload.stage}'.", "data": candidate}


@router.post("/candidates/{candidate_id}/convert-to-employee")
def convert_candidate_to_employee(candidate_id: str, payload: CandidateConvertRequest, current_user: Any = Depends(get_current_admin)):
    """
    Converts a HIRED candidate into a full active Employee record with an active salary structure.
    Prevents duplicate creation.
    """
    candidate = FirestoreService.get_by_id("candidates", str(candidate_id))
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    if candidate.get("converted_to_employee"):
        raise HTTPException(status_code=400, detail="Candidate has already been converted to an employee.")

    now_iso = datetime.now(timezone.utc).isoformat()
    emp_email = str(candidate.get("email")).lower().strip()

    # Create employee document
    new_employee = {
        "employee_id": payload.employee_id,
        "name": candidate.get("full_name"),
        "full_name": candidate.get("full_name"),
        "email": emp_email,
        "phone": candidate.get("phone", "--"),
        "department": payload.department,
        "designation": payload.designation,
        "joining_date": payload.joining_date,
        "employment_type": "Full-time",
        "status": "Active",
        "location": "HQ Office",
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    created_emp = FirestoreService.create("employees", new_employee, doc_id=payload.employee_id)

    # Create matching salary structure
    gross = payload.basic_salary + payload.hra + payload.other_allowances
    new_struct = {
        "employee_id": payload.employee_id,
        "basic_salary": payload.basic_salary,
        "hra": payload.hra,
        "other_allowances": payload.other_allowances,
        "gross_salary": gross,
        "pf_applicable": True,
        "pf_wage_base": 15000.0,
        "esi_applicable": gross <= 21000.0,
        "professional_tax": 200.0,
        "tds_monthly": 0.0,
        "effective_date": payload.joining_date,
        "is_active": True,
        "created_at": now_iso,
    }
    FirestoreService.create("salary_structures", new_struct)

    # Mark candidate as converted
    FirestoreService.update("candidates", str(candidate_id), {
        "converted_to_employee": True,
        "employee_id": payload.employee_id,
        "stage": "Hired",
        "updated_at": now_iso,
    })

    return {
        "message": f"Candidate successfully converted to Employee {payload.employee_id}.",
        "employee": created_emp,
    }
