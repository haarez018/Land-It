"""Unit tests for the Interview Callback Prediction Model."""

from __future__ import annotations

import math
from datetime import date

import pytest

from backend.parsers.schemas import (
    Education,
    JobDescription,
    Resume,
    ResumeContact,
    WorkExperience,
)
from backend.agents.tailor.prediction.interview_predictor import (
    predict_callback,
    CallbackPrediction,
    BASE_RATES,
    SENIORITY_RATE_MULTIPLIERS,
    _sigmoid_multiplier,
    _compute_confidence_interval,
    _compute_score_for_target_probability,
    _identify_factors,
    _generate_fixes_for_boost,
)
from backend.agents.tailor.weightage.scorer_engine import ATSScoreResult, DimensionScore
from backend.agents.tailor.standout.engine import StandoutScoreResult, StandoutDimensionScore


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_ats_result(
    total_score: float = 65.0,
    role_type: str = "software_engineer_backend",
    seniority: str = "mid",
    dim_scores: list[float] | None = None,
) -> ATSScoreResult:
    """Build a minimal ATSScoreResult for testing."""
    scores = dim_scores or [total_score] * 14
    dims = []
    dim_names = [
        "keyword_density", "skill_depth", "tech_stack_alignment",
        "experience_relevance", "quantified_impact", "action_verb_strength",
        "section_ordering", "bullet_quality", "ats_parsability",
        "seniority_calibration", "domain_knowledge", "education_relevance",
        "semantic_similarity", "voice_alignment",
    ]
    for i, name in enumerate(dim_names):
        raw = scores[i] if i < len(scores) else total_score
        dims.append(DimensionScore(
            dimension_id=name,
            dimension_name=name.replace("_", " ").title(),
            raw_score=raw,
            weighted_score=raw * (1.0 / 14),
            weight=1.0 / 14,
            explanation=f"Score: {raw}",
            issues=[f"Issue for {name}"] if raw < 60 else [],
            suggestions=[f"Improve {name}"] if raw < 70 else [],
            priority="medium",
        ))
    return ATSScoreResult(
        total_score=total_score,
        letter_grade="B",
        dimension_scores=dims,
        top_3_issues=[],
        top_3_wins=[],
        predicted_ats_pass=total_score >= 70,
        role_type=role_type,
        seniority_level=seniority,
        weights_used={n: 1.0 / 14 for n in dim_names},
    )


def _make_standout_result(
    total_score: float = 55.0,
    spike_detected: bool = False,
    dim_scores: list[float] | None = None,
) -> StandoutScoreResult:
    """Build a minimal StandoutScoreResult for testing."""
    scores = dim_scores or [total_score] * 8
    dim_names = [
        "spike_factor", "trajectory_signal", "builder_ratio",
        "outcome_density", "narrative_pull", "uniqueness_index",
        "credibility_anchors", "first_impression",
    ]
    dims = []
    for i, name in enumerate(dim_names):
        raw = scores[i] if i < len(scores) else total_score
        dims.append(StandoutDimensionScore(
            dimension_id=name,
            dimension_name=name.replace("_", " ").title(),
            raw_score=raw,
            weighted_score=raw * (1.0 / 8),
            weight=1.0 / 8,
            explanation=f"Score: {raw}",
            issues=[f"Issue for {name}"] if raw < 50 else [],
            suggestions=[f"Improve {name}"] if raw < 70 else [],
            priority="medium",
        ))
    return StandoutScoreResult(
        total_score=total_score,
        letter_grade="C+",
        dimension_scores=dims,
        top_3_issues=[],
        top_3_wins=[],
        spike_detected=spike_detected,
        role_type="software_engineer_backend",
        seniority_level="mid",
        weights_used={n: 1.0 / 8 for n in dim_names},
        amplification_tips=[],
    )


# ── Sigmoid mapping tests ────────────────────────────────────────────────────


