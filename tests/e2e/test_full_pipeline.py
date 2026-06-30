"""
End-to-end pipeline tests.

Each test exercises the full multi-agent flow the way a real user
would experience it — no mocking, no shortcuts.

Flow tested:
  1. Parse resume text → Resume
  2. Parse JD text     → JobDescription
  3. Scout: fit-score the JD against the resume
  4. Tailor: ATS-score and rewrite the resume for the JD
  5. Pitcher: generate a cover letter
  6. Coach: run a mock interview session
  7. Planner: plan the week and generate a report
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from backend.parsers.schemas import (
    Resume,
    ResumeContact,
    WorkExperience,
    Education,
    JobDescription,
    JDRequirement,
)
from backend.parsers.jd_parser import parse_jd

# Agents
from backend.agents.scout.agent import ScoutAgent
from backend.agents.scout.scorer import score_fit
from backend.agents.tailor.agent import TailorAgent
from backend.agents.pitcher.agent import PitcherAgent
from backend.agents.coach.agent import CoachAgent
from backend.agents.planner.agent import PlannerAgent
from backend.agents.planner.strategy import (
    ApplicationEntry,
    WeeklyGoal,
    store_application,
)
from backend.agents.tracker.agent import TrackerAgent


# ── Fixtures ────────────────────────────────────────────────────────────────

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _resume() -> Resume:
    """Realistic senior backend resume for testing."""
    return Resume(
        contact=ResumeContact(
            name="Alex Chen",
            email="alex@example.com",
            phone="555-1234",
            linkedin="linkedin.com/in/alexchen",
            github="github.com/alexchen",
            location="San Francisco, CA",
        ),
        raw_text=(
            "Alex Chen | alex@example.com | 555-1234\n\n"
            "SUMMARY\n"
            "Senior backend engineer with 8+ years building distributed systems at scale. "
            "Led teams of up to 12 engineers. Expert in Go, Python, Kafka, PostgreSQL.\n\n"
            "EXPERIENCE\n"
            "Senior Software Engineer at Google\nJan 2020 - Present\nSan Francisco, CA\n"
            "- Architected event processing pipeline handling 5M events/day using Kafka and Go, reducing latency by 40%\n"
            "- Led team of 8 engineers to redesign notification service, reliability 94% to 99.7%\n"
            "- Migrated monolith to microservices, reducing deployment time by 60%\n"
            "- Mentored 4 junior engineers through promotion to L4\n\n"
            "Software Engineer at Stripe\nMar 2017 - Dec 2019\nSan Francisco, CA\n"
            "- Built fraud detection API serving 50K req/sec with p99 < 100ms using Python and Redis\n"
            "- Designed distributed rate limiter used across 12 internal services\n"
            "- Reduced infra costs by $2.1M/year optimizing database queries\n\n"
            "SKILLS\nPython, Go, Kafka, PostgreSQL, Redis, Docker, Kubernetes, AWS, gRPC\n\n"
            "EDUCATION\nBS Computer Science, Stanford University, 2017"
        ),
        summary="Senior backend engineer with 8+ years building distributed systems at scale.",
        work_experience=[
            WorkExperience(
                company="Google",
                title="Senior Software Engineer",
                start_date=date(2020, 1, 1),
                bullets=[
                    "Architected event processing pipeline handling 5M events/day using Kafka and Go, reducing latency by 40%",
                    "Led team of 8 engineers to redesign notification service, reliability 94% to 99.7%",
                    "Migrated monolith to microservices, reducing deployment time by 60%",
                    "Mentored 4 junior engineers through promotion to L4",
                ],
                technologies=["Kafka", "Go", "Python", "PostgreSQL", "gRPC"],
                impact_metrics=["5M events/day", "99.7% reliability", "60% deployment reduction"],
            ),
            WorkExperience(
                company="Stripe",
                title="Software Engineer",
                start_date=date(2017, 3, 1),
                end_date=date(2019, 12, 31),
                bullets=[
                    "Built fraud detection API serving 50K req/sec with p99 < 100ms using Python and Redis",
                    "Designed distributed rate limiter used across 12 internal services",
                    "Reduced infra costs by $2.1M/year optimizing database queries",
                ],
                technologies=["Python", "Redis", "Django", "PostgreSQL"],
                impact_metrics=["50K req/sec", "$2.1M/year savings"],
            ),
        ],
        education=[
            Education(
                institution="Stanford University",
                degree="BS Computer Science",
                field="Computer Science",
                graduation_date=date(2017, 6, 1),
                gpa=3.8,
                honors=["Magna Cum Laude"],
            ),
        ],
        skills={
            "languages": ["Python", "Go"],
            "databases": ["PostgreSQL", "Redis"],
            "infrastructure": ["Docker", "Kubernetes", "AWS"],
            "messaging": ["Kafka"],
            "protocols": ["gRPC", "REST"],
        },
        seniority_level="senior",
        total_yoe=8.5,
        primary_domain="backend",
    )


def _jd() -> JobDescription:
    """Realistic senior backend engineer JD."""
    return JobDescription(
        raw_text=(
            "Senior Backend Engineer at Stripe\n\n"
            "Build scalable payment infrastructure. "
            "Required: Python, Go, Kafka, PostgreSQL. 5+ years backend experience. "
            "Experience with distributed systems, microservices, event-driven architectures. "
            "Nice to have: Kubernetes, gRPC, AWS. "
            "Domain: fintech, payments, transactions, compliance."
        ),
        title="Senior Backend Engineer",
        company="Stripe",
        location="San Francisco, CA",
        remote_policy="hybrid",
        seniority_level="senior",
        employment_type="full_time",
        required_skills=["Python", "Go", "Kafka", "PostgreSQL"],
        preferred_skills=["Kubernetes", "gRPC", "AWS"],
        tech_stack=["Python", "Go", "Kafka", "PostgreSQL", "Kubernetes", "gRPC"],
        requirements=[
            JDRequirement(text="5+ years backend experience", category="must_have",
                         skill_type="technical", extracted_keyword="backend"),
            JDRequirement(text="Experience with distributed systems", category="must_have",
                         skill_type="technical", extracted_keyword="distributed systems"),
            JDRequirement(text="Microservices architecture", category="must_have",
                         skill_type="technical", extracted_keyword="microservices"),
            JDRequirement(text="Strong API design skills", category="must_have",
                         skill_type="technical", extracted_keyword="API design"),
        ],
        required_experience_years=5,
        required_education="BS Computer Science",
        role_priorities=["Build scalable payment infrastructure", "Design distributed systems"],
        company_values=["transparency", "rigor", "users first"],
    )


# ── 1. Parse from raw text ──────────────────────────────────────────────────

class TestParseFromText:
    """Verify that the parsers handle fixture text files end-to-end."""

    def test_parse_jd_from_fixture(self):
        jd_text = (FIXTURES / "sample_jds" / "backend_engineer.txt").read_text()
        jd = parse_jd(jd_text)
        assert jd.title
        assert jd.company
        assert len(jd.required_skills) >= 1
        assert len(jd.tech_stack) >= 1

    def test_parse_jd_extracts_requirements(self):
        jd_text = (FIXTURES / "sample_jds" / "backend_engineer.txt").read_text()
        jd = parse_jd(jd_text)
        assert len(jd.requirements) >= 3


# ── 2. Scout → fit-score ────────────────────────────────────────────────────

class TestScoutPipeline:

    @pytest.mark.asyncio
    async def test_score_single_jd(self):
        """Score a single JD against the resume — full Scout pipeline."""
        scout = ScoutAgent()
        jd_text = (FIXTURES / "sample_jds" / "backend_engineer.txt").read_text()

        result = await scout.score_single_jd(_resume(), jd_text)

        assert result.total_scored == 1
        assert result.jobs[0].fit.total_score > 0
        assert len(result.jobs[0].fit.dimensions) >= 5

    @pytest.mark.asyncio
    async def test_score_batch(self):
        """Score multiple JDs in batch."""
        scout = ScoutAgent()
        jd_texts = [
            (FIXTURES / "sample_jds" / f).read_text()
            for f in ("backend_engineer.txt", "data_scientist.txt")
        ]
        result = await scout.score_batch(_resume(), jd_texts)

        assert result.total_scored == 2
        assert result.jobs[0].fit.total_score >= result.jobs[1].fit.total_score

    @pytest.mark.asyncio
    async def test_fit_score_deterministic(self):
        """Same inputs → same fit score every time."""
        resume = _resume()
        jd = _jd()
        s1 = score_fit(resume, jd)
        s2 = score_fit(resume, jd)
        assert s1.total_score == s2.total_score


# ── 3. Tailor → ATS score + rewrite ─────────────────────────────────────────

class TestTailorPipeline:

    @pytest.mark.asyncio
    async def test_full_tailor(self):
        """Full tailor pipeline: score → rewrite → re-score → diff."""
        tailor = TailorAgent()
        result = await tailor.tailor(_resume(), _jd())

        assert result.score_before.total_score > 0
        assert result.score_after.total_score > 0
        assert result.improvement is not None
        assert result.diff is not None
        assert len(result.rewrite_result.change_log) >= 1

    @pytest.mark.asyncio
    async def test_tailor_preserves_identity(self):
        """Rewriter must not change the candidate's name or contact info."""
        tailor = TailorAgent()
        result = await tailor.tailor(_resume(), _jd())

        assert result.rewritten_resume.contact.name == "Alex Chen"
        assert result.rewritten_resume.contact.email == "alex@example.com"

    @pytest.mark.asyncio
    async def test_tailor_diff_has_content(self):
        """The diff should contain actual changes, not be empty."""
        tailor = TailorAgent()
        result = await tailor.tailor(_resume(), _jd())

        # Either the unified diff or the change log should be non-empty
        assert result.diff.unified_diff or len(result.rewrite_result.change_log) >= 1

    @pytest.mark.asyncio
    async def test_tailor_score_has_14_dimensions(self):
        """ATS score should have all 14 dimensions."""
        tailor = TailorAgent()
        result = await tailor.tailor(_resume(), _jd())
        assert len(result.score_before.dimension_scores) == 14


