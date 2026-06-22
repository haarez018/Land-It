"""Application CRUD and Kanban data endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from backend.auth_deps import get_current_user_id
from backend.db import get_db

router = APIRouter()


class ApplicationResponse(BaseModel):
    id: str
    job_id: str
    status: str
    fit_score: float
    ats_score_before: Optional[float]
    ats_score_after: Optional[float]
    priority: int
    notes: str
    follow_up_due: Optional[str]


class UpdateStatusRequest(BaseModel):
    status: str


_VALID_STATUSES = {
    "queued", "tailoring", "ready", "submitted",
    "followed_up", "phone_screen", "interviewing",
    "offer", "rejected", "withdrawn",
}


def _row_to_response(row: dict) -> ApplicationResponse:
    return ApplicationResponse(
        id=row["id"],
        job_id=row["job_id"],
        status=row["status"],
        fit_score=row.get("fit_score") or 0.0,
        ats_score_before=row.get("ats_score_before"),
        ats_score_after=row.get("ats_score_after"),
        priority=row.get("priority") or 0,
        notes=row.get("notes") or "",
        follow_up_due=row.get("follow_up_due"),
    )


@router.get("/")
async def list_all_applications(user_id: str = Depends(get_current_user_id)):
    """List all applications in the pipeline."""
    db = get_db()
    resp = db.table("applications").select("*").eq("user_id", user_id).execute()
    return [_row_to_response(row) for row in resp.data]


@router.get("/{app_id}")
async def get_single_application(app_id: str, user_id: str = Depends(get_current_user_id)):
    """Get a single application."""
    db = get_db()
    resp = (
        db.table("applications")
        .select("*")
        .eq("id", app_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(404, "Application not found")
    return _row_to_response(resp.data[0])


@router.patch("/{app_id}")
async def update_application(
    app_id: str,
    request: UpdateStatusRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Update an application's status (for Kanban board drag)."""
    if request.status not in _VALID_STATUSES:
        raise HTTPException(400, f"Invalid status: {request.status}")

    db = get_db()
    resp = (
        db.table("applications")
        .update({"status": request.status})
        .eq("id", app_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(404, "Application not found")

    return {"status": "updated", "app_id": app_id, "new_status": request.status}


@router.get("/{app_id}/followup")
async def get_followup(app_id: str, user_id: str = Depends(get_current_user_id)):
    """Get follow-up status for an application."""
    db = get_db()
    resp = (
        db.table("applications")
        .select("id, status, follow_up_due")
        .eq("id", app_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(404, "Application not found")
    row = resp.data[0]
    return {
        "app_id": app_id,
        "follow_up_due": row.get("follow_up_due"),
        "status": row["status"],
    }