class TestSigmoidMapping:
    def test_score_30_produces_low_multiplier(self):
        """Score 30 should produce a low multiplier (well below average)."""
        mult = _sigmoid_multiplier(30)
        assert mult < 1.5, f"Score 30 multiplier too high: {mult}"

    def test_score_55_is_approximately_baseline(self):
        """Score 55 (midpoint) should give ~1x multiplier relative to average."""
        mult = _sigmoid_multiplier(55)
        assert 3.5 < mult < 5.0, f"Score 55 multiplier unexpected: {mult}"

    def test_score_90_produces_high_multiplier(self):
        """Score 90 should produce a high multiplier."""
        mult = _sigmoid_multiplier(90)
        assert mult > 7.0, f"Score 90 multiplier too low: {mult}"

    def test_monotonically_increasing(self):
        """Higher scores should always produce higher multipliers."""
        prev = 0
        for score in range(0, 101, 5):
            mult = _sigmoid_multiplier(score)
            assert mult >= prev, f"Non-monotonic at score {score}: {mult} < {prev}"
            prev = mult

    def test_score_0_positive(self):
        """Even score 0 should produce a positive (small) multiplier."""
        mult = _sigmoid_multiplier(0)
        assert mult > 0

    def test_score_100_bounded(self):
        """Score 100 should not exceed max_multiplier."""
        mult = _sigmoid_multiplier(100)
        assert mult <= 8.5

    def test_produces_sensible_probabilities_for_backend(self):
        """For a mid-level backend engineer, verify probability ranges."""
        base = BASE_RATES["software_engineer_backend"]  # 0.10
        # Score 30: should give < 15% callback
        prob_30 = min(base * _sigmoid_multiplier(30), 0.85)
        assert prob_30 < 0.15, f"Score 30 prob too high: {prob_30}"

        # Score 90: should give > 50% callback
        prob_90 = min(base * _sigmoid_multiplier(90), 0.85)
        assert prob_90 > 0.50, f"Score 90 prob too low: {prob_90}"


# ── Base rates tests ──────────────────────────────────────────────────────────


class TestBaseRates:
    def test_all_8_role_types_present(self):
        expected = {
            "software_engineer_backend", "software_engineer_frontend",
            "ml_engineer", "product_manager", "data_scientist",
            "devops_sre", "research_scientist", "design_ux",
        }
        assert set(BASE_RATES.keys()) == expected

    @pytest.mark.parametrize("role", list(BASE_RATES.keys()))
    def test_rates_are_reasonable(self, role):
        """All base rates should be between 3% and 15%."""
        rate = BASE_RATES[role]
        assert 0.03 <= rate <= 0.15, f"{role} rate {rate} out of range"

    def test_devops_has_highest_rate(self):
        """DevOps/SRE should have the highest base rate (supply shortage)."""
        assert BASE_RATES["devops_sre"] == max(BASE_RATES.values())

    def test_research_has_lowest_rate(self):
        """Research scientist should have the lowest rate (most competitive)."""
        assert BASE_RATES["research_scientist"] == min(BASE_RATES.values())


# ── Seniority multiplier tests ───────────────────────────────────────────────


class TestSeniorityMultipliers:
    def test_all_6_levels_present(self):
        expected = {"intern", "junior", "mid", "senior", "staff_principal", "executive"}
        assert set(SENIORITY_RATE_MULTIPLIERS.keys()) == expected

    def test_mid_is_baseline(self):
        assert SENIORITY_RATE_MULTIPLIERS["mid"] == 1.0

    def test_intern_higher_than_mid(self):
        """Interns get higher callback rates (more slots, lower bar)."""
        assert SENIORITY_RATE_MULTIPLIERS["intern"] > SENIORITY_RATE_MULTIPLIERS["mid"]

    def test_executive_lower_than_mid(self):
        """Executives have lower callback rates (very selective)."""
        assert SENIORITY_RATE_MULTIPLIERS["executive"] < SENIORITY_RATE_MULTIPLIERS["mid"]

    def test_monotonically_decreasing(self):
        """From intern to executive, multipliers should decrease."""
        order = ["intern", "junior", "mid", "senior", "staff_principal", "executive"]
        mults = [SENIORITY_RATE_MULTIPLIERS[s] for s in order]
        for i in range(1, len(mults)):
            assert mults[i] <= mults[i - 1], (
                f"{order[i]} ({mults[i]}) > {order[i-1]} ({mults[i-1]})"
            )

    @pytest.mark.parametrize("seniority", list(SENIORITY_RATE_MULTIPLIERS.keys()))
    def test_multipliers_positive(self, seniority):
        assert SENIORITY_RATE_MULTIPLIERS[seniority] > 0


# ── Confidence interval tests ────────────────────────────────────────────────


