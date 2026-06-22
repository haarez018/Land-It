"""
Standout Engine: master orchestrator for the 8 human-impression dimensions.

Parallel to backend.agents.tailor.weightage.scorer_engine (ATS scoring).
Runs all 8 standout scorers concurrently and produces a StandoutScoreResult.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional

from backend.parsers.schemas import Resume, JobDescription
from .dimensions import STANDOUT_DIMENSIONS
from .role_profiles import get_standout_role_profile
from .seniority_matrix import apply_standout_seniority_adjustment
from backend.agents.tailor.weightage.company_profiles import get_company_profile, apply_company_profile


@dataclass
class StandoutDimensionScore:
    dimension_id: str
    dimension_name: str
    raw_score: float
    weighted_score: float
    weight: float
    explanation: str
    issues: list[str]
    suggestions: list[str]
    priority: str


@dataclass
class StandoutScoreResult:
    total_score: float
    letter_grade: str
    dimension_scores: list[StandoutDimensionScore]
    top_3_issues: list[str]
    top_3_wins: list[str]
    spike_detected: bool
    role_type: str
    seniority_level: str
    weights_used: dict[str, float]
    amplification_tips: list[str] = field(default_factory=list)


def _get_standout_scorer_map():
    """Lazy import to avoid circular deps — matches ATS pattern."""
    from backend.agents.tailor.standout.scorers import (
        spike_factor_scorer,
        trajectory_scorer,
        builder_ratio_scorer,
        outcome_density_scorer,
        narrative_pull_scorer,
        uniqueness_index_scorer,
        credibility_anchors_scorer,
        first_impression_scorer,
    )
    return {
        "spike_factor": spike_factor_scorer,
        "trajectory_signal": trajectory_scorer,
        "builder_ratio": builder_ratio_scorer,
        "outcome_density": outcome_density_scorer,
        "narrative_pull": narrative_pull_scorer,
        "uniqueness_index": uniqueness_index_scorer,
        "credibility_anchors": credibility_anchors_scorer,
        "first_impression": first_impression_scorer,
    }


async def score_standout(
    resume: Resume,
    jd: JobDescription,
    role_type: Optional[str] = None,
    seniority: Optional[str] = None,
    company: Optional[str] = None,
) -> StandoutScoreResult:
    """
    Run all 8 standout scorers and produce a weighted result.

    Mirrors the contract of score_resume() but for human-impression dimensions.
    """
    role_type = role_type or jd.infer_role_type()
    seniority = seniority or resume.seniority_level

    base_weights = get_standout_role_profile(role_type)
    adjusted_weights = apply_standout_seniority_adjustment(base_weights, seniority)

    # Apply company-specific weight overrides if a profile exists
    company_name = company or jd.company
    company_profile = get_company_profile(company_name) if company_name else None
    if company_profile:
        adjusted_weights = apply_company_profile(adjusted_weights, company_profile, "standout")

    scorer_map = _get_standout_scorer_map()

    # Run all scorers concurrently
    scorer_coroutines = [
        scorer_map[dim_id](resume, jd)
        for dim_id in STANDOUT_DIMENSIONS.keys()
    ]
    raw_results = await asyncio.gather(*scorer_coroutines)

    dimension_scores: list[StandoutDimensionScore] = []
    total_score = 0.0
    all_suggestions: list[str] = []

    for dim_id, (raw_score, explanation, issues, suggestions) in zip(
        STANDOUT_DIMENSIONS.keys(), raw_results
    ):
        weight = adjusted_weights[dim_id]
        weighted = raw_score * weight
        total_score += weighted

        priority = _get_priority(raw_score, weight)

        dimension_scores.append(StandoutDimensionScore(
            dimension_id=dim_id,
            dimension_name=STANDOUT_DIMENSIONS[dim_id].name,
            raw_score=raw_score,
            weighted_score=weighted,
            weight=weight,
            explanation=explanation,
            issues=issues,
            suggestions=suggestions,
            priority=priority,
        ))

        # Collect top suggestions for amplification tips
        for s in suggestions:
            all_suggestions.append(s)

    # Sort by biggest improvement opportunity
    dimension_scores.sort(
        key=lambda d: d.weight * (100 - d.raw_score), reverse=True
    )

    # Spike detection: spike_factor raw_score >= 60
    spike_scores = [d for d in dimension_scores if d.dimension_id == "spike_factor"]
    spike_detected = spike_scores[0].raw_score >= 60 if spike_scores else False

    # Top amplification tips: suggestions from highest-impact dimensions
    amplification_tips = all_suggestions[:5]

    return StandoutScoreResult(
        total_score=round(total_score, 1),
        letter_grade=_to_letter_grade(total_score),
        dimension_scores=dimension_scores,
        top_3_issues=[d.issues[0] for d in dimension_scores[:3] if d.issues],
        top_3_wins=[
            d.dimension_name
            for d in sorted(dimension_scores, key=lambda x: x.raw_score, reverse=True)[:3]
        ],
        spike_detected=spike_detected,
        role_type=role_type,
        seniority_level=seniority,
        weights_used=adjusted_weights,
        amplification_tips=amplification_tips,
    )


def _get_priority(raw_score: float, weight: float) -> str:
    impact = weight * (100 - raw_score)
    if impact >= 8.0:
        return "critical"
    if impact >= 5.0:
        return "high"
    if impact >= 2.0:
        return "medium"
    return "low"


def _to_letter_grade(score: float) -> str:
    if score >= 95:
        return "A+"
    if score >= 90:
        return "A"
    if score >= 85:
        return "A-"
    if score >= 80:
        return "B+"
    if score >= 75:
        return "B"
    if score >= 70:
        return "B-"
    if score >= 65:
        return "C+"
    if score >= 60:
        return "C"
    if score >= 55:
        return "C-"
    if score >= 50:
        return "D"
    return "F"
