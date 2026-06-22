"""
TrackerAgent: manages the application lifecycle, follow-up scheduling,
and status transitions.

Pipeline: check timeline → compute follow-ups → classify signals → update statuses
Works entirely with heuristic logic — no LLM required.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional

from backend.parsers.schemas import JobDescription
from backend.agents.planner.strategy import (
    ApplicationEntry,
    get_application,
    list_applications,
    store_application,
    update_application_status,
)
from backend.agents.tracker.followup_scheduler import (
    FollowUp,
    FollowUpSchedule,
    compute_followup_schedule,
    get_due_followups,
    generate_followup_email,
)
from backend.agents.tracker.email_monitor import (
    EmailSignal,
    GmailMonitor,
    classify_email,
)


# ── Data models ──────────────────────────────────────────────────────────────

@dataclass
class TimelineEvent:
    """A single event in an application's timeline."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    application_id: str = ""
    event_type: str = ""       # status_change | followup_sent | email_received | note
    description: str = ""
    old_status: str = ""
    new_status: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class TrackerResult:
    """Result from the tracker pipeline."""
    applications_updated: int = 0
    followups_due: list[FollowUp] = field(default_factory=list)
    followups_generated: list[dict] = field(default_factory=list)
    signals_detected: list[EmailSignal] = field(default_factory=list)
    timeline_events: list[TimelineEvent] = field(default_factory=list)
    stale_applications: list[str] = field(default_factory=list)


# ── Valid status transitions ─────────────────────────────────────────────────

VALID_TRANSITIONS: dict[str, set[str]] = {
    "discovered": {"queued", "withdrawn"},
    "queued": {"tailoring", "withdrawn"},
    "tailoring": {"ready", "queued", "withdrawn"},
    "ready": {"submitted", "tailoring", "withdrawn"},
    "submitted": {"followed_up", "phone_screen", "interviewing", "rejected", "withdrawn"},
    "followed_up": {"phone_screen", "interviewing", "rejected", "withdrawn"},
    "phone_screen": {"interviewing", "rejected", "withdrawn"},
    "interviewing": {"offer", "rejected", "withdrawn"},
    "offer": {"withdrawn"},
    "rejected": set(),        # Terminal
    "withdrawn": set(),       # Terminal
}


# ── In-memory stores ────────────────────────────────────────────────────────

_timeline_store: dict[str, list[TimelineEvent]] = {}
_followup_store: dict[str, FollowUpSchedule] = {}


def store_timeline_event(event: TimelineEvent) -> None:
    _timeline_store.setdefault(event.application_id, []).append(event)


def get_timeline(application_id: str) -> list[TimelineEvent]:
    return _timeline_store.get(application_id, [])


def store_followup_schedule(schedule: FollowUpSchedule) -> None:
    _followup_store[schedule.application_id] = schedule


def get_followup_schedule(application_id: str) -> Optional[FollowUpSchedule]:
    return _followup_store.get(application_id)


def list_followup_schedules() -> list[FollowUpSchedule]:
    return list(_followup_store.values())


# ── Agent ────────────────────────────────────────────────────────────────────