class TestConfidenceInterval:
    def test_uniform_scores_give_tight_interval(self):
        """If all dimensions score the same, interval should be tight."""
        scores = [70.0] * 22
        ci, level = _compute_confidence_interval(0.40, scores)
        lower, upper = ci
        width = upper - lower
        assert width < 0.20, f"Too wide for uniform scores: {width}"
        assert level == "high"

    def test_varied_scores_give_wider_interval(self):
        """High variance in scores should widen the interval."""
        scores = [10, 20, 90, 95, 30, 85, 15, 80, 25, 75, 10, 90, 20, 80,
                  10, 90, 20, 85, 15, 95, 30, 70]
        ci, level = _compute_confidence_interval(0.40, scores)
        lower, upper = ci
        width = upper - lower
        assert width > 0.15, f"Too narrow for varied scores: {width}"

    def test_interval_contains_probability(self):
        """The probability should fall within its own confidence interval."""
        ci, _ = _compute_confidence_interval(0.35, [60.0] * 22)
        assert ci[0] <= 0.35 <= ci[1]

    def test_interval_bounded(self):
        """Interval should not exceed [0, 0.85]."""
        ci, _ = _compute_confidence_interval(0.80, [90.0] * 22)
        assert ci[0] >= 0.0
        assert ci[1] <= 0.85

    def test_very_few_scores_gives_low_confidence(self):
        """With < 2 dimension scores, confidence should be low."""
        ci, level = _compute_confidence_interval(0.30, [50.0])
        assert level == "low"

    def test_high_variance_gives_low_confidence(self):
        """Very high variance should produce low confidence."""
        scores = [5, 95] * 11  # alternating extremes
        ci, level = _compute_confidence_interval(0.50, scores)
        assert level == "low"


# ── Reverse sigmoid (score_for_target) tests ─────────────────────────────────


class TestScoreForTarget:
    def test_50pct_for_backend_mid(self):
        """Score needed for 50% with backend mid engineer."""
        base_rate = 0.10  # backend
        score = _compute_score_for_target_probability(0.50, base_rate)
        # 50% / 0.10 = multiplier 5.0, should need score ~58-68
        assert 50 < score < 80, f"Score for 50% unexpected: {score}"

    def test_impossible_target_returns_100(self):
        """If target probability needs multiplier > max, return 100."""
        score = _compute_score_for_target_probability(0.90, 0.05)
        # 0.90 / 0.05 = 18x — impossible (max ~8.5x)
        assert score == 100.0

    def test_zero_target_returns_0(self):
        """Target probability 0 should return score 0."""
        score = _compute_score_for_target_probability(0.0, 0.10)
        assert score == 0.0

    def test_round_trip_consistency(self):
        """
        For a given base rate, compute score-for-50%, then verify the sigmoid
        at that score produces a multiplier that gives ~50%.
        """
        base_rate = 0.10
        target = 0.50
        score = _compute_score_for_target_probability(target, base_rate)
        if score < 100:
            mult = _sigmoid_multiplier(score)
            prob = min(base_rate * mult, 0.85)
            assert abs(prob - target) < 0.02, (
                f"Round-trip mismatch: score={score}, prob={prob}, target={target}"
            )


# ── Factor identification tests ──────────────────────────────────────────────


class TestFactorIdentification:
    def test_positive_factors_from_high_scores(self):
        ats = _make_ats_result(
            total_score=80,
            dim_scores=[90, 85, 80, 75, 70, 65, 60, 55, 50, 45, 40, 35, 80, 70],
        )
        standout = _make_standout_result(total_score=60, dim_scores=[80, 70, 60, 50, 40, 30, 80, 90])
        pos, neg = _identify_factors(ats, standout)
        assert len(pos) >= 1
        # The highest-scoring dimensions should appear in positive factors
        assert any("90" in f for f in pos)

    def test_negative_factors_from_low_scores(self):
        ats = _make_ats_result(total_score=40, dim_scores=[20] * 14)
        standout = _make_standout_result(total_score=30, dim_scores=[20] * 8)
        pos, neg = _identify_factors(ats, standout)
        assert len(neg) >= 1

    def test_no_negative_factors_when_all_high(self):
        ats = _make_ats_result(total_score=90, dim_scores=[90] * 14)
        standout = _make_standout_result(total_score=90, dim_scores=[90] * 8)
        pos, neg = _identify_factors(ats, standout)
        assert len(neg) == 0  # All scores >= 60


# ── Main predict_callback tests ──────────────────────────────────────────────


