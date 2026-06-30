"""Unit tests for the Proof Exporter (HTML/PDF report generation)."""

from __future__ import annotations

from datetime import date

import pytest

from backend.parsers.schemas import (
    Education,
    JobDescription,
    Resume,
    ResumeContact,
    WorkExperience,
)
from backend.utils.proof_exporter import (
    generate_score_report,
    generate_diff_report,
    generate_coaching_report,
    generate_analytics_report,
    is_pdf_available,
)
from backend.agents.tailor.standout.engine import StandoutScoreResult, StandoutDimensionScore
from backend.agents.tailor.weightage.scorer_engine import ATSScoreResult, DimensionScore
from backend.agents.tailor.prediction.interview_predictor import CallbackPrediction


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_dim(dim_id: str, name: str, raw: float, weight: float = 0.07, priority: str = "medium"):
    return DimensionScore(
        dimension_id=dim_id, dimension_name=name, raw_score=raw,
        weighted_score=raw * weight, weight=weight, explanation=f"Score: {raw}",
        issues=[f"Issue for {name}"] if raw < 60 else [],
        suggestions=[f"Improve {name}"] if raw < 70 else [], priority=priority,
    )


def _make_standout_dim(dim_id: str, name: str, raw: float, weight: float = 0.12, priority: str = "medium"):
    return StandoutDimensionScore(
        dimension_id=dim_id, dimension_name=name, raw_score=raw,
        weighted_score=raw * weight, weight=weight, explanation=f"Score: {raw}",
        issues=[], suggestions=[], priority=priority,
    )


def _make_dual_result(ats_score: float = 72, standout_score: float = 60):
    ats_dims = [
        _make_dim(f"ats_{i}", f"ATS Dim {i}", ats_score + i - 7)
        for i in range(14)
    ]
    standout_dims = [
        _make_standout_dim(f"std_{i}", f"Standout Dim {i}", standout_score + i - 4)
        for i in range(8)
    ]

    ats = ATSScoreResult(
        total_score=ats_score, letter_grade="B", dimension_scores=ats_dims,
        top_3_issues=["Low keyword density", "Weak bullets"],
        top_3_wins=["Strong tech stack", "Good experience"],
        predicted_ats_pass=True, role_type="software_engineer_backend",
        seniority_level="senior", weights_used={},
    )
    standout = StandoutScoreResult(
        total_score=standout_score, letter_grade="C+", dimension_scores=standout_dims,
        top_3_issues=["No spikes"], top_3_wins=["Good trajectory"],
        spike_detected=False, role_type="software_engineer_backend",
        seniority_level="senior", weights_used={}, amplification_tips=[],
    )
    callback = CallbackPrediction(
        probability=0.35, confidence_interval=(0.25, 0.45),
        confidence_level="medium", top_positive_factors=["Strong tech"],
        top_negative_factors=["Low density"], vs_average_applicant=80.0,
        score_needed_for_50pct=75.0, fixes_for_10pct_boost=["Add metrics"],
        role_type="software_engineer_backend", seniority_level="senior",
        combined_score=67.2, base_rate=0.085,
    )

    class DualMock:
        pass

    dual = DualMock()
    dual.ats = ats
    dual.standout = standout
    dual.combined_score = round(ats_score * 0.6 + standout_score * 0.4, 1)
    dual.combined_grade = "B-"
    dual.callback_prediction = callback
    dual.total_dimensions = 22
    dual.summary = "ATS-safe but needs stronger differentiators"
    return dual


def _make_resume():
    return Resume(
        contact=ResumeContact(name="Alex Chen", email="alex@example.com"),
        raw_text="Senior Engineer at Google.",
        summary="Senior backend engineer with 8 years.",
        work_experience=[WorkExperience(
            company="Google", title="Senior Engineer",
            start_date=date(2020, 1, 1),
            bullets=["Built pipeline handling 5M events/day"],
            technologies=["Go", "Kafka"],
        )],
        education=[Education(institution="Stanford", degree="BS", field="CS")],
        skills={"languages": ["Python", "Go"]},
        seniority_level="senior", total_yoe=8.0,
    )


def _make_jd():
    return JobDescription(
        raw_text="Senior Backend Engineer at Stripe",
        title="Senior Backend Engineer", company="Stripe",
        required_skills=["Python", "Go"],
        tech_stack=["Python", "Go", "Kafka"],
    )


