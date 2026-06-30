"""Tests for the follow-up scheduling engine."""

from datetime import datetime, timedelta, UTC

import pytest

from backend.agents.tracker.followup_scheduler import (
    FollowUp,
    FollowUpSchedule,
    compute_followup_schedule,
    get_due_followups,
    generate_followup_email,
    MAX_FOLLOWUPS,
    FOLLOWUP_INTERVALS_DAYS,
    URGENT_INTERVAL_DAYS,
)


def _iso_now(offset_days: int = 0) -> str:
    return (datetime.now(UTC) + timedelta(days=offset_days)).isoformat()


class TestComputeFollowUpSchedule:

    def test_fresh_application_gets_3_followups(self):
        sched = compute_followup_schedule(
            application_id="app1",
            company="Stripe",
            role="Backend Eng",
            submitted_at=_iso_now(-1),
        )
        pending = [f for f in sched.followups if f.status == "pending"]
        assert len(pending) == MAX_FOLLOWUPS

    def test_followup_numbers_are_sequential(self):
        sched = compute_followup_schedule(
            application_id="app1",
            company="Stripe",
            role="Eng",
            submitted_at=_iso_now(-1),
        )
        nums = [f.followup_number for f in sched.followups]
        assert nums == [1, 2, 3]

    def test_terminal_status_gets_no_followups(self):
        for status in ("interviewing", "offer", "rejected", "withdrawn"):
            sched = compute_followup_schedule(
                application_id="app1",
                company="Co",
                role="Eng",
                submitted_at=_iso_now(-10),
                current_status=status,
            )
            pending = [f for f in sched.followups if f.status == "pending"]
            assert len(pending) == 0, f"Expected no pending for status={status}"

    def test_urgent_uses_shorter_intervals(self):
        sched = compute_followup_schedule(
            application_id="app1",
            company="Co",
            role="Eng",
            submitted_at=_iso_now(0),
            is_urgent=True,
        )
        # First follow-up should be 5 days, not 7
        first = sched.followups[0]
        sched_dt = datetime.fromisoformat(first.scheduled_date)
        now = datetime.now(UTC)
        delta = (sched_dt - now).days
        assert delta <= URGENT_INTERVAL_DAYS[0] + 1

    def test_existing_sent_followups_skipped(self):
        sent = FollowUp(
            application_id="app1",
            followup_number=1,
            scheduled_date=_iso_now(-5),
            status="sent",
        )
        sched = compute_followup_schedule(
            application_id="app1",
            company="Co",
            role="Eng",
            submitted_at=_iso_now(-10),
            existing_followups=[sent],
        )
        # Should have the sent one + 2 new pending
        pending = [f for f in sched.followups if f.status == "pending"]
        assert len(pending) == 2

    def test_all_sent_marks_stale(self):
        sent = [
            FollowUp(application_id="app1", followup_number=i + 1,
                     scheduled_date=_iso_now(-20 + i * 7), status="sent")
            for i in range(MAX_FOLLOWUPS)
        ]
        sched = compute_followup_schedule(
            application_id="app1",
            company="Co",
            role="Eng",
            submitted_at=_iso_now(-30),
            existing_followups=sent,
        )
        assert sched.is_stale is True

    def test_next_followup_date_set(self):
        sched = compute_followup_schedule(
            application_id="app1",
            company="Co",
            role="Eng",
            submitted_at=_iso_now(-1),
        )
        assert sched.next_followup_date is not None


class TestGetDueFollowups:

    def test_returns_due_followups(self):
        past = _iso_now(-2)
        future = _iso_now(5)
        schedules = [
            FollowUpSchedule(
                application_id="app1",
                company="Co",
                role="Eng",
                submitted_at=_iso_now(-10),
                followups=[
                    FollowUp(application_id="app1", followup_number=1,
                             scheduled_date=past, status="pending"),
                    FollowUp(application_id="app1", followup_number=2,
                             scheduled_date=future, status="pending"),
                ],
            )
        ]
        due = get_due_followups(schedules)
        assert len(due) == 1
        assert due[0].followup_number == 1

    def test_ignores_sent(self):
        past = _iso_now(-2)
        schedules = [
            FollowUpSchedule(
                application_id="app1",
                company="Co",
                role="Eng",
                submitted_at=_iso_now(-10),
                followups=[
                    FollowUp(application_id="app1", followup_number=1,
                             scheduled_date=past, status="sent"),
                ],
            )
        ]
        due = get_due_followups(schedules)
        assert len(due) == 0

    def test_empty_schedules(self):
        assert get_due_followups([]) == []


class TestGenerateFollowupEmail:

    def test_first_followup(self):
        email = generate_followup_email(
            candidate_name="Alex", company="Stripe", role="Backend Eng",
            followup_number=1, days_since=7,
        )
        assert "subject" in email
        assert "body" in email
        assert "Backend Eng" in email["subject"]
        assert "Alex" in email["body"]

    def test_final_followup(self):
        email = generate_followup_email(
            candidate_name="Alex", company="Stripe", role="Backend Eng",
            followup_number=3, days_since=21,
        )
        assert "final" in email["subject"].lower() or "Final" in email["subject"]

    def test_tone_casual(self):
        email = generate_followup_email(
            candidate_name="Alex", company="Co", role="Eng",
            followup_number=1, days_since=7, tone="confident_casual",
        )
        # Casual tone uses "Cheers" or "Best" but not "Sincerely"
        assert "Sincerely" not in email["body"]

    def test_tone_formal(self):
        email = generate_followup_email(
            candidate_name="Alex", company="Co", role="Eng",
            followup_number=1, days_since=7, tone="formal_authoritative",
        )
        assert "Dear Hiring Manager" in email["body"]

    def test_tone_warm_professional(self):
        email = generate_followup_email(
            candidate_name="Alex", company="Co", role="Eng",
            followup_number=1, days_since=7, tone="warm_professional",
        )
        assert "Alex" in email["body"]
        assert "Best regards" in email["body"] or "Best" in email["body"]

    def test_all_three_followup_numbers(self):
        for n in range(1, 4):
            email = generate_followup_email(
                candidate_name="Test", company="Co", role="Eng",
                followup_number=n, days_since=n * 7,
            )
            assert email["subject"]
            assert email["body"]
            assert len(email["body"]) > 50