class TestPredictCallback:
    def test_returns_callback_prediction(self):
        ats = _make_ats_result(total_score=70)
        standout = _make_standout_result(total_score=60)
        pred = predict_callback(ats, standout)
        assert isinstance(pred, CallbackPrediction)

    def test_probability_in_valid_range(self):
        ats = _make_ats_result(total_score=70)
        standout = _make_standout_result(total_score=60)
        pred = predict_callback(ats, standout)
        assert 0.0 <= pred.probability <= 0.85

    def test_probability_capped_at_85pct(self):
        """Even a perfect score should not exceed 85% callback probability."""
        ats = _make_ats_result(total_score=100)
        standout = _make_standout_result(total_score=100)
        pred = predict_callback(ats, standout)
        assert pred.probability <= 0.85

    def test_low_scores_give_low_probability(self):
        """Score 30 ATS + 20 Standout should give < 10% for mid-level backend."""
        ats = _make_ats_result(total_score=30, dim_scores=[30] * 14)
        standout = _make_standout_result(total_score=20, dim_scores=[20] * 8)
        pred = predict_callback(ats, standout)
        # combined = 30*0.6 + 20*0.4 = 26
        assert pred.probability < 0.10, f"Too high for low scores: {pred.probability}"

    def test_high_scores_give_high_probability(self):
        """Score 90 ATS + 85 Standout should give > 50% for mid-level backend."""
        ats = _make_ats_result(total_score=90, dim_scores=[90] * 14)
        standout = _make_standout_result(total_score=85, dim_scores=[85] * 8)
        pred = predict_callback(ats, standout)
        # combined = 90*0.6 + 85*0.4 = 88
        assert pred.probability > 0.50, f"Too low for high scores: {pred.probability}"

    def test_combined_score_computed_correctly(self):
        ats = _make_ats_result(total_score=80)
        standout = _make_standout_result(total_score=60)
        pred = predict_callback(ats, standout)
        expected = round(80 * 0.6 + 60 * 0.4, 1)
        assert pred.combined_score == expected

    def test_confidence_interval_populated(self):
        ats = _make_ats_result(total_score=65)
        standout = _make_standout_result(total_score=55)
        pred = predict_callback(ats, standout)
        lower, upper = pred.confidence_interval
        assert lower <= pred.probability <= upper

    def test_confidence_level_valid(self):
        ats = _make_ats_result(total_score=70)
        standout = _make_standout_result(total_score=60)
        pred = predict_callback(ats, standout)
        assert pred.confidence_level in {"high", "medium", "low"}

    def test_positive_factors_populated(self):
        ats = _make_ats_result(total_score=80, dim_scores=[85] * 14)
        standout = _make_standout_result(total_score=70, dim_scores=[75] * 8)
        pred = predict_callback(ats, standout)
        assert len(pred.top_positive_factors) >= 1

    def test_negative_factors_for_weak_resume(self):
        ats = _make_ats_result(total_score=35, dim_scores=[30] * 14)
        standout = _make_standout_result(total_score=25, dim_scores=[25] * 8)
        pred = predict_callback(ats, standout)
        assert len(pred.top_negative_factors) >= 1

    def test_vs_average_positive_for_strong_resume(self):
        ats = _make_ats_result(total_score=85)
        standout = _make_standout_result(total_score=80)
        pred = predict_callback(ats, standout)
        assert pred.vs_average_applicant > 0, "Strong resume should be above average"

    def test_vs_average_negative_for_weak_resume(self):
        ats = _make_ats_result(total_score=30, dim_scores=[30] * 14)
        standout = _make_standout_result(total_score=20, dim_scores=[20] * 8)
        pred = predict_callback(ats, standout)
        assert pred.vs_average_applicant < 0, "Weak resume should be below average"

    def test_score_needed_for_50pct_populated(self):
        ats = _make_ats_result(total_score=50)
        standout = _make_standout_result(total_score=40)
        pred = predict_callback(ats, standout)
        assert 0 < pred.score_needed_for_50pct <= 100

    def test_fixes_populated(self):
        ats = _make_ats_result(total_score=50, dim_scores=[40] * 14)
        standout = _make_standout_result(total_score=40, dim_scores=[35] * 8)
        pred = predict_callback(ats, standout)
        assert len(pred.fixes_for_10pct_boost) >= 1

    def test_role_type_override(self):
        ats = _make_ats_result(total_score=65)
        standout = _make_standout_result(total_score=55)
        pred = predict_callback(ats, standout, role_type="product_manager")
        assert pred.role_type == "product_manager"

    def test_seniority_override(self):
        ats = _make_ats_result(total_score=65)
        standout = _make_standout_result(total_score=55)
        pred = predict_callback(ats, standout, seniority="senior")
        assert pred.seniority_level == "senior"

    def test_base_rate_populated(self):
        ats = _make_ats_result(total_score=65)
        standout = _make_standout_result(total_score=55)
        pred = predict_callback(ats, standout)
        assert pred.base_rate > 0

    def test_intern_higher_probability_than_exec_at_same_score(self):
        """At the same score, interns should have higher callback probability."""
        ats_intern = _make_ats_result(total_score=60, seniority="intern")
        standout_intern = _make_standout_result(total_score=50)
        pred_intern = predict_callback(ats_intern, standout_intern, seniority="intern")

        ats_exec = _make_ats_result(total_score=60, seniority="executive")
        standout_exec = _make_standout_result(total_score=50)
        pred_exec = predict_callback(ats_exec, standout_exec, seniority="executive")

        assert pred_intern.probability > pred_exec.probability

    def test_devops_higher_probability_than_research_at_same_score(self):
        """DevOps/SRE should have higher callback rate than research scientist."""
        ats_devops = _make_ats_result(total_score=60, role_type="devops_sre")
        standout_devops = _make_standout_result(total_score=50)
        pred_devops = predict_callback(ats_devops, standout_devops, role_type="devops_sre")

        ats_research = _make_ats_result(total_score=60, role_type="research_scientist")
        standout_research = _make_standout_result(total_score=50)
        pred_research = predict_callback(
            ats_research, standout_research, role_type="research_scientist"
        )

        assert pred_devops.probability > pred_research.probability

    def test_unknown_role_uses_default_rate(self):
        """Unknown role type should use fallback rate (~8%)."""
        ats = _make_ats_result(total_score=65, role_type="unknown_role")
        standout = _make_standout_result(total_score=55)
        pred = predict_callback(ats, standout, role_type="unknown_role")
        assert pred.base_rate == 0.08  # fallback

    def test_unknown_seniority_uses_mid(self):
        """Unknown seniority should use mid (1.0x) multiplier."""
        ats = _make_ats_result(total_score=65, seniority="unknown")
        standout = _make_standout_result(total_score=55)
        pred_unknown = predict_callback(ats, standout, seniority="unknown")
        pred_mid = predict_callback(ats, standout, seniority="mid")
        assert pred_unknown.probability == pred_mid.probability


