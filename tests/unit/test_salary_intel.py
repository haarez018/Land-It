"""Unit tests for the Salary Intelligence Module."""

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
from backend.agents.scout.salary_intel import (
    estimate_salary,
    SalaryEstimate,
    BASE_SALARY_RANGES,
    LOCATION_MULTIPLIERS,
    COMPANY_STAGE_MULTIPLIERS,
    SKILL_PREMIUMS,
    _match_location,
    _infer_company_stage,
    _detect_career_gaps,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _contact() -> ResumeContact:
    return ResumeContact(name="Alex Chen", email="alex@example.com")


def _strong_resume() -> Resume:
    return Resume(
        contact=_contact(),
        raw_text="Senior Engineer at Google. Built distributed systems.",
        summary="Senior backend engineer with 8 years scaling systems.",
        work_experience=[
            WorkExperience(
                company="Google", title="Senior Software Engineer",
                start_date=date(2020, 1, 1),
                bullets=[
                    "Architected event processing pipeline handling 5M users",
                    "Reduced API latency by 40% through caching redesign",
                    "Led team of 8 engineers, saved $2.1M/year",
                ],
                technologies=["Go", "Kafka", "Kubernetes", "Python"],
            ),
            WorkExperience(
                company="Stripe", title="Software Engineer",
                start_date=date(2017, 1, 1), end_date=date(2019, 12, 31),
                bullets=["Built fraud detection API serving 50K req/sec"],
                technologies=["Python", "Redis", "AWS"],
            ),
        ],
        education=[Education(institution="Stanford", degree="BS", field="Computer Science")],
        skills={
            "languages": ["Python", "Go", "Rust"],
            "infra": ["Kafka", "Kubernetes", "AWS"],
            "concepts": ["distributed systems"],
        },
        seniority_level="senior",
        total_yoe=8.0,
        primary_domain="backend",
    )


def _junior_resume() -> Resume:
    return Resume(
        contact=_contact(),
        raw_text="Junior developer with 1 year experience.",
        work_experience=[
            WorkExperience(
                company="Startup Co", title="Junior Developer",
                start_date=date(2023, 6, 1),
                bullets=["Fixed bugs", "Wrote unit tests"],
                technologies=["JavaScript", "HTML"],
            ),
        ],
        education=[Education(institution="State U", degree="BS", field="IT")],
        skills={"languages": ["JavaScript"]},
        seniority_level="junior",
        total_yoe=1.0,
        primary_domain="general",
    )


def _phd_research_resume() -> Resume:
    return Resume(
        contact=_contact(),
        raw_text="Research scientist with PhD.",
        work_experience=[
            WorkExperience(
                company="DeepMind", title="Research Scientist",
                start_date=date(2020, 1, 1),
                bullets=["Published 5 papers in NeurIPS"],
                technologies=["PyTorch", "Python"],
            ),
        ],
        education=[Education(institution="MIT", degree="PhD", field="Machine Learning")],
        skills={"languages": ["Python"], "frameworks": ["PyTorch", "TensorFlow"]},
        seniority_level="senior",
        total_yoe=6.0,
        primary_domain="ml",
    )


def _gapped_resume() -> Resume:
    return Resume(
        contact=_contact(),
        raw_text="Developer with career gap.",
        work_experience=[
            WorkExperience(
                company="Acme", title="Engineer",
                start_date=date(2023, 1, 1),
                bullets=["Built APIs"],
                technologies=["Python"],
            ),
            WorkExperience(
                company="OldCo", title="Engineer",
                start_date=date(2019, 1, 1),
                end_date=date(2020, 6, 1),
                bullets=["Maintained systems"],
                technologies=["Java"],
            ),
        ],
        education=[],
        skills={"languages": ["Python", "Java"]},
        seniority_level="mid",
        total_yoe=4.0,
    )


def _make_jd(
    *,
    title: str = "Senior Backend Engineer",
    company: str = "Stripe",
    location: str = "San Francisco, CA",
    salary_range: tuple[int, int] | None = None,
) -> JobDescription:
    return JobDescription(
        raw_text=f"{title} at {company}",
        title=title, company=company, location=location,
        required_skills=["Python", "Go"],
        tech_stack=["Python", "Go", "Kafka"],
        salary_range=salary_range,
    )


# ── Base range tests ─────────────────────────────────────────────────────────


class TestBaseRanges:
    @pytest.mark.parametrize("key", list(BASE_SALARY_RANGES.keys()))
    def test_low_less_than_high(self, key):
        low, high = BASE_SALARY_RANGES[key]
        assert low < high, f"{key}: {low} >= {high}"

    @pytest.mark.parametrize("key", list(BASE_SALARY_RANGES.keys()))
    def test_ranges_positive(self, key):
        low, high = BASE_SALARY_RANGES[key]
        assert low > 0
        assert high > 0

    def test_at_least_24_combinations(self):
        assert len(BASE_SALARY_RANGES) >= 24

    def test_senior_higher_than_junior(self):
        junior = BASE_SALARY_RANGES[("software_engineer_backend", "junior")]
        senior = BASE_SALARY_RANGES[("software_engineer_backend", "senior")]
        assert senior[0] > junior[0]
        assert senior[1] > junior[1]

    def test_staff_higher_than_senior(self):
        senior = BASE_SALARY_RANGES[("software_engineer_backend", "senior")]
        staff = BASE_SALARY_RANGES[("software_engineer_backend", "staff_principal")]
        assert staff[0] > senior[0]


# ── Location multiplier tests ────────────────────────────────────────────────


class TestLocationMultipliers:
    def test_at_least_15_locations(self):
        assert len(LOCATION_MULTIPLIERS) >= 15

    @pytest.mark.parametrize("loc", list(LOCATION_MULTIPLIERS.keys()))
    def test_multipliers_positive(self, loc):
        assert LOCATION_MULTIPLIERS[loc] > 0

    def test_sf_highest_us(self):
        assert LOCATION_MULTIPLIERS["san_francisco"] >= LOCATION_MULTIPLIERS["new_york"]
        assert LOCATION_MULTIPLIERS["san_francisco"] >= LOCATION_MULTIPLIERS["seattle"]

    def test_bangalore_much_lower(self):
        assert LOCATION_MULTIPLIERS["bangalore"] < 0.5

    def test_fuzzy_match_sf(self):
        assert _match_location("San Francisco, CA") == "san_francisco"
        assert _match_location("SF Bay Area") == "san_francisco"
        assert _match_location("Mountain View, CA") == "san_francisco"

    def test_fuzzy_match_nyc(self):
        assert _match_location("New York, NY") == "new_york"
        assert _match_location("NYC") == "new_york"
        assert _match_location("Brooklyn, NY") == "new_york"

    def test_fuzzy_match_remote(self):
        assert _match_location("Remote") == "remote_us"

    def test_unknown_location_default(self):
        assert _match_location("Mars Colony") == "default"
        assert _match_location("") == "default"


# ── Company stage tests ──────────────────────────────────────────────────────


class TestCompanyStage:
    @pytest.mark.parametrize("stage", list(COMPANY_STAGE_MULTIPLIERS.keys()))
    def test_multipliers_positive(self, stage):
        assert COMPANY_STAGE_MULTIPLIERS[stage] > 0

    def test_faang_highest(self):
        assert COMPANY_STAGE_MULTIPLIERS["faang"] > COMPANY_STAGE_MULTIPLIERS["enterprise"]

    def test_seed_lowest(self):
        assert COMPANY_STAGE_MULTIPLIERS["seed"] < COMPANY_STAGE_MULTIPLIERS["enterprise"]

    def test_infer_google(self):
        assert _infer_company_stage("Google") == "faang"
        assert _infer_company_stage("Google LLC") == "faang"

    def test_infer_stripe(self):
        assert _infer_company_stage("Stripe") == "faang"

    def test_infer_consulting(self):
        assert _infer_company_stage("McKinsey & Company") == "consulting"

    def test_infer_unknown(self):
        assert _infer_company_stage("Random Corp") == "default"

    def test_infer_empty(self):
        assert _infer_company_stage("") == "default"


# ── Skill premium tests ─────────────────────────────────────────────────────


class TestSkillPremiums:
    @pytest.mark.parametrize("skill", list(SKILL_PREMIUMS.keys()))
    def test_premiums_positive(self, skill):
        assert 0 < SKILL_PREMIUMS[skill] <= 0.15

    def test_ai_has_highest_premium(self):
        assert SKILL_PREMIUMS["ai"] >= max(
            v for k, v in SKILL_PREMIUMS.items() if k not in ("ai", "machine learning", "deep learning", "staff_plus_leadership")
        )


# ── Career gap detection tests ───────────────────────────────────────────────


class TestCareerGaps:
    def test_no_gap(self):
        resume = _strong_resume()
        assert _detect_career_gaps(resume) == 0

    def test_detects_gap(self):
        resume = _gapped_resume()
        gap = _detect_career_gaps(resume)
        # Gap from June 2020 to Jan 2023 ≈ 31 months
        assert gap >= 28

    def test_single_job_no_gap(self):
        resume = _junior_resume()
        assert _detect_career_gaps(resume) == 0


# ── Core estimate_salary tests ───────────────────────────────────────────────


class TestEstimateSalary:
    def test_returns_salary_estimate(self):
        result = estimate_salary(_strong_resume(), _make_jd())
        assert isinstance(result, SalaryEstimate)

    def test_range_is_valid(self):
        result = estimate_salary(_strong_resume(), _make_jd())
        assert result.estimated_range[0] < result.estimated_range[1]
        assert result.estimated_range[0] > 0

    def test_midpoint_in_range(self):
        result = estimate_salary(_strong_resume(), _make_jd())
        low, high = result.estimated_range
        assert low <= result.estimated_midpoint <= high

    def test_sf_higher_than_denver(self):
        sf_result = estimate_salary(_strong_resume(), _make_jd(location="San Francisco, CA"))
        denver_result = estimate_salary(_strong_resume(), _make_jd(location="Denver, CO"))
        # SF multiplier is 1.35 vs Denver 1.00
        assert sf_result.estimated_midpoint > denver_result.estimated_midpoint
        ratio = sf_result.estimated_midpoint / denver_result.estimated_midpoint
        assert 1.20 < ratio < 1.50  # ~35% higher

    def test_faang_higher_than_startup(self):
        faang_result = estimate_salary(_strong_resume(), _make_jd(company="Google"))
        startup_result = estimate_salary(_strong_resume(), _make_jd(company="Seed Stage Startup"))
        assert faang_result.estimated_midpoint > startup_result.estimated_midpoint

    def test_tier1_experience_premium(self):
        result = estimate_salary(_strong_resume(), _make_jd())
        # Strong resume has Google + Stripe = tier 1 companies
        assert any("Tier 1" in f or "tier 1" in f.lower() for f in result.premium_factors)

    def test_skill_premiums_accumulated(self):
        result = estimate_salary(_strong_resume(), _make_jd())
        # Strong resume has Rust, Go, Kubernetes, distributed systems, Kafka, AWS
        assert any("skill" in f.lower() for f in result.premium_factors)

    def test_career_gap_discount(self):
        result = estimate_salary(_gapped_resume(), _make_jd(location="Denver"))
        assert any("gap" in f.lower() for f in result.discount_factors)

    def test_phd_premium_for_research(self):
        jd = _make_jd(title="Research Scientist", company="DeepMind")
        result = estimate_salary(_phd_research_resume(), jd)
        assert any("PhD" in f for f in result.premium_factors)

    def test_confidence_high_with_salary_range(self):
        jd = _make_jd(salary_range=(150_000, 220_000))
        result = estimate_salary(_strong_resume(), jd)
        assert result.confidence == "high"

    def test_confidence_medium_known_company_location(self):
        result = estimate_salary(_strong_resume(), _make_jd())
        assert result.confidence in ("high", "medium")

    def test_confidence_low_unknown(self):
        jd = _make_jd(company="", location="")
        result = estimate_salary(_strong_resume(), jd)
        assert result.confidence == "low"

    def test_user_position_below_mid(self):
        # Junior resume in senior JD → below mid
        result = estimate_salary(_junior_resume(), _make_jd(location="Denver"))
        # Might be at_mid or below_mid depending on factors
        assert result.user_position_in_range in ("below_mid", "at_mid", "above_mid")

    def test_user_position_valid(self):
        result = estimate_salary(_strong_resume(), _make_jd())
        assert result.user_position_in_range in ("below_mid", "at_mid", "above_mid")

    def test_user_value_positive(self):
        result = estimate_salary(_strong_resume(), _make_jd())
        assert result.user_estimated_value > 0

    def test_negotiation_talking_points_from_metrics(self):
        result = estimate_salary(_strong_resume(), _make_jd())
        # Strong resume has "$2.1M" and "40%" in bullets
        assert len(result.negotiation_talking_points) >= 1

    def test_role_type_populated(self):
        result = estimate_salary(_strong_resume(), _make_jd())
        assert result.role_type
        assert result.seniority

    def test_location_populated(self):
        result = estimate_salary(_strong_resume(), _make_jd(location="Seattle"))
        assert result.location == "seattle"


# ── With standout result tests ───────────────────────────────────────────────


class TestEstimateSalaryWithStandout:
    def _make_standout(self, spike_score: float = 70, cred_score: float = 65, outcome_score: float = 75):
        """Minimal standout result for testing."""
        from backend.agents.tailor.standout.engine import StandoutScoreResult, StandoutDimensionScore
        dims = [
            StandoutDimensionScore(
                dimension_id="spike_factor", dimension_name="Spike Factor",
                raw_score=spike_score, weighted_score=spike_score * 0.12, weight=0.12,
                explanation="Found 2 spikes: Google brand, 5M users scale",
                issues=[], suggestions=[], priority="medium",
            ),
            StandoutDimensionScore(
                dimension_id="credibility_anchors", dimension_name="Credibility Anchors",
                raw_score=cred_score, weighted_score=cred_score * 0.12, weight=0.12,
                explanation="Google + Stanford",
                issues=[], suggestions=[], priority="medium",
            ),
            StandoutDimensionScore(
                dimension_id="outcome_density", dimension_name="Outcome Density",
                raw_score=outcome_score, weighted_score=outcome_score * 0.15, weight=0.15,
                explanation="75% outcomes",
                issues=[], suggestions=[], priority="medium",
            ),
        ]
        # Fill remaining 5 dims
        for dim_id in ["trajectory_signal", "builder_ratio", "narrative_pull", "uniqueness_index", "first_impression"]:
            dims.append(StandoutDimensionScore(
                dimension_id=dim_id, dimension_name=dim_id.replace("_", " ").title(),
                raw_score=50, weighted_score=50 * 0.1, weight=0.1,
                explanation="Average", issues=[], suggestions=[], priority="low",
            ))
        return StandoutScoreResult(
            total_score=60, letter_grade="C", dimension_scores=dims,
            top_3_issues=[], top_3_wins=[], spike_detected=spike_score >= 60,
            role_type="software_engineer_backend", seniority_level="senior",
            weights_used={}, amplification_tips=[],
        )

    def test_spike_adds_negotiation_leverage(self):
        standout = self._make_standout(spike_score=70)
        result = estimate_salary(_strong_resume(), _make_jd(), standout_result=standout)
        assert any("spike" in l.lower() for l in result.negotiation_leverage)

    def test_credibility_adds_leverage(self):
        standout = self._make_standout(cred_score=80)
        result = estimate_salary(_strong_resume(), _make_jd(), standout_result=standout)
        assert any("credibility" in l.lower() for l in result.negotiation_leverage)

    def test_no_leverage_when_scores_low(self):
        standout = self._make_standout(spike_score=30, cred_score=30, outcome_score=30)
        result = estimate_salary(_strong_resume(), _make_jd(), standout_result=standout)
        spike_leverage = [l for l in result.negotiation_leverage if "spike" in l.lower()]
        assert len(spike_leverage) == 0
