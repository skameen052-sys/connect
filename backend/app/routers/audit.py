"""
Audit Trail API Router
Provides queryable audit logs recording security-sensitive modifications,
salary revisions, attendance changes, and approval workflows.
"""

from typing import List, Optional, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, status

from app.core.config import settings
from app.dependencies.auth import get_current_admin
from app.services.firestore_service import FirestoreService

router = APIRouter(prefix="/audit", tags=["Audit Trail"])


@router.get("/logs", response_model=List[dict])
def list_audit_logs(
    entity_type: Optional[str] = None,
    user_email: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    current_user: Any = Depends(get_current_admin),
):
    """List system audit logs (Admin only)."""
    logs = FirestoreService.get_all("audit_logs")

    if entity_type:
        logs = [l for l in logs if str(l.get("entity_type") or l.get("table_name", "")).lower() == entity_type.lower()]

    if user_email:
        logs = [l for l in logs if str(l.get("user_email") or l.get("actor_email", "")).lower() == user_email.lower()]

    sorted_logs = sorted(logs, key=lambda x: str(x.get("created_at") or x.get("timestamp", "")), reverse=True)
    return sorted_logs[:limit]
