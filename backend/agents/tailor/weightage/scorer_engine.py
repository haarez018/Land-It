"""Master scoring orchestrator: runs all 14 dimensions and produces ATSScoreResult."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from backend.parsers.schemas import Resume, JobDescription
from .dimensions import DIMENSIONS
from .role_profiles import get_role_profile
from .seniority_matrix import apply_seniority_adjustment
from .company_profiles import get_company_profile, apply_company_profile


@dataclass
class DimensionScore:
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
class ATSScoreResult:
    total_score: float
    letter_grade: str
    dimension_scores: list[DimensionScore]
    top_3_issues: list[str]
    top_3_wins: list[str]
    predicted_ats_pass: bool
    role_type: str
    seniority_level: str
    weights_used: dict[str, float]
    changed_dimensions: Optional[list[str]] = None


def _get_scorer_map():
    from backend.agents.tailor.ats_scorer import (
        keyword_density_scorer,
        skill_depth_scorer,
        tech_stack_scorer,
        experience_relevance_scorer,
        quantified_impact_scorer,
        action_verb_scorer,
        section_ordering_scorer,
        bullet_quality_scorer,
        ats_parsability_scorer,
        seniority_calibration_scorer,
        domain_knowledge_scorer,
        education_relevance_scorer,
        content_alignment_scorer,
        voice_alignment_scorer,
    )
    return {
        "keyword_density": keyword_density_scorer,
        "skill_depth": skill_depth_scorer,
        "tech_stack_alignment": tech_stack_scorer,
        "experience_relevance": experience_relevance_scorer,
        "quantified_impact": quantified_impact_scorer,
        "action_verb_strength": action_verb_scorer,
        "section_ordering": section_ordering_scorer,
        "bullet_quality": bullet_quality_scorer,
        "ats_parsability": ats_parsability_scorer,
        "seniority_calibration": seniority_calibration_scorer,
        "domain_knowledge": domain_knowledge_scorer,
        "education_relevance": education_relevance_scorer,
        "semantic_similarity": content_alignment_scorer,
        "voice_alignment": voice_alignment_scorer,
    }


async def score_resume(
    resume: Resume,
    jd: JobDescription,
    role_type: Optional[str] = None,
    seniority: Optional[str] = None,
    company: Optional[str] = None,
) -> ATSScoreResult:
    role_type = role_type or jd.infer_role_type()
    seniority = seniority or resume.seniority_level

    base_weights = get_role_profile(role_type)
    adjusted_weights = apply_seniority_adjustment(base_weights, seniority)

    # Apply company-specific weight overrides if a profile exists
    company_name = company or jd.company
    company_profile = get_company_profile(company_name) if company_name else None
    if company_profile:
        adjusted_weights = apply_company_profile(adjusted_weights, company_profile, "ats")

    scorer_map = _get_scorer_map()

    raw_results = [scorer_map[dim_id](resume, jd) for dim_id in DIMENSIONS.keys()]

    dimension_scores: list[DimensionScore] = []
    total_score = 0.0

    for dim_id, (raw_score, explanation, issues, suggestions) in zip(
        DIMENSIONS.keys(), raw_results
    ):
        weight = adjusted_weights[dim_id]
        weighted = raw_score * weight
        total_score += weighted

        priority = _get_priority(raw_score, weight)

        dimension_scores.append(DimensionScore(
            dimension_id=dim_id,
            dimension_name=DIMENSIONS[dim_id].name,
            raw_score=raw_score,
            weighted_score=weighted,
            weight=weight,
            explanation=explanation,
            issues=issues,
            suggestions=suggestions,
            priority=priority,
        ))

    dimension_scores.sort(key=lambda d: d.weight * (100 - d.raw_score), reverse=True)

    return ATSScoreResult(
        total_score=round(total_score, 1),
        letter_grade=_to_letter_grade(total_score),
        dimension_scores=dimension_scores,
        top_3_issues=[d.issues[0] for d in dimension_scores[:3] if d.issues],
        top_3_wins=[
            d.dimension_name
            for d in sorted(dimension_scores, key=lambda x: x.raw_score, reverse=True)[:3]
        ],
        predicted_ats_pass=total_score >= 70,
        role_type=role_type,
        seniority_level=seniority,
        weights_used=adjusted_weights,
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
