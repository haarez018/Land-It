"""Smart Notifications Engine: proactive nudges based on user state."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class Notification:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    type: str = "info"
    priority: str = "medium"
    title: str = ""
    body: str = ""
    action_url: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    dismissed: bool = False


NOTIFICATION_TRIGGERS: dict[str, dict] = {
    "stale_resume": {
        "message": "Your resume hasn't been scored in 2 weeks. Rescore against your latest targets.",
        "type": "reminder", "priority": "medium",
    },
    "follow_up_due": {
        "message": "No reply from {company} in {days} days. Ready to send a follow-up?",
        "type": "action", "priority": "high",
    },
    "score_milestone": {
        "message": "Your resume just hit 80+ for the first time! Top 15% of applicants.",
        "type": "celebration", "priority": "low",
    },
    "callback_prediction_high": {
        "message": "Strong match! {company} {role} has a {probability}% callback probability.",
        "type": "insight", "priority": "high",
    },
    "weekly_goal_behind": {
        "message": "Applied to {count}/{goal} this week. Pick up the pace to hit your goal.",
        "type": "reminder", "priority": "medium",
    },
    "gap_filled": {
        "message": "Adding {skill} closed a gap in 4 target roles. Rescore to see the impact.",
        "type": "celebration", "priority": "low",
    },
}


class NotificationEngine:
    def __init__(self) -> None:
        self._notifications: dict[str, list[Notification]] = {}

    def add(self, user_id: str, notification: Notification) -> None:
        self._notifications.setdefault(user_id, []).append(notification)

    def get_pending(self, user_id: str) -> list[Notification]:
        return [n for n in self._notifications.get(user_id, []) if not n.dismissed]

    def dismiss(self, user_id: str, notification_id: str) -> bool:
        for n in self._notifications.get(user_id, []):
            if n.id == notification_id:
                n.dismissed = True
                return True
        return False

    def check_stale_resume(self, user_id: str, days_since_score: int) -> Notification | None:
        if days_since_score >= 14:
            n = Notification(
                type="reminder", priority="medium",
                title="Resume needs rescoring",
                body=NOTIFICATION_TRIGGERS["stale_resume"]["message"],
                action_url="/tailor",
            )
            self.add(user_id, n)
            return n
        return None

    def check_follow_up(self, user_id: str, company: str, days: int) -> Notification | None:
        if days >= 7:
            msg = NOTIFICATION_TRIGGERS["follow_up_due"]["message"].format(company=company, days=days)
            n = Notification(
                type="action", priority="high",
                title=f"Follow up with {company}",
                body=msg, action_url="/tracker",
            )
            self.add(user_id, n)
            return n
        return None

    def check_score_milestone(self, user_id: str, score: float, prev_best: float) -> Notification | None:
        if score >= 80 and prev_best < 80:
            n = Notification(
                type="celebration", priority="low",
                title="Score milestone!",
                body=NOTIFICATION_TRIGGERS["score_milestone"]["message"],
            )
            self.add(user_id, n)
            return n
        return None

    def clear(self, user_id: str | None = None) -> None:
        if user_id:
            self._notifications.pop(user_id, None)
        else:
            self._notifications.clear()


notification_engine = NotificationEngine()
