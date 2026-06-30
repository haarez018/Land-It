"""Integration tests for the Tracker agent — lifecycle, follow-ups, transitions."""

import pytest

from backend.agents.tracker.agent import (
    TrackerAgent,
    VALID_TRANSITIONS,
    store_timeline_event,
    get_timeline,
    TimelineEvent,
)
from backend.agents.planner.strategy import (
    ApplicationEntry,
    store_application,
    get_application,
    update_application_status,
)
from backend.parsers.schemas import JobDescription


def _app(status="submitted", fit=80.0, **kw) -> ApplicationEntry:
    app = ApplicationEntry(
        status=status,
        fit_score=fit,
        jd=JobDescription(title="Backend Eng", company="Stripe"),
        **kw,
    )
    store_application(app)
    return app


class TestTrackerAgentTransitions:

    @pytest.mark.asyncio
    async def test_valid_transition(self):
        agent = TrackerAgent()
        app = _app(status="queued")

        result = await agent.transition_status(app.id, "tailoring", "Starting tailor")
        assert result.applications_updated == 1
        assert result.timeline_events[0].old_status == "queued"
        assert result.timeline_events[0].new_status == "tailoring"

        # Verify persisted
        updated = get_application(app.id)
        assert updated.status == "tailoring"

    @pytest.mark.asyncio
    async def test_invalid_transition_rejected(self):
        agent = TrackerAgent()
        app = _app(status="queued")

        result = await agent.transition_status(app.id, "offer")
        assert result.applications_updated == 0
        assert result.timeline_events[0].event_type == "error"

    @pytest.mark.asyncio
    async def test_transition_records_timeline(self):
        agent = TrackerAgent()
        app = _app(status="ready")

        await agent.transition_status(app.id, "submitted", "Submitted via email")

        timeline = get_timeline(app.id)
        assert len(timeline) >= 1
        assert timeline[-1].event_type == "status_change"
        assert timeline[-1].description == "Submitted via email"

    @pytest.mark.asyncio
    async def test_submitted_sets_timestamp(self):
        agent = TrackerAgent()
        app = _app(status="ready")
        assert app.submitted_at is None

        await agent.transition_status(app.id, "submitted")
        updated = get_application(app.id)
        assert updated.submitted_at is not None

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Walk an application through the full pipeline."""
        agent = TrackerAgent()
        app = _app(status="queued")

        transitions = [
            ("tailoring", "Started tailoring resume"),
            ("ready", "Resume tailored, cover letter done"),
            ("submitted", "Applied via company portal"),
            ("phone_screen", "Recruiter reached out"),
            ("interviewing", "Technical interview scheduled"),
            ("offer", "Offer received!"),
        ]
        for new_status, reason in transitions:
            result = await agent.transition_status(app.id, new_status, reason)
            assert result.applications_updated == 1

        updated = get_application(app.id)
        assert updated.status == "offer"

        timeline = get_timeline(app.id)
        assert len(timeline) == len(transitions)


class TestTrackerAgentNotes:

    @pytest.mark.asyncio
    async def test_add_note(self):
        agent = TrackerAgent()
        app = _app(status="submitted")

        event = await agent.add_note(app.id, "Recruiter is OOO until Monday")
        assert event.event_type == "note"
        assert "OOO" in event.description

        timeline = get_timeline(app.id)
        notes = [e for e in timeline if e.event_type == "note"]
        assert len(notes) >= 1


class TestTrackerAgentFollowUps:

    @pytest.mark.asyncio
    async def test_check_followups_generates_emails(self):
        agent = TrackerAgent()
        from datetime import datetime, timedelta, UTC

        # Create a submitted app from 8 days ago (past 1st follow-up window)
        app = _app(status="submitted")
        app.submitted_at = (datetime.now(UTC) - timedelta(days=8)).isoformat()
        store_application(app)

        result = await agent.check_followups(candidate_name="Alex Chen")

        assert len(result.followups_due) >= 1
        assert len(result.followups_generated) >= 1
        assert result.followups_generated[0]["company"] == "Stripe"
        assert "Alex Chen" in result.followups_generated[0]["body"]


class TestTrackerAgentEmailClassification:

    @pytest.mark.asyncio
    async def test_classify_rejection(self):
        agent = TrackerAgent()
        result = await agent.classify_incoming_email(
            "Update on your application",
            "We regret to inform you that we have decided to proceed with other candidates.",
        )
        assert len(result.signals_detected) == 1
        assert result.signals_detected[0].signal_type == "rejection"

    @pytest.mark.asyncio
    async def test_classify_interview(self):
        agent = TrackerAgent()
        result = await agent.classify_incoming_email(
            "Next steps",
            "We'd like to invite you to a technical interview next week.",
        )
        assert result.signals_detected[0].signal_type == "interview"


class TestTrackerAgentLangGraph:

    @pytest.mark.asyncio
    async def test_run_check_followups(self):
        agent = TrackerAgent()
        state = {"action": "check_followups"}
        result = await agent.run(state)
        assert "tracker_result" in result

    @pytest.mark.asyncio
    async def test_run_classify_email(self):
        agent = TrackerAgent()
        state = {
            "action": "classify_email",
            "email_subject": "Interview invitation",
            "email_body": "We'd love to schedule an interview with you.",
        }
        result = await agent.run(state)
        assert result["tracker_result"].signals_detected[0].signal_type == "interview"

    @pytest.mark.asyncio
    async def test_run_transition(self):
        agent = TrackerAgent()
        app = _app(status="tailoring")
        state = {
            "action": "transition",
            "application_id": app.id,
            "new_status": "ready",
            "reason": "Tailor complete",
        }
        result = await agent.run(state)
        assert result["tracker_result"].applications_updated == 1

    @pytest.mark.asyncio
    async def test_run_timeline(self):
        agent = TrackerAgent()
        app = _app(status="submitted")
        await agent.add_note(app.id, "Test note")

        state = {"action": "timeline", "application_id": app.id}
        result = await agent.run(state)
        assert len(result["tracker_result"].timeline_events) >= 1

    @pytest.mark.asyncio
    async def test_run_scan_inbox_raises(self):
        """scan_inbox should raise NotImplementedError without Gmail OAuth."""
        agent = TrackerAgent()
        with pytest.raises(NotImplementedError, match="Gmail OAuth"):
            await agent.run({"action": "scan_inbox"})