# ── Confidence interval width vs variance ────────────────────────────────────


class TestConfidenceIntervalVsVariance:
    def test_wider_with_more_variance(self):
        """Higher dimension score variance should produce a wider interval."""
        uniform_scores = [65.0] * 22
        varied_scores = [10, 20, 90, 95, 30, 85, 15, 80, 25, 75,
                         10, 90, 20, 85, 15, 95, 30, 70, 40, 60, 50, 80]

        ci_uniform, _ = _compute_confidence_interval(0.30, uniform_scores)
        ci_varied, _ = _compute_confidence_interval(0.30, varied_scores)

        width_uniform = ci_uniform[1] - ci_uniform[0]
        width_varied = ci_varied[1] - ci_varied[0]

        assert width_varied > width_uniform


# ── Fixes for boost tests ────────────────────────────────────────────────────


class TestFixesForBoost:
    def test_fixes_target_low_score_high_weight_dims(self):
        """Fixes should come from dimensions with highest improvement potential."""
        ats = _make_ats_result(
            total_score=50,
            dim_scores=[40, 35, 30, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95],
        )
        standout = _make_standout_result(
            total_score=45,
            dim_scores=[30, 40, 50, 60, 70, 80, 35, 45],
        )
        fixes = _generate_fixes_for_boost(ats, standout, 0.20)
        assert len(fixes) >= 1
        assert len(fixes) <= 4

    def test_no_fixes_when_all_high(self):
        """When all scores are high, should still return at least one suggestion."""
        ats = _make_ats_result(total_score=95, dim_scores=[95] * 14)
        standout = _make_standout_result(total_score=95, dim_scores=[95] * 8)
        fixes = _generate_fixes_for_boost(ats, standout, 0.70)
        assert len(fixes) >= 1  # Should have the fallback message
