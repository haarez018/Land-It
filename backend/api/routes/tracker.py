"""Tracker agent API: follow-ups, timelines, email classification, status transitions."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from backend.agents.tracker.agent import (
    TrackerAgent,
    get_timeline,
    VALID_TRANSITIONS,
)
from backend.auth_deps import get_current_user_id
from backend.db import get_db

router = APIRouter()

_agent = TrackerAgent()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_app_row(app_id: str, user_id: str) -> dict:
    """Fetch application row from DB, raise 404 if not found or not owned by user."""
    db = get_db()
    resp = (
        db.table("applications")
        .select("id, status")
        .eq("id", app_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(404, "Application not found")
    return resp.data[0]


# ── Request / Response models ────────────────────────────────────────────────

class TransitionRequest(BaseModel):
    new_status: str
    reason: str = ""


class NoteRequest(BaseModel):
    note: str


class ClassifyEmailRequest(BaseModel):
    subject: str
    body: str


class FollowUpCheckRequest(BaseModel):
    candidate_name: str = "Candidate"
    tone: str = "warm_professional"


class TimelineEventResponse(BaseModel):
    id: str
    application_id: str
    event_type: str
    description: str
    old_status: str
    new_status: str
    timestamp: str


class FollowUpEmailResponse(BaseModel):
    followup_id: str
    application_id: str
    company: str
    role: str
    subject: str
    body: str


class EmailSignalResponse(BaseModel):
    signal_type: str
    confidence: float
    subject: str
    snippet: str


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/{app_id}/transition")
async def transition_application(
    app_id: str,
    request: TransitionRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Transition an application status with validation and timeline logging."""
    app = _get_app_row(app_id, user_id)

    valid_next = VALID_TRANSITIONS.get(app["status"], set())
    if request.new_status not in valid_next:
        raise HTTPException(
            400,
            f"Cannot transition from '{app['status']}' to '{request.new_status}'. "
            f"Valid transitions: {sorted(valid_next)}",
        )

    # Persist new status to DB first, then record timeline event in agent
    get_db().table("applications").update({"status": request.new_status}).eq("id", app_id).execute()
    result = await _agent.transition_status(
        app_id, request.new_status, request.reason, old_status=app["status"]
    )

    return {
        "status": "transitioned",
        "app_id": app_id,
        "old_status": result.timeline_events[0].old_status if result.timeline_events else "",
        "new_status": request.new_status,
        "event_id": result.timeline_events[0].id if result.timeline_events else "",
    }


@router.get("/{app_id}/timeline")
async def get_application_timeline(
    app_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Get the full event timeline for an application."""
    _get_app_row(app_id, user_id)

    events = get_timeline(app_id)
    return [
        TimelineEventResponse(
            id=e.id,
            application_id=e.application_id,
            event_type=e.event_type,
            description=e.description,
            old_status=e.old_status,
            new_status=e.new_status,
            timestamp=e.timestamp,
        )
        for e in events
    ]


@router.post("/{app_id}/note")
async def add_application_note(
    app_id: str,
    request: NoteRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Add a manual note to an application's timeline."""
    _get_app_row(app_id, user_id)

    event = await _agent.add_note(app_id, request.note)
    return {
        "status": "noted",
        "event_id": event.id,
        "timestamp": event.timestamp,
    }


@router.post("/followups/check")
async def check_followups(
    request: FollowUpCheckRequest = FollowUpCheckRequest(),
    user_id: str = Depends(get_current_user_id),
):
    """Check all applications for due follow-ups and generate email drafts."""
    result = await _agent.check_followups(
        candidate_name=request.candidate_name,
        tone=request.tone,
    )
    return {
        "followups_due": len(result.followups_due),
        "stale_applications": result.stale_applications,
        "emails": [
            FollowUpEmailResponse(
                followup_id=e["followup_id"],
                application_id=e["application_id"],
                company=e["company"],
                role=e["role"],
                subject=e["subject"],
                body=e["body"],
            )
            for e in result.followups_generated
        ],
    }


@router.post("/classify-email")
async def classify_email(
    request: ClassifyEmailRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Classify an email to detect application signals (rejection, interview, etc.)."""
    result = await _agent.classify_incoming_email(request.subject, request.body)

    if not result.signals_detected:
        return {"signal_type": "unknown", "confidence": 0.0}

    signal = result.signals_detected[0]
    return EmailSignalResponse(
        signal_type=signal.signal_type,
        confidence=signal.confidence,
        subject=signal.subject,
        snippet=signal.snippet,
    )


class ScanEmailsRequest(BaseModel):
    access_token: str


@router.post("/scan-emails")
async def scan_emails(
    request: ScanEmailsRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Scan Gmail inbox for job-related emails using a user-supplied OAuth access token."""
    from backend.agents.tracker.email_monitor import poll_gmail_inbox
    results = await poll_gmail_inbox(user_id, request.access_token)
    return {"scanned": len(results), "results": results}


@router.get("/{app_id}/valid-transitions")
async def get_valid_transitions(
    app_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Get valid next statuses for an application."""
    app = _get_app_row(app_id, user_id)

    valid_next = VALID_TRANSITIONS.get(app["status"], set())
    return {
        "app_id": app_id,
        "current_status": app["status"],
        "valid_transitions": sorted(valid_next),
    }