def _make_salary():
    from backend.agents.scout.salary_intel import SalaryEstimate
    return SalaryEstimate(
        role_type="software_engineer_backend", seniority="senior",
        location="san_francisco", company="Stripe",
        estimated_range=(200_000, 340_000), estimated_midpoint=270_000,
        user_position_in_range="above_mid", user_estimated_value=295_000,
        premium_factors=["Tier 1 experience (Google): +15%", "Rust, Go skills: +13%"],
        discount_factors=[],
        negotiation_leverage=["Your spike is rare at this level"],
        negotiation_talking_points=["Reference: 5M events/day pipeline"],
        confidence="medium", confidence_reason="Known company and location",
    )


# ── Score Report tests ───────────────────────────────────────────────────────


class TestScoreReport:
    def test_returns_non_empty(self):
        content, ctype = generate_score_report(_make_dual_result(), _make_resume(), _make_jd())
        assert len(content) > 100

    def test_content_type_is_html_or_pdf(self):
        _, ctype = generate_score_report(_make_dual_result(), _make_resume(), _make_jd())
        assert ctype in ("text/html", "application/pdf")

    def test_contains_candidate_name(self):
        content, _ = generate_score_report(_make_dual_result(), _make_resume(), _make_jd())
        text = content.decode("utf-8") if isinstance(content, bytes) else content
        assert "Alex Chen" in text

    def test_contains_land_it_branding(self):
        content, _ = generate_score_report(_make_dual_result(), _make_resume(), _make_jd())
        text = content.decode("utf-8") if isinstance(content, bytes) else content
        assert "Land" in text and "It" in text

    def test_contains_all_22_dimension_rows(self):
        content, _ = generate_score_report(_make_dual_result(), _make_resume(), _make_jd())
        text = content.decode("utf-8") if isinstance(content, bytes) else content
        # 14 ATS dims + 8 standout dims = 22 rows
        assert text.count("<tr>") >= 22

    def test_contains_ats_score(self):
        content, _ = generate_score_report(_make_dual_result(ats_score=72), _make_resume(), _make_jd())
        text = content.decode("utf-8") if isinstance(content, bytes) else content
        assert "72" in text

    def test_contains_callback_probability(self):
        content, _ = generate_score_report(_make_dual_result(), _make_resume(), _make_jd())
        text = content.decode("utf-8") if isinstance(content, bytes) else content
        assert "35%" in text or "Callback" in text

    def test_with_salary_includes_salary_section(self):
        content, _ = generate_score_report(
            _make_dual_result(), _make_resume(), _make_jd(), salary=_make_salary()
        )
        text = content.decode("utf-8") if isinstance(content, bytes) else content
        assert "Salary" in text
        assert "295,000" in text or "$295" in text

    def test_without_salary_omits_salary_section(self):
        content, _ = generate_score_report(_make_dual_result(), _make_resume(), _make_jd())
        text = content.decode("utf-8") if isinstance(content, bytes) else content
        assert "Salary Intelligence" not in text

    def test_contains_strengths_and_improvements(self):
        content, _ = generate_score_report(_make_dual_result(), _make_resume(), _make_jd())
        text = content.decode("utf-8") if isinstance(content, bytes) else content
        assert "Strengths" in text
        assert "Improve" in text


# ── Diff Report tests ────────────────────────────────────────────────────────


class TestDiffReport:
    def test_returns_non_empty(self):
        content, ctype = generate_diff_report(
            "Original resume text", "Tailored resume text",
            [{"section": "summary", "original": "Old summary", "rewritten": "New summary",
              "reason": "Better keywords", "requires_verification": False}],
            score_before=55.0, score_after=72.0,
        )
        assert len(content) > 100

    def test_contains_before_after_scores(self):
        content, _ = generate_diff_report(
            "Original", "Tailored",
            [{"section": "skills", "original": "Python", "rewritten": "Python, Go",
              "reason": "Added Go", "requires_verification": False}],
            score_before=55, score_after=72,
        )
        text = content.decode("utf-8") if isinstance(content, bytes) else content
        assert "55" in text
        assert "72" in text

    def test_contains_change_log_entries(self):
        changes = [
            {"section": "summary", "original": "Old", "rewritten": "New",
             "reason": "Better", "requires_verification": False},
            {"section": "experience", "original": "Did stuff", "rewritten": "Built APIs",
             "reason": "Verb upgrade", "requires_verification": True},
        ]
        content, _ = generate_diff_report("O", "T", changes, 50, 70)
        text = content.decode("utf-8") if isinstance(content, bytes) else content
        assert "2 changes" in text
        assert "VERIFY" in text  # verification badge

    def test_verification_highlighted(self):
        changes = [
            {"section": "summary", "original": "X", "rewritten": "Y",
             "reason": "R", "requires_verification": True},
        ]
        content, _ = generate_diff_report("O", "T", changes, 50, 65)
        text = content.decode("utf-8") if isinstance(content, bytes) else content
        assert "VERIFY" in text


