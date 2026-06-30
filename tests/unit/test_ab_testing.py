"""Unit tests for the Resume A/B Testing Engine."""

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
from backend.agents.tailor.ab_testing import (
    ab_test_resumes,
    ABTestResult,
    _compare_dimensions,
    _generate_section_merge_suggestions,
    DimensionComparison,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _strong_resume() -> Resume:
    return Resume(
        contact=ResumeContact(name="Alex Chen", email="alex@example.com", linkedin="linkedin.com/in/alex"),
        raw_text=(
            "Senior Engineer at Google. Built distributed systems. Stanford CS.\n"
            "Architected event pipeline handling 5M users. Reduced latency by 40%."
        ),
        summary="Senior backend engineer with 8 years scaling distributed systems to 5M users.",
        work_experience=[
            WorkExperience(
                company="Google", title="Senior Software Engineer",
                start_date=date(2020, 1, 1),
                bullets=[
                    "Architected event processing pipeline handling 5M users",
                    "Reduced API latency by 40% through caching redesign",
                    "Led team of 8 engineers on payment infrastructure",
                ],
                technologies=["Go", "Kafka", "Python"],
            ),
            WorkExperience(
                company="Stripe", title="Software Engineer",
                start_date=date(2017, 1, 1), end_date=date(2019, 12, 31),
                bullets=["Built fraud detection API serving 50K req/sec", "Reduced infra costs by $2.1M/year"],
                technologies=["Python", "Redis"],
            ),
        ],
        education=[Education(institution="Stanford University", degree="BS", field="Computer Science")],
        skills={"languages": ["Python", "Go"], "infra": ["Kafka", "Kubernetes"]},
        seniority_level="senior", total_yoe=8.0, primary_domain="backend",
    )


def _weak_resume() -> Resume:
    return Resume(
        contact=ResumeContact(name="Bob Smith", email="bob@example.com"),
        raw_text="Software developer with 3 years experience. Worked on web apps.",
        summary="Passionate developer seeking challenging opportunities.",
        work_experience=[
            WorkExperience(
                company="Smallco Inc", title="Software Developer",
                start_date=date(2021, 1, 1),
                bullets=["Maintained legacy codebase", "Assisted with bug fixes", "Participated in code reviews"],
                technologies=["JavaScript"],
            ),
        ],
        education=[Education(institution="State University", degree="BS", field="IT")],
        skills={"languages": ["JavaScript", "HTML"]},
        seniority_level="junior", total_yoe=3.0, primary_domain="general",
    )


def _make_jd() -> JobDescription:
    return JobDescription(
        raw_text="Senior Backend Engineer at Stripe",
        title="Senior Backend Engineer", company="Stripe",
        required_skills=["Python", "Go"],
        tech_stack=["Python", "Go", "Kafka", "PostgreSQL"],
    )


# ── Core A/B test ─────────────────────────────────────────────────────────────


class TestABTestResumes:
    @pytest.mark.asyncio
    async def test_returns_ab_test_result(self):
        result = await ab_test_resumes(_strong_resume(), _weak_resume(), _make_jd())
        assert isinstance(result, ABTestResult)

    @pytest.mark.asyncio
    async def test_strong_vs_weak_a_wins(self):
        result = await ab_test_resumes(_strong_resume(), _weak_resume(), _make_jd())
        assert result.overall_winner == "A"
        assert result.version_a_combined > result.version_b_combined
        assert result.win_margin > 0

    @pytest.mark.asyncio
    async def test_same_resume_is_tie(self):
        resume = _strong_resume()
        result = await ab_test_resumes(resume, resume, _make_jd())
        assert result.overall_winner == "tie"

    @pytest.mark.asyncio
    async def test_has_22_dimension_comparisons(self):
        result = await ab_test_resumes(_strong_resume(), _weak_resume(), _make_jd())
        assert len(result.dimension_comparisons) == 22

    @pytest.mark.asyncio
    async def test_a_advantages_only_gt_5_delta(self):
        result = await ab_test_resumes(_strong_resume(), _weak_resume(), _make_jd())
        for adv in result.a_advantages:
            comp = next(c for c in result.dimension_comparisons if c.dimension_name == adv)
            assert comp.delta > 5

    @pytest.mark.asyncio
    async def test_b_advantages_only_gt_5_delta(self):
        result = await ab_test_resumes(_strong_resume(), _weak_resume(), _make_jd())
        for adv in result.b_advantages:
            comp = next(c for c in result.dimension_comparisons if c.dimension_name == adv)
            assert comp.delta > 5

    @pytest.mark.asyncio
    async def test_merge_suggestions_cover_key_sections(self):
        result = await ab_test_resumes(_strong_resume(), _weak_resume(), _make_jd())
        sections = {m.section for m in result.merge_suggestions}
        assert "summary" in sections
        assert "work_experience" in sections
        assert "skills" in sections

    @pytest.mark.asyncio
    async def test_recommendation_non_empty(self):
        result = await ab_test_resumes(_strong_resume(), _weak_resume(), _make_jd())
        assert len(result.recommendation) > 10
        assert "Version A" in result.recommendation or "Version B" in result.recommendation

    @pytest.mark.asyncio
    async def test_callback_probabilities_populated(self):
        result = await ab_test_resumes(_strong_resume(), _weak_resume(), _make_jd())
        assert 0 <= result.version_a_callback <= 0.85
        assert 0 <= result.version_b_callback <= 0.85
        assert result.version_a_callback > result.version_b_callback

    @pytest.mark.asyncio
    async def test_tie_threshold_2_points(self):
        """Identical resumes → combined diff is 0 → tie."""
        resume = _strong_resume()
        result = await ab_test_resumes(resume, resume, _make_jd())
        assert result.overall_winner == "tie"
        assert result.version_a_combined == result.version_b_combined

    @pytest.mark.asyncio
    async def test_ids_populated(self):
        result = await ab_test_resumes(_strong_resume(), _weak_resume(), _make_jd())
        assert result.version_a_id
        assert result.version_b_id
        assert result.jd_id

    @pytest.mark.asyncio
    async def test_role_type_populated(self):
        result = await ab_test_resumes(_strong_resume(), _weak_resume(), _make_jd())
        assert result.role_type
        assert result.seniority_level

    @pytest.mark.asyncio
    async def test_combined_is_weighted_blend(self):
        result = await ab_test_resumes(_strong_resume(), _weak_resume(), _make_jd())
        expected_a = round(result.version_a_ats * 0.6 + result.version_a_standout * 0.4, 1)
        assert abs(result.version_a_combined - expected_a) < 0.5

    @pytest.mark.asyncio
    async def test_company_profile_affects_both(self):
        """Scoring against Stripe JD should apply Stripe company profile to both."""
        jd = _make_jd()
        result = await ab_test_resumes(_strong_resume(), _weak_resume(), jd)
        # Just verify it runs — company profiles are tested separately
        assert result.version_a_ats > 0
        assert result.version_b_ats > 0


# ── Dimension comparison helper ───────────────────────────────────────────────


class TestCompareDimensions:
    def test_tie_within_3_points(self):
        from backend.agents.tailor.weightage.scorer_engine import DimensionScore

        dims_a = [DimensionScore(
            dimension_id="test", dimension_name="Test",
            raw_score=70.0, weighted_score=7.0, weight=0.1,
            explanation="", issues=[], suggestions=[], priority="medium",
        )]
        dims_b = [DimensionScore(
            dimension_id="test", dimension_name="Test",
            raw_score=72.0, weighted_score=7.2, weight=0.1,
            explanation="", issues=[], suggestions=[], priority="medium",
        )]
        comps = _compare_dimensions(dims_a, dims_b)
        assert comps[0].winner == "tie"

    def test_b_wins_above_3_points(self):
        from backend.agents.tailor.weightage.scorer_engine import DimensionScore

        dims_a = [DimensionScore(
            dimension_id="test", dimension_name="Test",
            raw_score=50.0, weighted_score=5.0, weight=0.1,
            explanation="", issues=[], suggestions=[], priority="medium",
        )]
        dims_b = [DimensionScore(
            dimension_id="test", dimension_name="Test",
            raw_score=80.0, weighted_score=8.0, weight=0.1,
            explanation="", issues=[], suggestions=[], priority="medium",
        )]
        comps = _compare_dimensions(dims_a, dims_b)
        assert comps[0].winner == "B"
        assert comps[0].delta == 30.0

    def test_sorted_by_weighted_impact(self):
        from backend.agents.tailor.weightage.scorer_engine import DimensionScore

        dims_a = [
            DimensionScore(dimension_id="low", dimension_name="Low", raw_score=50,
                           weighted_score=0.5, weight=0.01, explanation="",
                           issues=[], suggestions=[], priority="low"),
            DimensionScore(dimension_id="high", dimension_name="High", raw_score=50,
                           weighted_score=5.0, weight=0.15, explanation="",
                           issues=[], suggestions=[], priority="high"),
        ]
        dims_b = [
            DimensionScore(dimension_id="low", dimension_name="Low", raw_score=80,
                           weighted_score=0.8, weight=0.01, explanation="",
                           issues=[], suggestions=[], priority="low"),
            DimensionScore(dimension_id="high", dimension_name="High", raw_score=80,
                           weighted_score=12.0, weight=0.15, explanation="",
                           issues=[], suggestions=[], priority="high"),
        ]
        comps = _compare_dimensions(dims_a, dims_b)
        assert comps[0].dimension_id == "high"


# ── Section merge suggestion tests ───────────────────────────────────────────


class TestSectionMergeSuggestions:
    def test_covers_4_sections(self):
        comps = [DimensionComparison(
            dimension_id="first_impression", dimension_name="First Impression",
            score_a=80, score_b=50, delta=30, winner="A",
            weight=0.1, weighted_impact=3.0,
        )]
        suggestions = _generate_section_merge_suggestions(comps)
        sections = {s.section for s in suggestions}
        assert {"summary", "work_experience", "skills", "education"} == sections

    def test_valid_recommendations(self):
        comps = []
        suggestions = _generate_section_merge_suggestions(comps)
        for s in suggestions:
            assert s.recommendation in {"use_a", "use_b", "combine", "either"}

    def test_each_suggestion_has_reason(self):
        comps = []
        suggestions = _generate_section_merge_suggestions(comps)
        for s in suggestions:
            assert len(s.reason) > 0
