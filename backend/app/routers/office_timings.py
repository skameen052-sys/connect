from datetime import date, datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.services.firestore_service import firestore_service
from app.dependencies.auth import get_current_user, get_current_admin

router = APIRouter(prefix="/office-timings", tags=["Office Timings"])


class SaveTimingRequest(BaseModel):
    timingType: str = "REGULAR"  # "REGULAR" or "SPECIAL"
    startTime: str = "09:30"
    endTime: str = "18:30"
    graceMinutes: int = 2
    specialDate: Optional[str] = None
    specialOccasion: Optional[str] = None


@router.get("")
def get_office_timings(
    current_user=Depends(get_current_user),
):
    """Retrieve regular and special scheduled office timings from Firestore."""
    all_timings = firestore_service.list_documents("office_timings")

    regular = None
    special_days = []

    for t in all_timings:
        t_id = str(t.get("id", ""))
        if t_id == "timings" or t.get("timing_type") == "REGULAR" or "officeStartTime" in t:
            regular = t
        elif t.get("timing_type") == "SPECIAL":
            special_days.append(t)

    special_days.sort(key=lambda s: str(s.get("special_date", "")))

    start_time = "09:00"
    end_time = "18:00"
    grace_minutes = 15
    if regular:
        start_time = regular.get("officeStartTime") or regular.get("startTime") or regular.get("start_time") or "09:00"
        end_time = regular.get("officeEndTime") or regular.get("endTime") or regular.get("end_time") or "18:00"
        try:
            grace_minutes = int(regular.get("gracePeriodMinutes") or regular.get("graceMinutes") or regular.get("grace_minutes") or 15)
        except Exception:
            grace_minutes = 15

    return {
        "regular": {
            "startTime": start_time,
            "endTime": end_time,
            "graceMinutes": grace_minutes,
            "officeStartTime": start_time,
            "officeEndTime": end_time,
            "gracePeriodMinutes": grace_minutes,
        },
        "specialDays": [
            {
                "id": s.get("id"),
                "startTime": s.get("start_time", "09:30"),
                "endTime": s.get("end_time", "18:30"),
                "graceMinutes": s.get("grace_minutes", 2),
                "specialDate": str(s.get("special_date", "")).split("T")[0] if s.get("special_date") else "",
                "specialOccasion": s.get("special_occasion", ""),
            }
            for s in special_days
        ],
    }


@router.post("", status_code=status.HTTP_200_OK)
def save_office_timing(
    payload: SaveTimingRequest,
    admin_user=Depends(get_current_admin),
):
    """Save regular office hours policy or schedule a special day (Admin only)."""
    now_iso = datetime.now(timezone.utc).isoformat()

    if payload.timingType == "REGULAR":
        # Save both to document 'timings' (matching Firestore schema) and regular record
        update_payload = {
            "id": "timings",
            "timing_type": "REGULAR",
            "officeStartTime": payload.startTime,
            "officeEndTime": payload.endTime,
            "gracePeriodMinutes": payload.graceMinutes,
            "start_time": payload.startTime,
            "end_time": payload.endTime,
            "grace_minutes": payload.graceMinutes,
            "updated_at": now_iso,
        }
        firestore_service.create_document("office_timings", update_payload)

        # Also write to settings/officeTimings for Android mobile app
        try:
            from app.services.firestore_service import FirestoreService
            FirestoreService.save("settings", "officeTimings", {
                "id": "officeTimings",
                "officeStartTime": payload.startTime,
                "officeEndTime": payload.endTime,
                "gracePeriodMinutes": payload.graceMinutes,
                "startTime": payload.startTime,
                "endTime": payload.endTime,
                "graceMinutes": payload.graceMinutes,
                "updated_at": now_iso,
            })
        except Exception:
            pass

        # Record audit log
        firestore_service.create_document("audit_logs", {
            "actor_id": admin_user.id,
            "actor_email": admin_user.email,
            "action": "UPDATE_REGULAR_OFFICE_TIMING",
            "target_type": "office_timings",
            "target_id": "REGULAR",
            "timestamp": now_iso,
        })

        return {"success": True, "message": "Regular office timings updated successfully"}
    else:
        if not payload.specialDate:
            raise HTTPException(status_code=400, detail="Special date is required for custom timing")
        try:
            s_date = date.fromisoformat(payload.specialDate)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format for special timing (YYYY-MM-DD)")

        special_data = {
            "timing_type": "SPECIAL",
            "start_time": payload.startTime,
            "end_time": payload.endTime,
            "grace_minutes": payload.graceMinutes,
            "special_date": s_date.isoformat(),
            "special_occasion": payload.specialOccasion or "Special Schedule",
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        doc_id = firestore_service.create_document("office_timings", special_data)

        # Record audit log
        firestore_service.create_document("audit_logs", {
            "actor_id": admin_user.id,
            "actor_email": admin_user.email,
            "action": "CREATE_SPECIAL_OFFICE_TIMING",
            "target_type": "office_timings",
            "target_id": doc_id,
            "timestamp": now_iso,
        })

        return {"success": True, "message": "Special office timing added successfully"}


@router.delete("/{timing_id}", status_code=status.HTTP_200_OK)
def delete_special_timing(
    timing_id: str,
    admin_user=Depends(get_current_admin),
):
    """Delete special day schedule (Admin only)."""
    timing = firestore_service.get_document("office_timings", str(timing_id))
    if not timing:
        # Search by id string comparison
        all_timings = firestore_service.list_documents("office_timings")
        for t in all_timings:
            if str(t.get("id")) == str(timing_id) and t.get("timing_type") == "SPECIAL":
                timing = t
                break

    if not timing or timing.get("timing_type") != "SPECIAL":
        raise HTTPException(status_code=404, detail="Special timing not found")

    firestore_service.delete_document("office_timings", str(timing["id"]))

    # Record audit log
    firestore_service.create_document("audit_logs", {
        "actor_id": admin_user.id,
        "actor_email": admin_user.email,
        "action": "DELETE_SPECIAL_OFFICE_TIMING",
        "target_type": "office_timings",
        "target_id": str(timing["id"]),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {"success": True, "message": "Special timing removed"}
