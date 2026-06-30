"""Unit tests for the Standout Engine: orchestrator, role profiles, seniority matrix."""

from datetime import date

import pytest

from backend.parsers.schemas import (
    Education,
    JobDescription,
    Resume,
    ResumeContact,
    WorkExperience,
)
from backend.agents.tailor.standout.engine import score_standout, StandoutScoreResult
from backend.agents.tailor.standout.role_profiles import (
    STANDOUT_ROLE_PROFILES,
    get_standout_role_profile,
)
from backend.agents.tailor.standout.seniority_matrix import (
    STANDOUT_SENIORITY_MULTIPLIERS,
    apply_standout_seniority_adjustment,
)
from backend.agents.tailor.standout.dimensions import STANDOUT_DIMENSIONS


# ── Test fixtures ─────────────────────────────────────────────────────────────


def _contact() -> ResumeContact:
    return ResumeContact(name="Alex Chen", email="alex@example.com", linkedin="linkedin.com/in/alex")


def _make_resume(**overrides) -> Resume:
    defaults = dict(
        contact=_contact(),
        raw_text="Senior Engineer at Google. Built distributed systems. Patent holder.",
        summary="Backend engineer with 8 years scaling distributed systems to 10M users.",
        work_experience=[
            WorkExperience(
                company="Google",
                title="Senior Engineer",
                start_date=date(2020, 1, 1),
                bullets=[
                    "Built real-time data pipeline processing 5M events/day",
                    "Reduced API latency by 40% through caching redesign",
                    "Led team of 5 engineers on payment infrastructure",
                ],
                technologies=["Go", "Kafka"],
            ),
            WorkExperience(
                company="Startup Inc",
                title="Software Engineer",
                start_date=date(2016, 1, 1),
                end_date=date(2019, 12, 31),
                bullets=[
                    "Designed microservices architecture serving 100K users",
                    "Shipped customer-facing dashboard in 3 sprints",
                ],
                technologies=["Python", "PostgreSQL"],
            ),
        ],
        education=[
            Education(institution="MIT", degree="BS", field="Computer Science"),
        ],
        skills={"languages": ["Python", "Go"], "frameworks": ["FastAPI", "Kafka"]},
        seniority_level="senior",
        total_yoe=8.0,
        primary_domain="backend",
    )
    defaults.update(overrides)
    return Resume(**defaults)


def _make_jd(**overrides) -> JobDescription:
    defaults = dict(
        raw_text="Senior backend engineer for distributed systems",
        title="Senior Backend Engineer",
        company="Stripe",
        required_skills=["Python", "Go"],
        tech_stack=["Python", "Go", "Kafka", "PostgreSQL"],
    )
    defaults.update(overrides)
    return JobDescription(**defaults)


# ── Role Profiles ─────────────────────────────────────────────────────────────


class TestStandoutRoleProfiles:
    @pytest.mark.parametrize("role", list(STANDOUT_ROLE_PROFILES.keys()))
    def test_weights_sum_to_one(self, role):
        weights = STANDOUT_ROLE_PROFILES[role]
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01, f"{role} standout weights sum to {total}"

    @pytest.mark.parametrize("role", list(STANDOUT_ROLE_PROFILES.keys()))
    def test_all_8_dimensions_present(self, role):
        weights = STANDOUT_ROLE_PROFILES[role]
        assert len(weights) == 8, f"{role} has {len(weights)} dimensions, expected 8"

    @pytest.mark.parametrize("role", list(STANDOUT_ROLE_PROFILES.keys()))
    def test_all_dimension_ids_match(self, role):
        weights = STANDOUT_ROLE_PROFILES[role]
        expected_ids = set(STANDOUT_DIMENSIONS.keys())
        assert set(weights.keys()) == expected_ids

    def test_generic_fallback(self):
        profile = get_standout_role_profile("nonexistent_role_type")
        assert len(profile) == 8
        total = sum(profile.values())
        assert abs(total - 1.0) < 0.01

    def test_known_role_returns_correct_profile(self):
        profile = get_standout_role_profile("software_engineer_backend")
        assert profile == STANDOUT_ROLE_PROFILES["software_engineer_backend"]

    def test_research_scientist_weights_credibility_high(self):
        profile = get_standout_role_profile("research_scientist")
        assert profile["credibility_anchors"] >= 0.20

    def test_product_manager_weights_outcomes_high(self):
        profile = get_standout_role_profile("product_manager")
        assert profile["outcome_density"] >= 0.15


# ── Seniority Matrix ─────────────────────────────────────────────────────────


