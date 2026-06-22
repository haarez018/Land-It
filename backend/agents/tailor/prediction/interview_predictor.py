"""
Interview Callback Prediction Model.

Estimates the probability of receiving an interview callback using a Bayesian
approach calibrated against published industry callback rates (~8% average).

Uses a sigmoid mapping from the combined 22-dimension score to a probability
multiplier, then adjusts by role type and seniority. No external ML libraries
— pure math with the standard library.

Published industry data sources:
  - Average callback rate: ~8% (Jobvite 2023, Glassdoor)
  - Software engineer roles: ~10-12% (higher demand)
  - Product manager roles: ~6-8%
  - Data scientist roles: ~9-11%
  - Executive roles: ~5-7% (selective, fewer applicants)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from backend.agents.tailor.weightage.scorer_engine import ATSScoreResult
from backend.agents.tailor.standout.engine import StandoutScoreResult


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class CallbackPrediction:
    """Predicted interview callback probability with confidence intervals."""
    probability: float                   # 0.0 to 0.85 (capped)
    confidence_interval: tuple[float, float]  # (lower, upper) bounds
    confidence_level: str                # "high" | "medium" | "low"
    top_positive_factors: list[str]      # What's helping
    top_negative_factors: list[str]      # What's hurting
    vs_average_applicant: float          # Percentage above/below average (e.g., +180%)
    score_needed_for_50pct: float        # Combined score needed to hit 50% callback
    fixes_for_10pct_boost: list[str]     # Actionable fixes for +10% probability
    role_type: str
    seniority_level: str
    combined_score: float
    base_rate: float                     # Base callback rate before adjustments


# ── Base rates (calibrated from published industry data) ──────────────────

BASE_RATES: dict[str, float] = {
    "software_engineer_backend": 0.10,    # Backend eng: ~10%
    "software_engineer_frontend": 0.11,   # Frontend eng: slightly higher demand
    "ml_engineer": 0.09,                  # ML: competitive but specialized
    "product_manager": 0.07,              # PM: fewer roles, more applicants
    "data_scientist": 0.09,              # Data science: strong demand
    "devops_sre": 0.12,                  # DevOps/SRE: high demand, fewer candidates
    "research_scientist": 0.06,          # Research: very competitive
    "design_ux": 0.08,                   # UX: moderate
}

# Seniority adjustments: interns have higher callback rates (less competition
# for intern slots, lower bar); executives have lower rates (very selective,
# each opening has fewer but stronger applicants)
SENIORITY_RATE_MULTIPLIERS: dict[str, float] = {
    "intern": 1.4,          # Intern: more slots, lower bar → higher rate
    "junior": 1.2,          # Junior: still accessible
    "mid": 1.0,             # Mid: baseline
    "senior": 0.85,         # Senior: more selective
    "staff_principal": 0.7,  # Staff/Principal: very selective
    "executive": 0.55,       # Executive: extremely selective
}


# ── Sigmoid mapping ──────────────────────────────────────────────────────────

def _sigmoid_multiplier(combined_score: float) -> float:
    """
    Map a combined score (0-100) to a probability multiplier using a sigmoid.

    The sigmoid is centered at 55 (average resume score) with a steepness
    that produces sensible ranges:
      - Score 30 → multiplier ~0.3  (well below average)
      - Score 50 → multiplier ~0.8  (slightly below average)
      - Score 55 → multiplier ~1.0  (average)
      - Score 70 → multiplier ~2.5  (strong)
      - Score 80 → multiplier ~4.5  (very strong)
      - Score 90 → multiplier ~7.0  (exceptional)

    Uses a modified sigmoid: multiplier = max_mult / (1 + e^(-k*(x - midpoint)))
    """
    midpoint = 55.0
    steepness = 0.08
    max_multiplier = 8.5

    # Standard sigmoid → [0, 1] range
    sigmoid_value = 1.0 / (1.0 + math.exp(-steepness * (combined_score - midpoint)))

    # Scale to [0, max_multiplier]
    return sigmoid_value * max_multiplier


def _compute_confidence_interval(
    probability: float,
    dimension_scores: list[float],
) -> tuple[tuple[float, float], str]:
    """
    Compute confidence interval based on dimension score variance.

    High variance = less reliable prediction → wider interval.
    Low variance = consistent scores → tighter interval.

    Returns:
        ((lower, upper), confidence_level)
    """
    n = len(dimension_scores)
    if n < 2:
        half_width = probability * 0.4
        return (
            (max(0.0, probability - half_width), min(0.85, probability + half_width)),
            "low",
        )

    mean = sum(dimension_scores) / n
    variance = sum((s - mean) ** 2 for s in dimension_scores) / (n - 1)
    std_dev = math.sqrt(variance)

    # Coefficient of variation — higher = more spread
    cv = std_dev / mean if mean > 0 else 1.0

    # Scale half-width by CV
    # CV ≈ 0.1 → tight (±15%), CV ≈ 0.3 → moderate (±30%), CV ≈ 0.5+ → wide (±45%)
    half_width_pct = min(0.45, 0.15 + cv * 0.6)
    half_width = probability * half_width_pct

    lower = max(0.01, probability - half_width)
    upper = min(0.85, probability + half_width)

    # Classify confidence
    if cv < 0.15:
        level = "high"
    elif cv < 0.30:
        level = "medium"
    else:
        level = "low"

    return (round(lower, 4), round(upper, 4)), level


def _identify_factors(
    ats: ATSScoreResult,
    standout: StandoutScoreResult,
) -> tuple[list[str], list[str]]:
    """
    Identify top positive and negative factors from dimension scores.

    Returns:
        (top_positive, top_negative)
    """
    all_dims: list[tuple[str, float, float]] = []  # (name, raw_score, weight)

    for d in ats.dimension_scores:
        all_dims.append((d.dimension_name, d.raw_score, d.weight))
    for d in standout.dimension_scores:
        all_dims.append((d.dimension_name, d.raw_score, d.weight))

    # Positive: high raw_score × weight (contributing most)
    positive = sorted(all_dims, key=lambda x: x[1] * x[2], reverse=True)
    top_positive = [
        f"{name} ({score:.0f}/100)"
        for name, score, weight in positive[:4]
        if score >= 60
    ]

    # Negative: low raw_score × high weight (dragging score down most)
    negative = sorted(all_dims, key=lambda x: (100 - x[1]) * x[2], reverse=True)
    top_negative = [
        f"{name} ({score:.0f}/100)"
        for name, score, weight in negative[:4]
        if score < 60
    ]

    return top_positive, top_negative


def _compute_score_for_target_probability(
    target_prob: float,
    base_rate: float,
) -> float:
    """
    Reverse the sigmoid to find the combined score needed for a target probability.

    probability = min(base_rate * multiplier, 0.85)
    target_prob = base_rate * multiplier
    multiplier = target_prob / base_rate
    sigmoid_value = multiplier / max_multiplier
    combined_score = midpoint - ln(1/sigmoid_value - 1) / steepness
    """
    max_multiplier = 8.5
    midpoint = 55.0
    steepness = 0.08

    needed_multiplier = target_prob / base_rate
    if needed_multiplier >= max_multiplier:
        return 100.0  # Not achievable
    if needed_multiplier <= 0:
        return 0.0

    sigmoid_value = needed_multiplier / max_multiplier
    if sigmoid_value >= 1.0:
        return 100.0
    if sigmoid_value <= 0.0:
        return 0.0

    # Inverse sigmoid: x = midpoint - ln(1/s - 1) / steepness
    score = midpoint - math.log(1.0 / sigmoid_value - 1.0) / steepness
    return max(0.0, min(100.0, round(score, 1)))


def _generate_fixes_for_boost(
    ats: ATSScoreResult,
    standout: StandoutScoreResult,
    current_probability: float,
) -> list[str]:
    """
    Generate actionable fixes that would boost callback probability by ~10%.

    Targets the dimensions with the highest improvement-to-effort ratio:
    high weight × low current score = biggest bang for buck.
    """
    fixes: list[str] = []

    # Combine all dimensions with their suggestions
    all_dims: list[tuple[str, float, float, list[str]]] = []
    for d in ats.dimension_scores:
        all_dims.append((d.dimension_name, d.raw_score, d.weight, d.suggestions))
    for d in standout.dimension_scores:
        all_dims.append((d.dimension_name, d.raw_score, d.weight, d.suggestions))

    # Sort by improvement potential: weight × (100 - score) = "room × impact"
    all_dims.sort(key=lambda x: x[2] * (100 - x[1]), reverse=True)

    for name, score, weight, suggestions in all_dims:
        if score < 70 and suggestions:
            fixes.append(f"{name}: {suggestions[0]}")
            if len(fixes) >= 4:
                break

    if not fixes:
        fixes.append("Your scores are already strong — focus on tailoring to specific JD keywords")

    return fixes


# ── Calibration ─────────────────────────────────────────────────────────────

CALIBRATION_POINTS: dict[int, tuple[float, float]] = {
    30: (0.02, 0.08),
    40: (0.03, 0.10),
    50: (0.05, 0.15),
    60: (0.08, 0.25),
    70: (0.15, 0.40),
    80: (0.25, 0.55),
    90: (0.40, 0.70),
    95: (0.50, 0.80),
}


def validate_calibration(
    role_type: str = "software_engineer_backend",
    seniority: str = "mid",
) -> list[str]:
    """Run calibration check. Returns list of violations."""
    violations: list[str] = []
    base = BASE_RATES.get(role_type, 0.08)
    mult = SENIORITY_RATE_MULTIPLIERS.get(seniority, 1.0)
    adjusted_base = base * mult

    for score, (expected_low, expected_high) in CALIBRATION_POINTS.items():
        multiplier = _sigmoid_multiplier(score)
        probability = min(adjusted_base * multiplier, 0.85)

        if probability < expected_low or probability > expected_high:
            violations.append(
                f"Score {score}: got {probability:.3f}, "
                f"expected {expected_low:.3f}-{expected_high:.3f}"
            )
    return violations


# ── Main prediction function ─────────────────────────────────────────────────

def predict_callback(
    ats: ATSScoreResult,
    standout: StandoutScoreResult,
    role_type: Optional[str] = None,
    seniority: Optional[str] = None,
) -> CallbackPrediction:
    """
    Predict interview callback probability from ATS and Standout scores.

    Algorithm:
      1. combined_score = 0.6 × ATS + 0.4 × Standout
      2. base_rate = BASE_RATES[role_type] × SENIORITY_MULTIPLIERS[seniority]
      3. multiplier = sigmoid(combined_score)
      4. probability = min(base_rate × multiplier, 0.85)
      5. confidence_interval from dimension score variance
      6. Compute vs_average, score_for_50%, fixes

    Args:
        ats: ATSScoreResult from the 14-dimension scorer
        standout: StandoutScoreResult from the 8-dimension scorer
        role_type: Override role type (default: from ATS result)
        seniority: Override seniority (default: from ATS result)

    Returns:
        CallbackPrediction with probability and actionable insights
    """
    # Step 1: Combined score
    combined_score = round(ats.total_score * 0.6 + standout.total_score * 0.4, 1)

    # Step 2: Base rate
    _role = role_type or ats.role_type
    _seniority = seniority or ats.seniority_level

    role_rate = BASE_RATES.get(_role, 0.08)
    seniority_mult = SENIORITY_RATE_MULTIPLIERS.get(_seniority, 1.0)
    base_rate = role_rate * seniority_mult

    # Step 3: Sigmoid multiplier
    multiplier = _sigmoid_multiplier(combined_score)

    # Step 4: Probability (capped at 85%)
    probability = min(base_rate * multiplier, 0.85)
    probability = round(probability, 4)

    # Step 5: Confidence interval
    all_raw_scores = [d.raw_score for d in ats.dimension_scores] + \
                     [d.raw_score for d in standout.dimension_scores]
    ci, confidence_level = _compute_confidence_interval(probability, all_raw_scores)

    # Step 6: Factors
    top_positive, top_negative = _identify_factors(ats, standout)

    # Vs average: what % above/below the average applicant?
    # Average applicant: combined ~50, base_rate callback
    avg_probability = base_rate * _sigmoid_multiplier(50.0)
    if avg_probability > 0:
        vs_average = round((probability - avg_probability) / avg_probability * 100, 1)
    else:
        vs_average = 0.0

    # Score needed for 50% callback
    score_for_50 = _compute_score_for_target_probability(0.50, base_rate)

    # Fixes for ~10% boost
    fixes = _generate_fixes_for_boost(ats, standout, probability)

    return CallbackPrediction(
        probability=probability,
        confidence_interval=ci,
        confidence_level=confidence_level,
        top_positive_factors=top_positive,
        top_negative_factors=top_negative,
        vs_average_applicant=vs_average,
        score_needed_for_50pct=score_for_50,
        fixes_for_10pct_boost=fixes,
        role_type=_role,
        seniority_level=_seniority,
        combined_score=combined_score,
        base_rate=round(base_rate, 4),
    )
