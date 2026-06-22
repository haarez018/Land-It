"""Demo endpoint: pre-loaded resume + JD scoring for the /demo page."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter

from backend.fixtures.demo_data import DEMO_RESUME_TEXT, DEMO_JD_TEXT
from backend.parsers.resume_parser import parse_resume_text
from backend.parsers.jd_parser import parse_jd
from backend.agents.tailor.agent import TailorAgent, DualScoreResult
from backend.agents.scout.salary_intel import estimate_salary, SalaryEstimate

router = APIRouter()

_cached_demo_result: Optional[dict] = None


async def _compute_demo_score() -> dict:
    global _cached_demo_result
    if _cached_demo_result is not None:
        return _cached_demo_result

    resume = parse_resume_text(DEMO_RESUME_TEXT)
    jd = parse_jd(DEMO_JD_TEXT)

    agent = TailorAgent()
    dual: DualScoreResult = await agent.score_dual(
        resume, jd,
        role_type="software_engineer_backend",
        seniority="senior",
        company="google",
    )

    salary: SalaryEstimate = estimate_salary(resume, jd)

    from backend.api.routes.resume import (
        ScoreResponse, DimensionScoreResponse,
        StandoutScoreResponse, StandoutDimensionScoreResponse,
        DualScoreResponse, CallbackPredictionResponse,
    )

    ats_resp = ScoreResponse(
        total_score=dual.ats.total_score,
        letter_grade=dual.ats.letter_grade,
        dimension_scores=[
            DimensionScoreResponse(
                dimension_id=d.dimension_id, dimension_name=d.dimension_name,
                raw_score=d.raw_score, weighted_score=d.weighted_score,
                weight=d.weight, explanation=d.explanation,
                issues=d.issues, suggestions=d.suggestions, priority=d.priority,
            ) for d in dual.ats.dimension_scores
        ],
        top_3_issues=dual.ats.top_3_issues,
        top_3_wins=dual.ats.top_3_wins,
        predicted_ats_pass=dual.ats.predicted_ats_pass,
        role_type=dual.ats.role_type,
        seniority_level=dual.ats.seniority_level,
        weights_used=dual.ats.weights_used,
    )

    standout_resp = StandoutScoreResponse(
        total_score=dual.standout.total_score,
        letter_grade=dual.standout.letter_grade,
        dimension_scores=[
            StandoutDimensionScoreResponse(
                dimension_id=d.dimension_id, dimension_name=d.dimension_name,
                raw_score=d.raw_score, weighted_score=d.weighted_score,
                weight=d.weight, explanation=d.explanation,
                issues=d.issues, suggestions=d.suggestions, priority=d.priority,
            ) for d in dual.standout.dimension_scores
        ],
        top_3_issues=dual.standout.top_3_issues,
        top_3_wins=dual.standout.top_3_wins,
        spike_detected=dual.standout.spike_detected,
        role_type=dual.standout.role_type,
        seniority_level=dual.standout.seniority_level,
        weights_used=dual.standout.weights_used,
        amplification_tips=dual.standout.amplification_tips,
    )

    callback_resp = None
    if dual.callback_prediction:
        p = dual.callback_prediction
        callback_resp = CallbackPredictionResponse(
            probability=p.probability,
            confidence_interval=p.confidence_interval,
            confidence_level=p.confidence_level,
            top_positive_factors=p.top_positive_factors,
            top_negative_factors=p.top_negative_factors,
            vs_average_applicant=p.vs_average_applicant,
            score_needed_for_50pct=p.score_needed_for_50pct,
            fixes_for_10pct_boost=p.fixes_for_10pct_boost,
            role_type=p.role_type,
            seniority_level=p.seniority_level,
            combined_score=p.combined_score,
            base_rate=p.base_rate,
        )

    dual_resp = DualScoreResponse(
        ats_score=ats_resp,
        standout_score=standout_resp,
        combined_score=dual.combined_score,
        combined_grade=dual.combined_grade,
        total_dimensions=dual.total_dimensions,
        summary=dual.summary,
        callback_prediction=callback_resp,
    )

    salary_resp = {
        "role_type": salary.role_type,
        "seniority": salary.seniority,
        "location": salary.location,
        "company": salary.company,
        "estimated_range": list(salary.estimated_range),
        "estimated_midpoint": salary.estimated_midpoint,
        "user_position_in_range": salary.user_position_in_range,
        "user_estimated_value": salary.user_estimated_value,
        "premium_factors": salary.premium_factors,
        "discount_factors": salary.discount_factors,
        "negotiation_leverage": salary.negotiation_leverage,
        "negotiation_talking_points": salary.negotiation_talking_points,
        "confidence": salary.confidence,
        "confidence_reason": salary.confidence_reason,
    }

    _cached_demo_result = {
        "dual_score": dual_resp.model_dump(),
        "salary": salary_resp,
        "demo_resume_text": DEMO_RESUME_TEXT,
        "demo_jd_text": DEMO_JD_TEXT,
    }

    return _cached_demo_result


@router.get("/score")
async def demo_score():
    """Score the pre-loaded demo resume against the demo JD. Cached after first call."""
    return await _compute_demo_score()