class TestStandoutSeniorityMatrix:
    @pytest.mark.parametrize("seniority", list(STANDOUT_SENIORITY_MULTIPLIERS.keys()))
    def test_all_8_multipliers_present(self, seniority):
        multipliers = STANDOUT_SENIORITY_MULTIPLIERS[seniority]
        assert len(multipliers) == 8

    @pytest.mark.parametrize("seniority", list(STANDOUT_SENIORITY_MULTIPLIERS.keys()))
    def test_all_dimension_ids_match(self, seniority):
        multipliers = STANDOUT_SENIORITY_MULTIPLIERS[seniority]
        expected_ids = set(STANDOUT_DIMENSIONS.keys())
        assert set(multipliers.keys()) == expected_ids

    @pytest.mark.parametrize("seniority", list(STANDOUT_SENIORITY_MULTIPLIERS.keys()))
    def test_adjusted_weights_sum_to_one(self, seniority):
        base = get_standout_role_profile("software_engineer_backend")
        adjusted = apply_standout_seniority_adjustment(base, seniority)
        total = sum(adjusted.values())
        assert abs(total - 1.0) < 0.001, f"{seniority} adjusted standout weights sum to {total}"

    def test_mid_level_is_identity(self):
        base = get_standout_role_profile("software_engineer_backend")
        adjusted = apply_standout_seniority_adjustment(base, "mid")
        for k in base:
            assert abs(base[k] - adjusted[k]) < 0.001

    def test_intern_boosts_uniqueness(self):
        base = get_standout_role_profile("software_engineer_backend")
        adjusted_intern = apply_standout_seniority_adjustment(base, "intern")
        adjusted_senior = apply_standout_seniority_adjustment(base, "senior")
        assert adjusted_intern["uniqueness_index"] > adjusted_senior["uniqueness_index"]

    def test_senior_boosts_spike_factor(self):
        base = get_standout_role_profile("software_engineer_backend")
        adjusted_senior = apply_standout_seniority_adjustment(base, "senior")
        adjusted_mid = apply_standout_seniority_adjustment(base, "mid")
        assert adjusted_senior["spike_factor"] > adjusted_mid["spike_factor"]

    def test_executive_heavily_weights_outcomes(self):
        base = get_standout_role_profile("software_engineer_backend")
        adjusted = apply_standout_seniority_adjustment(base, "executive")
        # outcome_density should be one of the heaviest
        top_3 = sorted(adjusted.items(), key=lambda x: x[1], reverse=True)[:3]
        top_3_keys = [k for k, v in top_3]
        assert "outcome_density" in top_3_keys


class TestCrossRoleSeniority:
    """Ensure all role x seniority combinations produce valid normalized weights."""

    @pytest.mark.parametrize("role", list(STANDOUT_ROLE_PROFILES.keys()))
    @pytest.mark.parametrize("seniority", list(STANDOUT_SENIORITY_MULTIPLIERS.keys()))
    def test_all_combinations_normalize(self, role, seniority):
        base = get_standout_role_profile(role)
        adjusted = apply_standout_seniority_adjustment(base, seniority)
        total = sum(adjusted.values())
        assert abs(total - 1.0) < 0.001
        assert all(v >= 0 for v in adjusted.values())


# ── Engine Orchestrator ───────────────────────────────────────────────────────


class TestStandoutEngine:
    @pytest.mark.asyncio
    async def test_score_standout_returns_result(self):
        result = await score_standout(_make_resume(), _make_jd())
        assert isinstance(result, StandoutScoreResult)

    @pytest.mark.asyncio
    async def test_result_has_8_dimension_scores(self):
        result = await score_standout(_make_resume(), _make_jd())
        assert len(result.dimension_scores) == 8

    @pytest.mark.asyncio
    async def test_result_total_score_in_range(self):
        result = await score_standout(_make_resume(), _make_jd())
        assert 0 <= result.total_score <= 100

    @pytest.mark.asyncio
    async def test_result_has_letter_grade(self):
        result = await score_standout(_make_resume(), _make_jd())
        assert result.letter_grade in {
            "A+", "A", "A-", "B+", "B", "B-",
            "C+", "C", "C-", "D", "F",
        }

    @pytest.mark.asyncio
    async def test_result_has_top_3_wins(self):
        result = await score_standout(_make_resume(), _make_jd())
        assert len(result.top_3_wins) <= 3
        assert all(isinstance(w, str) for w in result.top_3_wins)

    @pytest.mark.asyncio
    async def test_result_has_role_type(self):
        result = await score_standout(_make_resume(), _make_jd())
        assert result.role_type == "software_engineer_backend"

    @pytest.mark.asyncio
    async def test_result_has_seniority_level(self):
        result = await score_standout(_make_resume(), _make_jd())
        assert result.seniority_level == "senior"

    @pytest.mark.asyncio
    async def test_weights_sum_to_one(self):
        result = await score_standout(_make_resume(), _make_jd())
        total = sum(result.weights_used.values())
        assert abs(total - 1.0) < 0.001

    @pytest.mark.asyncio
    async def test_weighted_scores_sum_to_total(self):
        result = await score_standout(_make_resume(), _make_jd())
        computed_total = sum(d.weighted_score for d in result.dimension_scores)
        assert abs(computed_total - result.total_score) < 0.5

    @pytest.mark.asyncio
    async def test_each_dimension_has_priority(self):
        result = await score_standout(_make_resume(), _make_jd())
        for d in result.dimension_scores:
            assert d.priority in {"critical", "high", "medium", "low"}

    @pytest.mark.asyncio
    async def test_amplification_tips_populated(self):
        result = await score_standout(_make_resume(), _make_jd())
        assert isinstance(result.amplification_tips, list)

    @pytest.mark.asyncio
    async def test_spike_detected_flag(self):
        # Strong resume with spikes
        result = await score_standout(_make_resume(), _make_jd())
        assert isinstance(result.spike_detected, bool)

    @pytest.mark.asyncio
    async def test_custom_role_type_override(self):
        result = await score_standout(
            _make_resume(), _make_jd(), role_type="product_manager"
        )
        assert result.role_type == "product_manager"

    @pytest.mark.asyncio
    async def test_custom_seniority_override(self):
        result = await score_standout(
            _make_resume(), _make_jd(), seniority="junior"
        )
        assert result.seniority_level == "junior"

    @pytest.mark.asyncio
    async def test_dimension_scores_sorted_by_impact(self):
        result = await score_standout(_make_resume(), _make_jd())
        # Sorted descending by weight * (100 - raw_score)
        impacts = [d.weight * (100 - d.raw_score) for d in result.dimension_scores]
        assert impacts == sorted(impacts, reverse=True)

    @pytest.mark.asyncio
    async def test_all_dimension_ids_are_valid(self):
        result = await score_standout(_make_resume(), _make_jd())
        valid_ids = set(STANDOUT_DIMENSIONS.keys())
        for d in result.dimension_scores:
            assert d.dimension_id in valid_ids