class TrackerAgent:
    """Manages application lifecycle, timelines, and follow-ups."""

    def __init__(self):
        self.gmail = GmailMonitor()

    async def run(self, state: dict) -> dict:
        """
        LangGraph-compatible run method.

        Expected state keys:
            - action: str — "check_followups" | "transition" | "classify_email" | "scan_inbox" | "timeline"
            - application_id: str (for transition/timeline)
            - new_status: str (for transition)
            - email_subject: str (for classify_email)
            - email_body: str (for classify_email)

        Returns updated state with:
            - tracker_result: TrackerResult
        """
        action = state.get("action", "check_followups")

        if action == "check_followups":
            result = await self.check_followups()
        elif action == "transition":
            result = await self.transition_status(
                state["application_id"],
                state["new_status"],
                reason=state.get("reason", ""),
            )
        elif action == "classify_email":
            result = await self.classify_incoming_email(
                state.get("email_subject", ""),
                state.get("email_body", ""),
            )
        elif action == "scan_inbox":
            result = await self.scan_inbox()
        elif action == "timeline":
            result = TrackerResult(
                timeline_events=get_timeline(state["application_id"]),
            )
        else:
            result = TrackerResult()

        return {**state, "tracker_result": result}

    async def check_followups(
        self,
        candidate_name: str = "Candidate",
        tone: str = "warm_professional",
    ) -> TrackerResult:
        """
        Check all applications for due follow-ups and generate emails.

        Returns:
            TrackerResult with due follow-ups and generated email drafts
        """
        apps = list_applications()
        result = TrackerResult()

        for app in apps:
            if app.status not in ("submitted", "followed_up"):
                continue

            # Compute schedule
            company = app.jd.company if app.jd else "Company"
            role = app.jd.title if app.jd else "Role"
            submitted_at = app.submitted_at or datetime.now(UTC).isoformat()

            existing_schedule = get_followup_schedule(app.id)
            existing_fus = existing_schedule.followups if existing_schedule else []

            schedule = compute_followup_schedule(
                application_id=app.id,
                company=company,
                role=role,
                submitted_at=submitted_at,
                current_status=app.status,
                existing_followups=existing_fus,
            )
            store_followup_schedule(schedule)

            if schedule.is_stale:
                result.stale_applications.append(app.id)

        # Get all due follow-ups
        all_schedules = list_followup_schedules()
        due = get_due_followups(all_schedules)
        result.followups_due = due

        # Generate email drafts for due follow-ups
        for fu in due:
            sched = get_followup_schedule(fu.application_id)
            if not sched:
                continue

            submitted_at = sched.submitted_at
            try:
                submitted_dt = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
                days_since = (datetime.now(UTC) - submitted_dt).days
            except (ValueError, AttributeError):
                days_since = fu.followup_number * 7

            email = generate_followup_email(
                candidate_name=candidate_name,
                company=sched.company,
                role=sched.role,
                followup_number=fu.followup_number,
                days_since=days_since,
                tone=tone,
            )
            result.followups_generated.append({
                "followup_id": fu.id,
                "application_id": fu.application_id,
                "company": sched.company,
                "role": sched.role,
                **email,
            })

        return result

    async def transition_status(
        self,
        application_id: str,
        new_status: str,
        reason: str = "",
    ) -> TrackerResult:
        """
        Transition an application to a new status with validation.

        Args:
            application_id: The application to transition
            new_status: Target status
            reason: Optional reason for the transition

        Returns:
            TrackerResult with timeline events
        """
        result = TrackerResult()

        app = get_application(application_id)
        if not app:
            return result

        old_status = app.status

        # Validate transition
        valid_next = VALID_TRANSITIONS.get(old_status, set())
        if new_status not in valid_next:
            event = TimelineEvent(
                application_id=application_id,
                event_type="error",
                description=f"Invalid transition: {old_status} → {new_status}",
            )
            result.timeline_events.append(event)
            return result

        # Apply transition
        update_application_status(application_id, new_status)
        result.applications_updated = 1

        # Record timeline event
        event = TimelineEvent(
            application_id=application_id,
            event_type="status_change",
            description=reason or f"Status changed from {old_status} to {new_status}",
            old_status=old_status,
            new_status=new_status,
        )
        store_timeline_event(event)
        result.timeline_events.append(event)

        # Auto-record submission timestamp
        if new_status == "submitted" and not app.submitted_at:
            app.submitted_at = datetime.now(UTC).isoformat()

        # Cancel follow-ups if moving to terminal state
        if new_status in ("interviewing", "phone_screen", "offer", "rejected", "withdrawn"):
            sched = get_followup_schedule(application_id)
            if sched:
                for fu in sched.followups:
                    if fu.status == "pending":
                        fu.status = "cancelled"

        return result

    async def classify_incoming_email(
        self,
        subject: str,
        body: str,
    ) -> TrackerResult:
        """
        Classify an email and determine what action to take.

        Returns:
            TrackerResult with detected signals
        """
        signal = classify_email(subject, body)
        result = TrackerResult()
        result.signals_detected.append(signal)
        return result

    async def scan_inbox(self) -> TrackerResult:
        """
        Scan Gmail inbox for new application-related emails.

        Returns:
            TrackerResult with signals and auto-applied transitions.

        Raises:
            NotImplementedError: When Gmail is not configured.
        """
        result = TrackerResult()

        if not self.gmail.is_available:
            raise NotImplementedError(
                "Gmail OAuth is not configured. "
                "Set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET to enable inbox scanning."
            )

        signals = await self.gmail.check_inbox()
        result.signals_detected = signals
        return result

    async def get_application_timeline(
        self,
        application_id: str,
    ) -> list[TimelineEvent]:
        """Get the full timeline for an application."""
        return get_timeline(application_id)

    async def add_note(
        self,
        application_id: str,
        note: str,
    ) -> TimelineEvent:
        """Add a manual note to an application's timeline."""
        event = TimelineEvent(
            application_id=application_id,
            event_type="note",
            description=note,
        )
        store_timeline_event(event)
        return event
