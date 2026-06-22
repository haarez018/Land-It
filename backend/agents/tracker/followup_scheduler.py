"""
Follow-up scheduling engine.

Determines when and how to follow up based on:
  - Time since submission
  - Number of previous follow-ups
  - Application status / stage
  - Company response signals

Rules:
  - 1st follow-up: 7 days after submission
  - 2nd follow-up: 14 days after submission
  - 3rd follow-up: 21 days (final, then mark stale)
  - No follow-up if already interviewing/offered/rejected
  - Shorten to 5 days if the posting mentioned "urgently hiring"
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from typing import Optional


# ── Data models ──────────────────────────────────────────────────────────────

@dataclass
class FollowUp:
    """A scheduled or completed follow-up."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    application_id: str = ""
    followup_number: int = 1         # 1st, 2nd, 3rd
    scheduled_date: str = ""         # ISO date when it should be sent
    sent_date: Optional[str] = None  # ISO date when it was actually sent
    status: str = "pending"          # pending | sent | skipped | cancelled
    subject: str = ""
    body: str = ""


@dataclass
class FollowUpSchedule:
    """Complete follow-up schedule for an application."""
    application_id: str
    company: str
    role: str
    submitted_at: str
    followups: list[FollowUp] = field(default_factory=list)
    is_stale: bool = False  # True after 3rd follow-up with no response
    next_followup_date: Optional[str] = None


# ── Constants ────────────────────────────────────────────────────────────────

FOLLOWUP_INTERVALS_DAYS = [7, 14, 21]  # Days after submission for each follow-up
MAX_FOLLOWUPS = 3
URGENT_INTERVAL_DAYS = [5, 10, 15]     # Shortened for "urgently hiring" roles

# Statuses that block follow-ups
TERMINAL_STATUSES = {"interviewing", "phone_screen", "offer", "rejected", "withdrawn"}


# ── Core logic ───────────────────────────────────────────────────────────────

def compute_followup_schedule(
    application_id: str,
    company: str,
    role: str,
    submitted_at: str,
    *,
    is_urgent: bool = False,
    existing_followups: Optional[list[FollowUp]] = None,
    current_status: str = "submitted",
) -> FollowUpSchedule:
    """
    Compute the follow-up schedule for an application.

    Args:
        application_id: ID of the application
        company: Company name
        role: Role title
        submitted_at: ISO datetime of submission
        is_urgent: Whether the posting signals urgency
        existing_followups: Already-sent follow-ups
        current_status: Current application status

    Returns:
        FollowUpSchedule with pending follow-ups
    """
    existing = existing_followups or []
    intervals = URGENT_INTERVAL_DAYS if is_urgent else FOLLOWUP_INTERVALS_DAYS

    try:
        submit_dt = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        submit_dt = datetime.now(UTC)

    # Don't schedule if terminal
    if current_status in TERMINAL_STATUSES:
        return FollowUpSchedule(
            application_id=application_id,
            company=company,
            role=role,
            submitted_at=submitted_at,
            followups=existing,
            is_stale=False,
            next_followup_date=None,
        )

    # Build scheduled follow-ups
    completed_count = len([f for f in existing if f.status == "sent"])
    pending: list[FollowUp] = list(existing)

    for i in range(completed_count, MAX_FOLLOWUPS):
        if i >= len(intervals):
            break
        scheduled = submit_dt + timedelta(days=intervals[i])
        fu = FollowUp(
            application_id=application_id,
            followup_number=i + 1,
            scheduled_date=scheduled.isoformat(),
            status="pending",
        )
        pending.append(fu)

    # Determine next due date
    pending_fus = [f for f in pending if f.status == "pending"]
    next_date = pending_fus[0].scheduled_date if pending_fus else None

    # Mark stale if all follow-ups exhausted
    is_stale = completed_count >= MAX_FOLLOWUPS

    return FollowUpSchedule(
        application_id=application_id,
        company=company,
        role=role,
        submitted_at=submitted_at,
        followups=pending,
        is_stale=is_stale,
        next_followup_date=next_date,
    )


def get_due_followups(
    schedules: list[FollowUpSchedule],
    as_of: Optional[datetime] = None,
) -> list[FollowUp]:
    """Return all follow-ups that are due (scheduled_date <= now)."""
    now = as_of or datetime.now(UTC)

    due: list[FollowUp] = []
    for sched in schedules:
        for fu in sched.followups:
            if fu.status != "pending":
                continue
            try:
                sched_dt = datetime.fromisoformat(fu.scheduled_date.replace("Z", "+00:00"))
                if sched_dt <= now:
                    due.append(fu)
            except (ValueError, AttributeError):
                continue

    due.sort(key=lambda f: f.scheduled_date)
    return due


