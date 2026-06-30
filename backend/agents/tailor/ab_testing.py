"""
Resume A/B Testing Engine.

Scores two resume versions against the same JD on all 22 dimensions,
produces per-dimension comparison, winner determination, section-based
merge suggestions, and a plain-English recommendation.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional

from backend.parsers.schemas import Resume, JobDescription
from backend.agents.tailor.weightage.scorer_engine import score_resume, ATSScoreResult
from backend.agents.tailor.standout.engine import score_standout, StandoutScoreResult
from backend.agents.tailor.prediction.interview_predictor import predict_callback, CallbackPrediction


# ── Data models ──────────────────────────────────────────────────────────────

@dataclass
class DimensionComparison:
    """Per-dimension comparison between version A and version B."""
    dimension_id: str
    dimension_name: str
    score_a: float
    score_b: float
    delta: float              # absolute difference
    winner: str               # "A" | "B" | "tie" — tie if delta < 3
    weight: float
    weighted_impact: float    # How much the winner's advantage matters


@dataclass
class MergeSuggestion:
    """Section-level merge suggestion."""
    section: str              # "summary" | "work_experience" | "skills" | "education"
    recommendation: str       # "use_a" | "use_b" | "combine" | "either"
    reason: str


@dataclass
class ABTestResult:
    """Complete A/B test result comparing two resume versions."""
    version_a_id: str
    version_b_id: str
    jd_id: str

    # Scores
    version_a_ats: float
    version_b_ats: float
    version_a_standout: float
    version_b_standout: float
    version_a_combined: float
    version_b_combined: float
    version_a_callback: float
    version_b_callback: float

    # Winner
    overall_winner: str       # "A" | "B" | "tie" — tie if combined diff < 2
    win_margin: float         # percentage difference

    # Per-dimension breakdown (all 22)
    dimension_comparisons: list[DimensionComparison]

    # Advantage lists (dims where winner leads by >5 points)
    a_advantages: list[str]
    b_advantages: list[str]

    # Section-based merge suggestions
    merge_suggestions: list[MergeSuggestion]

    # Plain-English recommendation
    recommendation: str

    # Callback predictions
    callback_a: CallbackPrediction
    callback_b: CallbackPrediction

    # Context
    role_type: str
    seniority_level: str


# ── Helpers ──────────────────────────────────────────────────────────────────

def _compare_dimensions(
    dims_a: list,
    dims_b: list,
) -> list[DimensionComparison]:
    """Compare matching dimensions from two score results."""
    a_map = {d.dimension_id: d for d in dims_a}
    b_map = {d.dimension_id: d for d in dims_b}

    comparisons = []
    for dim_id in a_map:
        if dim_id not in b_map:
            continue
        da = a_map[dim_id]
        db = b_map[dim_id]
        raw_delta = db.raw_score - da.raw_score
        abs_delta = abs(raw_delta)
        weight = (da.weight + db.weight) / 2

        if abs_delta < 3.0:
            winner = "tie"
        elif raw_delta > 0:
            winner = "B"
        else:
            winner = "A"

        comparisons.append(DimensionComparison(
            dimension_id=dim_id,
            dimension_name=da.dimension_name,
            score_a=da.raw_score,
            score_b=db.raw_score,
            delta=round(abs_delta, 1),
            winner=winner,
            weight=round(weight, 4),
            weighted_impact=round(abs_delta * weight, 2),
        ))

    comparisons.sort(key=lambda c: c.weighted_impact, reverse=True)
    return comparisons


def _section_score(
    comps_by_id: dict[str, DimensionComparison],
    dim_ids: list[str],
    version: str,
) -> float:
    """Average raw score for a set of dimension IDs for a given version."""
    scores = []
    for dim_id in dim_ids:
        comp = comps_by_id.get(dim_id)
        if comp:
            scores.append(comp.score_a if version == "A" else comp.score_b)
    return sum(scores) / len(scores) if scores else 0.0


def _generate_section_merge_suggestions(
    all_comps: list[DimensionComparison],
) -> list[MergeSuggestion]:
    """Generate section-based merge suggestions."""
    comps_by_id = {c.dimension_id: c for c in all_comps}

    # Map sections to the dimensions that drive them
    section_dims = {
        "summary": ["first_impression", "narrative_pull"],
        "work_experience": ["quantified_impact", "outcome_density", "action_verb_strength", "builder_ratio"],
        "skills": ["keyword_density", "tech_stack_alignment", "skill_depth"],
        "education": ["education_relevance", "credibility_anchors"],
    }

    suggestions = []
    for section, dim_ids in section_dims.items():
        score_a = _section_score(comps_by_id, dim_ids, "A")
        score_b = _section_score(comps_by_id, dim_ids, "B")
        diff = score_a - score_b

        if abs(diff) < 3.0:
            if score_a >= 70:
                rec = "either"
                reason = f"Both versions score similarly on {section} ({score_a:.0f} vs {score_b:.0f})"
            else:
                rec = "combine"
                reason = f"Both score low on {section} ({score_a:.0f} vs {score_b:.0f}) — merge the best of both"
        elif diff > 0:
            rec = "use_a"
            reason = f"Version A's {section} is stronger ({score_a:.0f} vs {score_b:.0f})"
        else:
            rec = "use_b"
            reason = f"Version B's {section} is stronger ({score_b:.0f} vs {score_a:.0f})"

        suggestions.append(MergeSuggestion(
            section=section,
            recommendation=rec,
            reason=reason,
        ))

    return suggestions


def _build_recommendation(
    overall_winner: str,
    combined_a: float,
    combined_b: float,
    a_advantages: list[str],
    b_advantages: list[str],
    merge_suggestions: list[MergeSuggestion],
) -> str:
    """Build a plain-English recommendation string."""
    if overall_winner == "tie":
        parts = ["Both versions perform similarly."]
        a_sections = [s.section for s in merge_suggestions if s.recommendation == "use_a"]
        b_sections = [s.section for s in merge_suggestions if s.recommendation == "use_b"]
        if a_sections:
            parts.append(f"Take Version A's {', '.join(a_sections)}.")
        if b_sections:
            parts.append(f"Take Version B's {', '.join(b_sections)}.")
        return " ".join(parts)

    winner_label = f"Version {overall_winner}"
    winner_score = combined_a if overall_winner == "A" else combined_b
    loser_score = combined_b if overall_winner == "A" else combined_a
    loser = "B" if overall_winner == "A" else "A"
    pct = round((winner_score - loser_score) / loser_score * 100) if loser_score > 0 else 0

    parts = [
        f"Use {winner_label} — it scores {pct}% higher overall "
        f"({winner_score} vs {loser_score})."
    ]

    # Name the winner's top advantages
    winner_advs = a_advantages if overall_winner == "A" else b_advantages
    if winner_advs:
        parts.append(f"Strongest advantages: {', '.join(winner_advs[:3])}.")

    # Suggest taking the loser's better sections
    loser_sections = [
        s.section for s in merge_suggestions
        if s.recommendation == f"use_{loser.lower()}"
    ]
    if loser_sections:
        parts.append(f"Consider taking Version {loser}'s {', '.join(loser_sections)}.")

    return " ".join(parts)


# ── Main function ────────────────────────────────────────────────────────────

async def ab_test_resumes(
    version_a: Resume,
    version_b: Resume,
    jd: JobDescription,
    *,
    role_type: Optional[str] = None,
    seniority: Optional[str] = None,
    company: Optional[str] = None,
    user_id: Optional[str] = None,
    save_result: bool = True,
) -> ABTestResult:
    """
    A/B test two resume versions against the same JD.

    Scores both on all 22 dimensions (14 ATS + 8 Standout), compares
    per-dimension, generates section-based merge suggestions, and builds
    a plain-English recommendation.
    """
    # 1. Score both versions in parallel (4 coroutines)
    ats_a, standout_a, ats_b, standout_b = await asyncio.gather(
        score_resume(version_a, jd, role_type=role_type, seniority=seniority, company=company),
        score_standout(version_a, jd, role_type=role_type, seniority=seniority, company=company),
        score_resume(version_b, jd, role_type=role_type, seniority=seniority, company=company),
        score_standout(version_b, jd, role_type=role_type, seniority=seniority, company=company),
    )

    # 2. Combined scores (60% ATS + 40% Standout)
    combined_a = round(ats_a.total_score * 0.6 + standout_a.total_score * 0.4, 1)
    combined_b = round(ats_b.total_score * 0.6 + standout_b.total_score * 0.4, 1)

    # 3. Callback predictions
    callback_a = predict_callback(ats_a, standout_a)
    callback_b = predict_callback(ats_b, standout_b)

    # 4. Per-dimension comparisons (all 22)
    ats_comps = _compare_dimensions(ats_a.dimension_scores, ats_b.dimension_scores)
    standout_comps = _compare_dimensions(standout_a.dimension_scores, standout_b.dimension_scores)
    all_comps = ats_comps + standout_comps

    # 5. Advantages (dims where winner leads by >5 points)
    a_advantages = [
        c.dimension_name for c in all_comps
        if c.winner == "A" and c.delta > 5
    ]
    b_advantages = [
        c.dimension_name for c in all_comps
        if c.winner == "B" and c.delta > 5
    ]

    # 6. Overall winner (tie if < 2 points combined)
    margin = abs(combined_a - combined_b)
    win_margin_pct = round(margin / min(combined_a, combined_b) * 100, 1) if min(combined_a, combined_b) > 0 else 0
    if margin < 2.0:
        overall_winner = "tie"
    elif combined_a > combined_b:
        overall_winner = "A"
    else:
        overall_winner = "B"

    # 7. Section-based merge suggestions
    merge_suggestions = _generate_section_merge_suggestions(all_comps)

    # 8. Recommendation
    recommendation = _build_recommendation(
        overall_winner, combined_a, combined_b,
        a_advantages, b_advantages, merge_suggestions,
    )

    result = ABTestResult(
        version_a_id=version_a.id,
        version_b_id=version_b.id,
        jd_id=jd.id,
        version_a_ats=ats_a.total_score,
        version_b_ats=ats_b.total_score,
        version_a_standout=standout_a.total_score,
        version_b_standout=standout_b.total_score,
        version_a_combined=combined_a,
        version_b_combined=combined_b,
        version_a_callback=callback_a.probability,
        version_b_callback=callback_b.probability,
        overall_winner=overall_winner,
        win_margin=win_margin_pct,
        dimension_comparisons=all_comps,
        a_advantages=a_advantages,
        b_advantages=b_advantages,
        merge_suggestions=merge_suggestions,
        recommendation=recommendation,
        callback_a=callback_a,
        callback_b=callback_b,
        role_type=ats_a.role_type,
        seniority_level=ats_a.seniority_level,
    )

    if save_result and user_id:
        try:
            from backend.db import get_db
            get_db().table("ab_tests").insert({
                "user_id": user_id,
                "resume_a_id": version_a.id,
                "resume_b_id": version_b.id,
                "job_id": jd.id,
                "score_a": combined_a,
                "score_b": combined_b,
                "winner": overall_winner,
                "dimensions_a": [
                    {"id": c.dimension_id, "name": c.dimension_name, "score": c.score_a, "weight": c.weight}
                    for c in all_comps
                ],
                "dimensions_b": [
                    {"id": c.dimension_id, "name": c.dimension_name, "score": c.score_b, "weight": c.weight}
                    for c in all_comps
                ],
            }).execute()
        except Exception:
            pass  # DB errors must not block the scoring result

    return result
