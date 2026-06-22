"""
Gmail inbox watcher for application status updates via push notifications.

Stub implementation — raises NotImplementedError when GMAIL_CLIENT_ID
is not configured (by design: Day 1 runnable with zero API keys).

The monitor classifies incoming emails into signals:
  - rejection    → move app to "rejected"
  - interview    → move app to "interviewing"
  - phone_screen → move app to "phone_screen"
  - offer        → move app to "offer"
  - acknowledgement → no status change (just note the ack)
  - follow_up_reply → cancel pending follow-ups
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from backend.config import settings


# ── Data models ──────────────────────────────────────────────────────────────

@dataclass
class EmailSignal:
    """An inferred signal from an incoming email."""
    signal_type: str   # rejection | interview | phone_screen | offer | acknowledgement | follow_up_reply | unknown
    confidence: float  # 0.0 to 1.0
    company: str = ""
    role: str = ""
    sender: str = ""
    subject: str = ""
    snippet: str = ""
    raw_body: str = ""
    matched_application_id: Optional[str] = None


# ── Signal classification (heuristic, no LLM) ───────────────────────────────

_REJECTION_PATTERNS = [
    r"we(?:'ve|\s+have)?\s+decided\s+to\s+(?:move|proceed)\s+(?:forward\s+)?with\s+other",
    r"unfortunately.*(?:not\s+(?:be\s+)?(?:moving|proceeding)|decided\s+not)",
    r"we\s+(?:will\s+)?not\s+be\s+(?:moving|advancing)\s+(?:forward\s+)?with",
    r"position\s+has\s+been\s+filled",
    r"not\s+a\s+(?:good\s+)?fit\s+at\s+this\s+time",
    r"we\s+regret\s+to\s+inform",
    r"after\s+careful\s+(?:review|consideration).*(?:not\s+(?:moving|proceeding)|move\s+forward\s+with\s+other)",
]

_INTERVIEW_PATTERNS = [
    r"schedule\s+(?:an?\s+)?interview",
    r"(?:like|love)\s+to\s+(?:set\s+up|schedule)\s+(?:a\s+)?(?:call|meeting|interview)",
    r"invite\s+you\s+(?:to|for)\s+(?:an?\s+)?interview",
    r"next\s+(?:step|round)\s+(?:in|of)\s+(?:the|our)\s+(?:interview|process)",
    r"on[-\s]?site\s+interview",
    r"technical\s+(?:interview|assessment|round)",
    r"panel\s+interview",
]

_PHONE_SCREEN_PATTERNS = [
    r"phone\s+(?:screen|call|interview)",
    r"(?:intro|introductory|initial)\s+(?:call|conversation|chat)",
    r"recruiter\s+(?:call|screen|chat)",
    r"(?:30|15|20|45)\s*[-–]?\s*minute\s+(?:call|chat)",
]

_OFFER_PATTERNS = [
    r"(?:pleased|happy|excited|thrilled)\s+to\s+(?:extend|offer|present)",
    r"offer\s+(?:letter|of\s+employment)",
    r"we\s+(?:would\s+)?(?:like|love)\s+to\s+(?:extend|make)\s+(?:you\s+)?(?:an?\s+)?offer",
    r"compensation\s+package",
    r"start\s+date.*offer",
]

_ACK_PATTERNS = [
    r"(?:received|got)\s+your\s+application",
    r"thank\s+you\s+for\s+(?:applying|your\s+(?:application|interest))",
    r"application\s+(?:has\s+been\s+)?received",
    r"we(?:'ll|\s+will)\s+(?:review|be\s+in\s+touch)",
]


def classify_email(subject: str, body: str) -> EmailSignal:
    """
    Classify an email into a signal type using regex pattern matching.

    Args:
        subject: Email subject line
        body: Email body text

    Returns:
        EmailSignal with type and confidence
    """
    text = f"{subject} {body}".lower()

    # Check for follow-up reply first (reply to our follow-up)
    if re.search(r"re:\s*(?:follow|checking\s+in|final\s+follow)", subject.lower()):
        return EmailSignal(signal_type="follow_up_reply", confidence=0.8, subject=subject)

    def _check_patterns(patterns: list[str]) -> float:
        matches = sum(1 for p in patterns if re.search(p, text))
        return min(1.0, matches / max(len(patterns) * 0.3, 1))

    scores = {
        "rejection": _check_patterns(_REJECTION_PATTERNS),
        "interview": _check_patterns(_INTERVIEW_PATTERNS),
        "phone_screen": _check_patterns(_PHONE_SCREEN_PATTERNS),
        "offer": _check_patterns(_OFFER_PATTERNS),
        "acknowledgement": _check_patterns(_ACK_PATTERNS),
    }

    # Rejection trumps acknowledgement when both match (rejection emails
    # often start with "Thank you for your interest…")
    if scores["rejection"] > 0 and scores["acknowledgement"] > 0:
        scores["acknowledgement"] = 0.0

    # Pick highest confidence
    best_type = max(scores, key=scores.get)  # type: ignore[arg-type]
    best_score = scores[best_type]

    if best_score < 0.3:
        return EmailSignal(signal_type="unknown", confidence=best_score, subject=subject)

    return EmailSignal(
        signal_type=best_type,
        confidence=round(best_score, 2),
        subject=subject,
        snippet=body[:200] if body else "",
    )


# ── Gmail integration stub ──────────────────────────────────────────────────

class GmailMonitor:
    """
    Watches Gmail inbox for application status updates.

    Raises NotImplementedError when Gmail OAuth is not configured.
    """

    def __init__(self):
        if not settings.GMAIL_CLIENT_ID:
            self._available = False
        else:
            self._available = True

    @property
    def is_available(self) -> bool:
        return self._available

    async def check_inbox(self, since_hours: int = 24) -> list[EmailSignal]:
        """
        Check inbox for new application-related emails.

        Raises:
            NotImplementedError: When Gmail OAuth is not configured.
        """
        if not self._available:
            raise NotImplementedError(
                "Gmail OAuth is not configured. "
                "Set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET in .env to enable inbox monitoring."
            )
        # Real implementation would use Gmail API here
        return []

    async def watch_inbox(self) -> None:
        """
        Set up Gmail push notifications via Pub/Sub.

        Raises:
            NotImplementedError: When Gmail OAuth is not configured.
        """
        if not self._available:
            raise NotImplementedError(
                "Gmail push notifications require OAuth configuration."
            )