# ── Coaching Report tests ────────────────────────────────────────────────────


class TestCoachingReport:
    def _session_data(self):
        return {
            "session_id": "abc123",
            "score_pct": 72.5,
            "grade_letter": "B",
            "questions_answered": 5,
            "questions_skipped": 1,
            "total_questions": 6,
            "strongest_dimension": "Technical Depth",
            "weakest_dimension": "Communication",
            "all_strengths": ["Good STAR structure", "Specific metrics"],
            "all_improvements": ["Be more concise", "Add more context"],
            "duration_seconds": 1200,
            "results": [
                {"question_text": "Tell me about a challenge", "score": 80,
                 "strengths": ["Good example"], "improvements": ["Be shorter"]},
                {"question_text": "Design a system", "score": 65,
                 "strengths": ["Clear thinking"], "improvements": ["Mention tradeoffs"]},
            ],
        }

    def test_returns_non_empty(self):
        content, _ = generate_coaching_report(self._session_data())
        assert len(content) > 100

    def test_contains_session_score(self):
        content, _ = generate_coaching_report(self._session_data())
        text = content.decode("utf-8") if isinstance(content, bytes) else content
        assert "72" in text or "73" in text  # score_pct rounded

    def test_contains_per_question_grades(self):
        content, _ = generate_coaching_report(self._session_data())
        text = content.decode("utf-8") if isinstance(content, bytes) else content
        assert "Tell me about a challenge" in text
        assert "Design a system" in text

    def test_answer_text_not_included(self):
        """Privacy: actual answer text should NOT be in the report."""
        data = self._session_data()
        data["results"][0]["answer_text"] = "SECRET_ANSWER_CONTENT"
        content, _ = generate_coaching_report(data)
        text = content.decode("utf-8") if isinstance(content, bytes) else content
        assert "SECRET_ANSWER_CONTENT" not in text

    def test_contains_recommendations(self):
        content, _ = generate_coaching_report(self._session_data())
        text = content.decode("utf-8") if isinstance(content, bytes) else content
        assert "Recommendations" in text

    def test_contains_branding(self):
        content, _ = generate_coaching_report(self._session_data())
        text = content.decode("utf-8") if isinstance(content, bytes) else content
        assert "Land" in text


# ── Analytics Report tests ───────────────────────────────────────────────────


class TestAnalyticsReport:
    def _make_analytics(self):
        from backend.agents.planner.analytics import compute_analytics
        apps = [
            {"status": "submitted", "jd": {"company": "A", "title": "Eng"},
             "created_at": "2026-05-01T10:00:00", "applied_at": "2026-05-02T10:00:00",
             "last_activity": "2026-05-10T10:00:00", "fit_score": 75,
             "ats_score_before": 60, "ats_score_after": 72},
            {"status": "interviewing", "jd": {"company": "B", "title": "Eng"},
             "created_at": "2026-05-01T10:00:00", "applied_at": "2026-05-03T10:00:00",
             "last_activity": "2026-05-15T10:00:00", "fit_score": 80,
             "ats_score_before": 65, "ats_score_after": 78},
            {"status": "rejected", "jd": {"company": "C", "title": "Eng"},
             "created_at": "2026-05-01T10:00:00", "applied_at": "2026-05-04T10:00:00",
             "last_activity": "2026-05-12T10:00:00", "fit_score": 50,
             "ats_score_before": 45, "ats_score_after": 55},
        ]
        return compute_analytics(apps)

    def test_returns_non_empty(self):
        content, _ = generate_analytics_report(self._make_analytics())
        assert len(content) > 100

    def test_contains_funnel_data(self):
        content, _ = generate_analytics_report(self._make_analytics())
        text = content.decode("utf-8") if isinstance(content, bytes) else content
        assert "Funnel" in text
        assert "Applied" in text

    def test_contains_predictions(self):
        content, _ = generate_analytics_report(self._make_analytics())
        text = content.decode("utf-8") if isinstance(content, bytes) else content
        assert "Prediction" in text

    def test_contains_branding(self):
        content, _ = generate_analytics_report(self._make_analytics())
        text = content.decode("utf-8") if isinstance(content, bytes) else content
        assert "Land" in text

    def test_contains_action_items(self):
        content, _ = generate_analytics_report(self._make_analytics())
        text = content.decode("utf-8") if isinstance(content, bytes) else content
        assert "Action" in text


# ── PDF availability check ───────────────────────────────────────────────────


class TestPDFAvailability:
    def test_is_pdf_available_returns_bool(self):
        result = is_pdf_available()
        assert isinstance(result, bool)
