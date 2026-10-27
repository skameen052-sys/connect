"""
Performance Management API Router
Manages employee goals/OKRs, appraisal review cycles, 1-5 ratings,
manager evaluations, and salary increment recommendations.
"""

from typing import List, Optional, Any
from datetime import datetime, timezone, date
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.dependencies.auth import get_current_user, get_current_admin
from app.services.firestore_service import FirestoreService

router = APIRouter(prefix="/performance", tags=["Performance & Appraisals"])


class GoalCreate(BaseModel):
    employee_id: str
    title: str = Field(..., min_length=3)
    description: str
    target_date: str
    weightage: float = Field(default=20.0, ge=1, le=100)


class GoalProgressUpdate(BaseModel):
    progress: float = Field(..., ge=0, le=100)
    status: Optional[str] = "IN_PROGRESS"


class ReviewCreate(BaseModel):
    employee_id: str
    review_period: str = "Annual 2026"
    rating: float = Field(..., ge=1.0, le=5.0)
    strengths: str
    areas_for_improvement: str
    manager_feedback: str
    recommended_increment_pct: Optional[float] = Field(default=0.0, ge=0)
    employee_name: Optional[str] = None
    employee_email: Optional[str] = None
    department: Optional[str] = None


@router.get("/goals", response_model=List[dict])
def list_goals(employee_id: Optional[str] = None, current_user: Any = Depends(get_current_user)):
    """List performance goals. Employees view own; Admins view all."""
    role = str(getattr(current_user, "role", "employee")).lower()
    caller_emp_id = str(getattr(current_user, "employee_id", "") or getattr(current_user, "employeeId", "") or getattr(current_user, "id", "") or "").strip()
    caller_email = str(getattr(current_user, "email", "") or "").strip().lower()

    all_goals = FirestoreService.get_all("performance_goals")

    if role == "employee" or employee_id:
        candidate_ids = set()
        if employee_id: candidate_ids.add(str(employee_id).strip().lower())
        if caller_emp_id: candidate_ids.add(caller_emp_id.lower())
        if caller_email: candidate_ids.add(caller_email)

        matched_goals = []
        for g in all_goals:
            g_eid = str(g.get("employee_id") or g.get("employeeId") or "").strip().lower()
            if g_eid and g_eid in candidate_ids:
                matched_goals.append(g)
        all_goals = matched_goals

    return sorted(all_goals, key=lambda x: str(x.get("created_at", "")), reverse=True)