# ── 3b. Standout + DualScore ───────────────────────────────────────────────

class TestStandoutPipeline:

    @pytest.mark.asyncio
    async def test_standout_scoring(self):
        """Score a resume on the 8 Standout (human-impression) dimensions."""
        from backend.agents.tailor.standout.engine import score_standout

        result = await score_standout(_resume(), _jd())
        assert result.total_score > 0
        assert len(result.dimension_scores) == 8
        assert result.letter_grade in {"A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "F"}

    @pytest.mark.asyncio
    async def test_dual_score(self):
        """Full 22-dimension dual scoring: 14 ATS + 8 Standout."""
        tailor = TailorAgent()
        result = await tailor.score_dual(_resume(), _jd())

        assert result.total_dimensions == 22
        assert 0 <= result.combined_score <= 100
        assert len(result.ats.dimension_scores) == 14
        assert len(result.standout.dimension_scores) == 8
        assert result.summary  # should have a human-readable summary

    @pytest.mark.asyncio
    async def test_dual_score_includes_callback_prediction(self):
        """score_dual() should include a callback prediction."""
        tailor = TailorAgent()
        result = await tailor.score_dual(_resume(), _jd())

        pred = result.callback_prediction
        assert pred is not None
        assert 0 < pred.probability <= 0.85
        lower, upper = pred.confidence_interval
        assert lower <= pred.probability <= upper
        assert pred.confidence_level in {"high", "medium", "low"}
        assert pred.combined_score > 0
        assert pred.base_rate > 0
        assert len(pred.top_positive_factors) >= 1

    @pytest.mark.asyncio
    async def test_callback_prediction_standalone(self):
        """Predict callback probability from pre-computed scores."""
        from backend.agents.tailor.prediction.interview_predictor import predict_callback
        from backend.agents.tailor.weightage.scorer_engine import score_resume
        from backend.agents.tailor.standout.engine import score_standout

        resume = _resume()
        jd = _jd()
        ats = await score_resume(resume, jd)
        standout_result = await score_standout(resume, jd)

        pred = predict_callback(ats, standout_result)
        # Strong resume (Google + Stripe + Stanford) should get decent probability
        assert pred.probability > 0.10
        assert pred.vs_average_applicant > 0  # above average

    @pytest.mark.asyncio
    async def test_tailor_produces_dual_scores(self):
        """The tailor pipeline should now produce dual scores before and after."""
        tailor = TailorAgent()
        result = await tailor.tailor(_resume(), _jd())

        assert result.dual_score_before is not None
        assert result.dual_score_after is not None
        assert result.dual_score_before.total_dimensions == 22
        assert result.dual_score_after.total_dimensions == 22

    @pytest.mark.asyncio
    async def test_strong_resume_has_spikes(self):
        """Our fixture resume (Google + Stripe + Stanford) should detect spikes."""
        from backend.agents.tailor.standout.engine import score_standout

        result = await score_standout(_resume(), _jd())
        # With Google, Stripe, Stanford, patents — should have a good spike score
        spike = next(d for d in result.dimension_scores if d.dimension_id == "spike_factor")
        assert spike.raw_score >= 30  # Google + Stripe = strong brand spike

    @pytest.mark.asyncio
    async def test_company_profile_changes_weights(self):
        """Scoring against Stripe vs a generic company should use different weights."""
        from backend.agents.tailor.weightage.scorer_engine import score_resume

        resume = _resume()
        jd_stripe = _jd()  # company = "Stripe"
        result_stripe = await score_resume(resume, jd_stripe)

        # Score against a company with no profile match
        jd_generic = _jd()
        jd_generic.company = "Acme Corp"
        result_generic = await score_resume(resume, jd_generic)

        # Weights should differ because Stripe profile is applied
        assert result_stripe.weights_used != result_generic.weights_used

    @pytest.mark.asyncio
    async def test_company_profile_in_dual_score(self):
        """score_dual should apply company profile automatically from JD."""
        tailor = TailorAgent()
        result = await tailor.score_dual(_resume(), _jd())  # Stripe JD
        # Should still produce valid 22-dimension result with company adjustments
        assert result.total_dimensions == 22
        assert 0 <= result.combined_score <= 100


# ── 3c. Resume A/B Testing ────────────────────────────────────────────────

class TestABTestingPipeline:

    @pytest.mark.asyncio
    async def test_ab_test_strong_vs_weak(self):
        """A/B test the full fixture resume against a stripped-down version."""
        from backend.agents.tailor.ab_testing import ab_test_resumes

        strong = _resume()
        weak = Resume(
            contact=ResumeContact(name="Test User", email="test@example.com"),
            raw_text="Developer at Smallco. Fixed bugs.",
            work_experience=[
                WorkExperience(
                    company="Smallco",
                    title="Developer",
                    start_date=date(2022, 1, 1),
                    bullets=["Fixed bugs", "Wrote tests"],
                    technologies=["Python"],
                ),
            ],
            education=[],
            skills={"languages": ["Python"]},
            seniority_level="junior",
            total_yoe=2.0,
            primary_domain="general",
        )

        result = await ab_test_resumes(strong, weak, _jd())
        assert result.overall_winner == "A"
        assert len(result.a_advantages) > 0
        assert len(result.dimension_comparisons) == 22
        assert len(result.merge_suggestions) >= 3  # summary, work_exp, skills, edu
        assert len(result.recommendation) > 10

    @pytest.mark.asyncio
    async def test_ab_test_identical_is_tie(self):
        """A/B testing the same resume against itself should be a tie."""
        from backend.agents.tailor.ab_testing import ab_test_resumes

        resume = _resume()
        result = await ab_test_resumes(resume, resume, _jd())
        assert result.overall_winner == "tie"
        # All dims should be ties (delta = 0 < 3)
        ties = sum(1 for c in result.dimension_comparisons if c.winner == "tie")
        assert ties == 22


# ── 4. Pitcher → cover letter ───────────────────────────────────────────────

class TestPitcherPipeline:

    @pytest.mark.asyncio
    async def test_generate_cover_letter(self):
        """Full pitcher pipeline: voice → company → letter → validate."""
        pitcher = PitcherAgent()
        result = await pitcher.generate(
            _resume(), _jd(),
            writing_samples=[
                "I've always believed that the best code is the code you don't write. "
                "When I joined Google, the first thing I did was audit the existing payment pipeline "
                "and found 30% of the code was dead.",
                "Building systems that handle millions of requests is about constraints, not complexity. "
                "At Stripe, we learned this the hard way during Black Friday."
            ],
        )

        assert result.cover_letter.text
        assert result.cover_letter.word_count > 50
        assert result.cover_letter.paragraphs >= 3
        assert result.cover_letter.company_name == "Stripe"
        assert result.voice_profile.tone
        assert result.company_context.company_name == "Stripe"

    @pytest.mark.asyncio
    async def test_cover_letter_mentions_company(self):
        """The cover letter should reference the company by name."""
        pitcher = PitcherAgent()
        result = await pitcher.generate(_resume(), _jd())

        assert "stripe" in result.cover_letter.text.lower()

    @pytest.mark.asyncio
    async def test_alternative_openings_generated(self):
        """Should produce at least one alternative opening."""
        pitcher = PitcherAgent()
        result = await pitcher.generate(_resume(), _jd())

        assert len(result.alternative_openings) >= 1


# ── 5. Coach → interview session ────────────────────────────────────────────

class TestCoachPipeline:

    @pytest.mark.asyncio
    async def test_full_session_lifecycle(self):
        """Start session → answer questions → get summary."""
        coach = CoachAgent()

        # Start
        start_result = await coach.start_session(_jd())
        session = start_result.session
        assert session.id
        assert len(session.questions) >= 5

        # Answer first 3 questions
        for _ in range(3):
            q = session.current_question
            assert q is not None
            grade = await coach.submit_answer(
                session.id,
                "In my role at Google, I led the migration from a monolithic architecture to "
                "microservices. The situation was that deployment took 4 hours. I identified the "
                "key coupling points and designed an incremental migration. As a result, we reduced "
                "deployment time by 60% and improved team velocity by 3x.",
                duration=45.0,
            )
            assert grade is not None
            assert grade.overall_score > 0

        # Skip one
        await coach.skip_question(session.id)

        # Summary (partial)
        summary = await coach.get_summary(session.id)
        assert summary is not None
        assert summary.questions_answered == 3
        assert summary.questions_skipped == 1

    @pytest.mark.asyncio
    async def test_questions_match_jd(self):
        """Questions should include JD-specific content, not just generic ones."""
        coach = CoachAgent()
        result = await coach.start_session(_jd(), _resume())

        texts = [q.text.lower() for q in result.session.questions]
        combined = " ".join(texts)

        # At least some questions should reference tech from the JD
        tech_mentioned = any(
            tech.lower() in combined
            for tech in ["python", "go", "kafka", "postgresql", "distributed", "payment"]
        )
        assert tech_mentioned, "Expected at least one JD-specific term in the questions"


# ── 6. Planner → weekly plan + report ────────────────────────────────────────

class TestPlannerPipeline:

    @pytest.mark.asyncio
    async def test_full_weekly_plan(self):
        """Full planner pipeline with multiple applications across stages."""
        planner = PlannerAgent()

        apps = [
            ApplicationEntry(
                status="queued", fit_score=85.0,
                jd=JobDescription(title="Backend Eng", company="Stripe"),
            ),
            ApplicationEntry(
                status="ready", fit_score=70.0,
                jd=JobDescription(title="Platform Eng", company="Datadog"),
            ),
            ApplicationEntry(
                status="interviewing", fit_score=90.0,
                jd=JobDescription(title="Staff Eng", company="Notion"),
            ),
            ApplicationEntry(
                status="submitted", fit_score=60.0,
                jd=JobDescription(title="SRE", company="Google"),
            ),
        ]
        goal = WeeklyGoal(target_applications=10, target_role="Senior Backend Engineer")

        result = await planner.plan_week(apps, goal)

        assert result.report.summary
        assert result.report.applications_sent == 1  # 1 submitted
        assert result.report.interviews_scheduled == 1  # 1 interviewing
        assert len(result.prioritized_apps) >= 1
        assert len(result.agent_tasks) >= 1

        # Prioritization: interviewing (2.0 weight) should be top
        assert result.prioritized_apps[0].status == "interviewing"

    @pytest.mark.asyncio
    async def test_planner_generates_all_agent_types(self):
        """The planner should generate tasks for multiple agent types."""
        planner = PlannerAgent()
        apps = [
            ApplicationEntry(
                status="queued", fit_score=80.0,
                jd=JobDescription(title="Eng", company="A"),
            ),
            ApplicationEntry(
                status="ready", fit_score=75.0,
                jd=JobDescription(title="Eng", company="B"),
            ),
            ApplicationEntry(
                status="interviewing", fit_score=90.0,
                jd=JobDescription(title="Eng", company="C"),
            ),
        ]
        result = await planner.plan_week(apps, WeeklyGoal())

        agent_types = {t.agent for t in result.agent_tasks}
        assert "tailor" in agent_types
        assert "pitcher" in agent_types
        assert "coach" in agent_types


# ── 7. Tracker → follow-ups, transitions, timeline ──────────────────────────

class TestTrackerPipeline:

    @pytest.mark.asyncio
    async def test_full_lifecycle_with_tracker(self):
        """Tracker manages an application through the full pipeline with timeline."""
        tracker = TrackerAgent()

        # Create and store an application
        app = ApplicationEntry(
            status="queued", fit_score=85.0,
            jd=JobDescription(title="Backend Eng", company="Stripe"),
        )
        store_application(app)

        # Walk through transitions
        for new_status, reason in [
            ("tailoring", "Started resume tailor"),
            ("ready", "Resume and cover letter ready"),
            ("submitted", "Applied on company portal"),
        ]:
            result = await tracker.transition_status(app.id, new_status, reason)
            assert result.applications_updated == 1

        # Add a note
        event = await tracker.add_note(app.id, "Referred by John Doe")
        assert event.event_type == "note"

        # Check timeline
        timeline = await tracker.get_application_timeline(app.id)
        assert len(timeline) >= 4  # 3 transitions + 1 note
        assert timeline[0].event_type == "status_change"
        assert timeline[-1].event_type == "note"

    @pytest.mark.asyncio
    async def test_email_classification_pipeline(self):
        """Classify a batch of emails and verify signal types."""
        tracker = TrackerAgent()

        test_emails = [
            ("Update on your application", "We have decided to move forward with other candidates.", "rejection"),
            ("Interview invitation", "We'd like to schedule a technical interview.", "interview"),
            ("Application received", "Thank you for applying. We've received your application.", "acknowledgement"),
        ]

        for subject, body, expected_type in test_emails:
            result = await tracker.classify_incoming_email(subject, body)
            signal = result.signals_detected[0]
            assert signal.signal_type == expected_type, (
                f"Expected {expected_type} for '{subject}', got {signal.signal_type}"
            )

    @pytest.mark.asyncio
    async def test_invalid_transition_blocked(self):
        """Tracker should reject invalid status transitions."""
        tracker = TrackerAgent()
        app = ApplicationEntry(status="queued", fit_score=70.0,
                               jd=JobDescription(title="Eng", company="Co"))
        store_application(app)

        result = await tracker.transition_status(app.id, "offer")
        assert result.applications_updated == 0
        assert result.timeline_events[0].event_type == "error"


# ── 8. End-to-end: full user journey ────────────────────────────────────────

class TestFullUserJourney:
    """
    Simulates a complete user workflow:
    Resume upload → JD parse → fit score → tailor → cover letter → coaching → plan.
    """

    @pytest.mark.asyncio
    async def test_complete_workflow(self):
        resume = _resume()
        jd = _jd()

        # Step 1: Scout scores the job
        scout = ScoutAgent()
        scout_result = await scout.score_single_jd(resume, jd.raw_text)
        fit_score = scout_result.jobs[0].fit.total_score
        assert fit_score > 0

        # Step 2: Tailor the resume
        tailor = TailorAgent()
        tailor_result = await tailor.tailor(resume, jd)
        ats_before = tailor_result.score_before.total_score
        ats_after = tailor_result.score_after.total_score
        assert ats_before > 0
        assert ats_after > 0

        # Step 3: Generate a cover letter from the tailored resume
        pitcher = PitcherAgent()
        pitcher_result = await pitcher.generate(
            tailor_result.rewritten_resume, jd,
            writing_samples=["I thrive in fast-paced environments where impact matters."],
        )
        assert pitcher_result.cover_letter.word_count > 50

        # Step 4: Start a coaching session
        coach = CoachAgent()
        coach_result = await coach.start_session(jd, resume)
        session = coach_result.session
        assert len(session.questions) >= 5

        # Answer one question
        q = session.current_question
        grade = await coach.submit_answer(
            session.id,
            "At Google, I led the design of a real-time event pipeline handling 5M events/day. "
            "The challenge was balancing throughput with latency. I chose Kafka with Go consumers "
            "and achieved 40% latency reduction while maintaining 99.7% reliability.",
        )
        assert grade.overall_score > 0

        # Step 5: Track the application through the pipeline
        app = ApplicationEntry(
            status="tailoring",
            fit_score=fit_score,
            ats_score_before=ats_before,
            ats_score_after=ats_after,
            jd=jd,
        )
        store_application(app)

        tracker = TrackerAgent()
        await tracker.transition_status(app.id, "ready", "Tailor + pitch complete")
        await tracker.transition_status(app.id, "submitted", "Applied on portal")
        await tracker.add_note(app.id, "Applied via company careers page")

        timeline = await tracker.get_application_timeline(app.id)
        assert len(timeline) >= 3

        # Step 6: Plan the week with the application in the pipeline
        planner = PlannerAgent()
        plan = await planner.plan_week([app], WeeklyGoal(target_applications=5))

        assert plan.report.summary
        assert len(plan.agent_tasks) >= 1

    @pytest.mark.asyncio
    async def test_poor_fit_still_completes(self):
        """A mismatched resume/JD should still complete the pipeline without errors."""
        resume = Resume(
            contact=ResumeContact(name="Jane Doe", email="jane@example.com"),
            raw_text="Jane Doe\njane@example.com\n\nExperience\nBarista at Coffee Shop\n- Made coffee",
            work_experience=[
                WorkExperience(
                    company="Coffee Shop",
                    title="Barista",
                    start_date=date(2023, 1, 1),
                    bullets=["Made coffee", "Cleaned tables"],
                    technologies=[],
                ),
            ],
            education=[],
            skills={"food_service": ["Espresso", "Latte Art"]},
            seniority_level="entry",
            total_yoe=1.0,
            primary_domain="hospitality",
        )

        jd = _jd()  # Senior backend eng at Stripe

        # Scout: should give low fit
        scout = ScoutAgent()
        scout_result = await scout.score_single_jd(resume, jd.raw_text)
        assert scout_result.jobs[0].fit.total_score < 50

        # Tailor: should still run
        tailor = TailorAgent()
        tailor_result = await tailor.tailor(resume, jd)
        assert tailor_result.score_before.total_score < 50

        # Pitcher: should still generate something
        pitcher = PitcherAgent()
        pitcher_result = await pitcher.generate(resume, jd)
        assert pitcher_result.cover_letter.text

        # Coach: should still generate questions
        coach = CoachAgent()
        coach_result = await coach.start_session(jd, resume)
        assert len(coach_result.session.questions) >= 5


# ── 8. FastAPI route integration ─────────────────────────────────────────────

class TestFastAPIRoutes:
    """Verify the FastAPI app starts and routes respond correctly."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from backend.main import app
        return TestClient(app)

    def test_health_check(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_stats_endpoint(self, client):
        r = client.get("/api/planner/stats")
        assert r.status_code == 200
        data = r.json()
        assert "total_applications" in data
        assert "avg_ats_score" in data

    def test_applications_list(self, client):
        r = client.get("/api/applications/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_planner_history(self, client):
        r = client.get("/api/planner/history")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_trigger_weekly_planner(self, client):
        r = client.post("/api/planner/run-weekly")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "result" in data

    def test_update_invalid_status_rejected(self, client):
        r = client.patch("/api/applications/fake-id", json={"status": "invalid_status"})
        assert r.status_code == 400

    def test_get_nonexistent_app_404(self, client):
        r = client.get("/api/applications/nonexistent-id")
        assert r.status_code == 404

    def test_classify_email_endpoint(self, client):
        r = client.post("/api/tracker/classify-email", json={
            "subject": "Interview invitation",
            "body": "We'd like to schedule an interview with you.",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["signal_type"] == "interview"
        assert data["confidence"] > 0

    def test_check_followups_endpoint(self, client):
        r = client.post("/api/tracker/followups/check", json={
            "candidate_name": "Test User",
            "tone": "warm_professional",
        })
        assert r.status_code == 200
        data = r.json()
        assert "followups_due" in data
        assert "emails" in data

    def test_tracker_nonexistent_timeline_404(self, client):
        r = client.get("/api/tracker/nonexistent-id/timeline")
        assert r.status_code == 404

    def test_analytics_endpoint(self, client):
        r = client.get("/api/analytics")
        assert r.status_code == 200
        data = r.json()
        assert "funnel" in data
        assert "score_trends" in data
        assert "one_sentence_summary" in data

    def test_analytics_funnel_endpoint(self, client):
        r = client.get("/api/analytics/funnel")
        assert r.status_code == 200
        data = r.json()
        assert "jobs_discovered" in data
        assert "conversion_rates" in data

    def test_analytics_heatmap_endpoint(self, client):
        r = client.get("/api/analytics/dimension-heatmap")
        assert r.status_code == 200
        data = r.json()
        assert "dimension_averages" in data
        assert "strongest_dimensions" in data
        assert "weakest_dimensions" in data

    def test_company_profiles_endpoint(self, client):
        r = client.get("/api/company-profiles")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 8
        assert all("hiring_philosophy" in p for p in data)

    def test_salary_ranges_endpoint(self, client):
        r = client.get("/api/salary/ranges")
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 24
        # Each entry should have low and high
        for key, val in data.items():
            assert val["low"] < val["high"]

    def test_salary_locations_endpoint(self, client):
        r = client.get("/api/salary/locations")
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 15
        assert data["san_francisco"] > data["bangalore"]


# ── 9. Full onboarding E2E flow ──────────────────────────────────────────────

class TestOnboardingE2E:
    """Full onboarding wizard: profile → resume → baseline → complete."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from backend.main import app
        return TestClient(app)

    def test_full_onboarding_flow(self, client):
        # Step 1: Create profile
        r = client.post("/api/onboarding/profile", json={
            "name": "Alex Chen",
            "email": "alex@example.com",
            "target_roles": ["software_engineer_backend"],
            "target_seniority": "senior",
            "target_locations": ["san_francisco"],
            "remote_preference": "hybrid",
            "salary_min": 180000,
            "salary_max": 280000,
            "company_size_preference": ["faang"],
            "weekly_goal": 8,
        })
        assert r.status_code == 200
        profile_id = r.json()["profile_id"]

        # Step 2: Upload resume text
        r = client.post("/api/onboarding/resume-text", json={
            "resume_text": (
                "Alex Chen\nalex@example.com\n555-1234\n\n"
                "SUMMARY\n"
                "Senior backend engineer with 8+ years building distributed systems.\n\n"
                "EXPERIENCE\n"
                "Senior Software Engineer at Google\nJan 2020 - Present\n"
                "- Architected event processing pipeline handling 5M events/day\n"
                "- Reduced API latency by 40% through caching redesign\n"
                "- Led team of 8 engineers on payment infrastructure\n\n"
                "Software Engineer at Stripe\nMar 2017 - Dec 2019\n"
                "- Built fraud detection API serving 50K req/sec\n\n"
                "SKILLS\nPython, Go, Kafka, PostgreSQL, Kubernetes, AWS\n\n"
                "EDUCATION\nBS Computer Science, Stanford University, 2017"
            ),
        })
        assert r.status_code == 200
        assert r.json()["resume_id"]
        assert r.json()["seniority_level"]

        # Step 3: Writing samples (optional)
        r = client.post("/api/onboarding/writing-samples", json={
            "samples": [
                "I thrive in fast-paced environments where impact matters."
            ],
        })
        assert r.status_code == 200
        assert r.json()["voice_summary"] is not None

        # Step 4: Baseline score
        r = client.post("/api/onboarding/baseline-score", json={})
        assert r.status_code == 200
        baseline = r.json()
        assert baseline["ats_score"] > 0
        assert baseline["standout_score"] > 0
        assert baseline["combined_score"] > 0

        # Step 5: Complete
        r = client.post("/api/onboarding/complete")
        assert r.status_code == 200
        complete_data = r.json()
        assert complete_data["onboarding_completed"] is True
        assert complete_data["baseline_ats_score"] > 0
        assert complete_data["baseline_standout_score"] > 0
        assert complete_data["baseline_combined_score"] > 0

        # Verify status
        r = client.get("/api/onboarding/status")
        assert r.status_code == 200
        status = r.json()
        assert status["completed"] is True
        assert "profile" in status["steps_done"]
        assert "resume" in status["steps_done"]
        assert "baseline_score" in status["steps_done"]
        assert "complete" in status["steps_done"]


# ── 10. Export endpoints ─────────────────────────────────────────────────────

class TestExportEndpoints:
    """Test the proof artifact export endpoints."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from backend.main import app
        return TestClient(app)

    def test_export_formats(self, client):
        r = client.get("/api/export/formats")
        assert r.status_code == 200
        data = r.json()
        assert "pdf_available" in data
        assert isinstance(data["formats"], list)
        assert "html" in data["formats"]

    def test_export_analytics_report(self, client):
        r = client.post("/api/export/analytics-report")
        assert r.status_code == 200
        assert len(r.content) > 100
        # Should be HTML (weasyprint not available in test env)
        assert b"Land" in r.content
        assert b"Funnel" in r.content