def generate_followup_email(
    candidate_name: str,
    company: str,
    role: str,
    followup_number: int,
    days_since: int,
    tone: str = "warm_professional",
) -> dict[str, str]:
    """
    Generate a follow-up email using templates (no LLM required).

    Returns:
        {"subject": "...", "body": "..."}
    """
    # Subject line variations
    subjects = {
        1: f"Following up: {role} application",
        2: f"Checking in: {role} position",
        3: f"Final follow-up: {role} at {company}",
    }

    # Body templates by tone
    if tone == "confident_casual":
        bodies = {
            1: (
                f"Hi there,\n\n"
                f"I applied for the {role} position about a week ago and wanted to check in. "
                f"I'm genuinely excited about this role — the challenges {company} is tackling "
                f"are right in my wheelhouse.\n\n"
                f"Happy to jump on a quick call whenever works for you.\n\n"
                f"Best,\n{candidate_name}"
            ),
            2: (
                f"Hi,\n\n"
                f"Just circling back on my {role} application from {days_since} days ago. "
                f"I'm still very interested and would love to learn more about where things stand.\n\n"
                f"Let me know if you need anything else from my end.\n\n"
                f"Cheers,\n{candidate_name}"
            ),
            3: (
                f"Hi,\n\n"
                f"I wanted to reach out one more time regarding the {role} position. "
                f"I understand if the timeline has shifted — just wanted to reiterate my strong "
                f"interest in joining {company}.\n\n"
                f"I'm happy to stay in touch for future opportunities as well.\n\n"
                f"Best,\n{candidate_name}"
            ),
        }
    elif tone == "formal_authoritative":
        bodies = {
            1: (
                f"Dear Hiring Manager,\n\n"
                f"I am writing to follow up on my application for the {role} position at {company}, "
                f"submitted {days_since} days ago. I remain very interested in this opportunity "
                f"and would welcome the chance to discuss how my experience aligns with your needs.\n\n"
                f"I am available at your convenience for a conversation.\n\n"
                f"Sincerely,\n{candidate_name}"
            ),
            2: (
                f"Dear Hiring Manager,\n\n"
                f"I wanted to follow up once more on my {role} application. "
                f"I continue to be enthusiastic about the role and believe my background "
                f"would be a strong fit for your team.\n\n"
                f"Please do not hesitate to reach out if you require any additional information.\n\n"
                f"Best regards,\n{candidate_name}"
            ),
            3: (
                f"Dear Hiring Manager,\n\n"
                f"This is a final follow-up regarding my application for {role} at {company}. "
                f"I understand that hiring timelines can be unpredictable. Should the position "
                f"or a similar role become available in the future, I would be glad to be considered.\n\n"
                f"Thank you for your time and consideration.\n\n"
                f"Respectfully,\n{candidate_name}"
            ),
        }
    else:  # warm_professional (default)
        bodies = {
            1: (
                f"Hi,\n\n"
                f"I hope this message finds you well. I recently applied for the {role} position "
                f"at {company} and wanted to follow up to express my continued interest. "
                f"The work your team is doing is genuinely exciting, and I'd love the chance "
                f"to contribute.\n\n"
                f"Would you have time for a brief conversation this week?\n\n"
                f"Best regards,\n{candidate_name}"
            ),
            2: (
                f"Hi,\n\n"
                f"I'm checking in on my application for the {role} position, submitted "
                f"{days_since} days ago. I remain very interested in this opportunity and would "
                f"welcome any updates on the timeline.\n\n"
                f"Please let me know if there's anything else I can provide.\n\n"
                f"Best,\n{candidate_name}"
            ),
            3: (
                f"Hi,\n\n"
                f"I wanted to reach out one final time about the {role} position at {company}. "
                f"I understand that hiring processes take time, and I respect your timeline. "
                f"I'm still interested and would be happy to reconnect whenever it makes sense.\n\n"
                f"Thank you for considering my application.\n\n"
                f"Warm regards,\n{candidate_name}"
            ),
        }

    num = min(followup_number, MAX_FOLLOWUPS)
    return {
        "subject": subjects.get(num, subjects[3]),
        "body": bodies.get(num, bodies[3]),
    }
