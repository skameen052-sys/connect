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


@router.get("/goals", response_model=List[dict])
def list_goals(employee_id: Optional[str] = None, current_user: Any = Depends(get_current_user)):
    """List performance goals. Employees view own; Admins view all."""
    role = str(getattr(current_user, "role", "employee")).lower()
    caller_emp_id = str(getattr(current_user, "employee_id", "") or getattr(current_user, "employeeId", ""))

    all_goals = FirestoreService.get_all("performance_goals")
    target_id = employee_id if (role != "employee" and employee_id) else (caller_emp_id if role == "employee" else employee_id)

    if target_id:
        all_goals = [g for g in all_goals if str(g.get("employee_id") or g.get("employeeId")) == str(target_id)]

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
    """List appraisal review cycles."""
    role = str(getattr(current_user, "role", "employee")).lower()
    caller_emp_id = str(getattr(current_user, "employee_id", "") or getattr(current_user, "employeeId", ""))

    all_reviews = FirestoreService.get_all("performance_reviews")
    target_id = employee_id if (role != "employee" and employee_id) else (caller_emp_id if role == "employee" else employee_id)

    if target_id:
        all_reviews = [r for r in all_reviews if str(r.get("employee_id")) == str(target_id)]

    employees = FirestoreService.get_all("employees")
    emp_map = {
        str(e.get("employee_id") or e.get("employeeId") or e.get("id")): e
        for e in employees
    }
    for r in all_reviews:
        eid = str(r.get("employee_id"))
        emp = emp_map.get(eid, {})
        r["employee_name"] = emp.get("name") or emp.get("full_name") or "Employee"
        r["department"] = emp.get("department") or emp.get("dept") or "Engineering"

    return sorted(all_reviews, key=lambda x: str(x.get("created_at", "")), reverse=True)


@router.post("/reviews", status_code=status.HTTP_201_CREATED)
def submit_performance_review(payload: ReviewCreate, current_user: Any = Depends(get_current_admin)):
    """Submit performance review appraisal rating and increment recommendation."""
    now_iso = datetime.now(timezone.utc).isoformat()
    doc = {
        **payload.model_dump(),
        "evaluated_by": getattr(current_user, "email", "admin"),
        "evaluated_at": now_iso,
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    created = FirestoreService.create("performance_reviews", doc)
    return {"message": "Performance appraisal submitted.", "data": created}