@router.post("/goals", status_code=status.HTTP_201_CREATED)
def create_goal(payload: GoalCreate, current_user: Any = Depends(get_current_user)):
    """Create a new goal or OKR."""
    now_iso = datetime.now(timezone.utc).isoformat()
    doc = {
        **payload.model_dump(),
        "progress": 0.0,
        "status": "NOT_STARTED",
        "created_by": getattr(current_user, "email", "admin"),
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    created = FirestoreService.create("performance_goals", doc)
    return {"message": "Goal created successfully.", "data": created}


@router.patch("/goals/{goal_id}/progress")
def update_goal_progress(goal_id: str, payload: GoalProgressUpdate, current_user: Any = Depends(get_current_user)):
    """Update goal completion percentage."""
    goal = FirestoreService.get_by_id("performance_goals", str(goal_id))
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found.")

    now_iso = datetime.now(timezone.utc).isoformat()
    status_val = "COMPLETED" if payload.progress >= 100.0 else (payload.status or "IN_PROGRESS")
    update_data = {
        "progress": payload.progress,
        "status": status_val,
        "updated_at": now_iso,
    }
    FirestoreService.update("performance_goals", str(goal_id), update_data)
    goal.update(update_data)
    return {"message": "Goal progress updated.", "data": goal}


@router.get("/reviews", response_model=List[dict])
def list_reviews(employee_id: Optional[str] = None, current_user: Any = Depends(get_current_user)):
    """List appraisal review cycles. Filtered for employees to only see their own appraisals."""
    role = str(getattr(current_user, "role", "employee")).lower()
    caller_emp_id = str(getattr(current_user, "employee_id", "") or getattr(current_user, "employeeId", "") or getattr(current_user, "id", "") or "").strip()
    caller_email = str(getattr(current_user, "email", "") or "").strip().lower()

    all_reviews = FirestoreService.get_all("performance_reviews")
    employees = FirestoreService.get_all("employees")

    # If the user is an employee OR an explicit employee_id filter is requested
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

        matched_reviews = []
        for r in all_reviews:
            r_eid = str(r.get("employee_id") or "").strip().lower()
            r_eid2 = str(r.get("employeeId") or "").strip().lower()
            r_email = str(r.get("employee_email") or r.get("email") or "").strip().lower()
            r_doc_id = str(r.get("employee_doc_id") or "").strip().lower()

            if (r_eid and r_eid in candidate_ids) or \
               (r_eid2 and r_eid2 in candidate_ids) or \
               (r_email and r_email in candidate_ids) or \
               (r_doc_id and r_doc_id in candidate_ids):
                matched_reviews.append(r)

        all_reviews = matched_reviews

    # Enrich metadata for employee_name and department
    emp_map = {}
    for e in employees:
        if e.get("id"): emp_map[str(e["id"]).lower()] = e
        if e.get("employeeId"): emp_map[str(e["employeeId"]).lower()] = e
        if e.get("employee_id"): emp_map[str(e["employee_id"]).lower()] = e
        if e.get("email"): emp_map[str(e["email"]).lower()] = e

    for r in all_reviews:
        eid = str(r.get("employee_id") or r.get("employeeId") or "").lower()
        e_email = str(r.get("employee_email") or "").lower()
        emp = emp_map.get(eid) or emp_map.get(e_email) or {}
        r["employee_name"] = r.get("employee_name") or emp.get("name") or emp.get("full_name") or emp.get("fullName") or "Employee"
        r["department"] = r.get("department") or emp.get("department") or emp.get("dept") or "Engineering"

    return sorted(all_reviews, key=lambda x: str(x.get("created_at", "")), reverse=True)


@router.post("/reviews", status_code=status.HTTP_201_CREATED)
def submit_performance_review(payload: ReviewCreate, current_user: Any = Depends(get_current_admin)):
    """Submit performance review appraisal rating and increment recommendation."""
    raw_target_id = str(payload.employee_id).strip()
    clean_target_id = raw_target_id.lower()
    payload_email = str(payload.employee_email or "").strip().lower()

    # Look up employee to resolve standard identifiers
    employees = FirestoreService.get_all("employees")
    matched_emp = next((
        e for e in employees
        if str(e.get("employeeId") or "").strip().lower() == clean_target_id
        or str(e.get("employee_id") or "").strip().lower() == clean_target_id
        or str(e.get("id") or "").strip().lower() == clean_target_id
        or str(e.get("uid") or "").strip().lower() == clean_target_id
        or (payload_email and str(e.get("email") or "").strip().lower() == payload_email)
        or (clean_target_id and str(e.get("email") or "").strip().lower() == clean_target_id)
    ), None)

    canonical_eid = raw_target_id
    canonical_name = payload.employee_name or ""
    canonical_email = payload.employee_email or ""
    canonical_dept = payload.department or ""
    emp_doc_id = ""

    if matched_emp:
        canonical_eid = matched_emp.get("employeeId") or matched_emp.get("employee_id") or matched_emp.get("id") or raw_target_id
        canonical_name = canonical_name or matched_emp.get("name") or matched_emp.get("fullName") or matched_emp.get("full_name") or "Employee"
        canonical_email = canonical_email or matched_emp.get("email") or ""
        canonical_dept = canonical_dept or matched_emp.get("department") or matched_emp.get("dept") or "Engineering"
        emp_doc_id = str(matched_emp.get("id") or "")

    now_iso = datetime.now(timezone.utc).isoformat()
    doc = {
        **payload.model_dump(),
        "employee_id": canonical_eid,
        "employeeId": canonical_eid,
        "employee_name": canonical_name or "Employee",
        "employee_email": canonical_email,
        "department": canonical_dept or "Engineering",
        "employee_doc_id": emp_doc_id,
        "evaluated_by": getattr(current_user, "email", "admin"),
        "evaluated_at": now_iso,
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    created = FirestoreService.create("performance_reviews", doc)
    return {"message": "Performance appraisal submitted successfully.", "data": created}

