"""
TailorAgent: rewrites resumes to maximize ATS score against a specific JD.

Pipeline: parse → score_before → rewrite (6 passes) → score_after → diff → return
Now also produces a Standout score (8 human-impression dimensions) alongside the ATS score.
"""

from __future__ import annotations

import asyncio
import copy
from dataclasses import dataclass, field
from typing import Optional

from backend.parsers.schemas import Resume, JobDescription
from backend.agents.tailor.resume_rewriter import rewrite_resume, RewriteResult
from backend.agents.tailor.diff_generator import generate_diff, ResumeDiff
from backend.agents.tailor.weightage.scorer_engine import score_resume, ATSScoreResult
from backend.agents.tailor.standout.engine import score_standout, StandoutScoreResult
from backend.agents.tailor.prediction.interview_predictor import (
    predict_callback,
    CallbackPrediction,
)


@dataclass
class DualScoreResult:
    """Combined 22-dimension score: 14 ATS + 8 Standout + callback prediction."""
    ats: ATSScoreResult
    standout: StandoutScoreResult
    combined_score: float          # weighted blend of both
    combined_grade: str
    total_dimensions: int = 22
    summary: str = ""
    callback_prediction: Optional[CallbackPrediction] = None


def _compute_dual_score(ats: ATSScoreResult, standout: StandoutScoreResult) -> DualScoreResult:
    """Compute combined score: 60% ATS + 40% Standout (ATS matters more for getting past the robot)."""
    combined = round(ats.total_score * 0.6 + standout.total_score * 0.4, 1)
    grade = _to_letter_grade(combined)

    # Build a human-readable summary
    if ats.predicted_ats_pass and standout.spike_detected:
        summary = "Strong candidate: passes ATS filters AND has standout spikes"
    elif ats.predicted_ats_pass and not standout.spike_detected:
        summary = "ATS-safe but blends in — needs stronger differentiators"
    elif not ats.predicted_ats_pass and standout.spike_detected:
        summary = "Impressive profile but may not pass ATS filters — optimize keywords"
    else:
        summary = "Needs work on both ATS optimization and human-impression factors"

    # Predict callback probability
    prediction = predict_callback(ats, standout)

    return DualScoreResult(
        ats=ats,
        standout=standout,
        combined_score=combined,
        combined_grade=grade,
        summary=summary,
        callback_prediction=prediction,
    )


@dataclass
class TailorResult:
    """Complete result from the tailor pipeline."""
    original_resume: Resume
    rewritten_resume: Resume
    score_before: ATSScoreResult
    score_after: ATSScoreResult
    diff: ResumeDiff
    rewrite_result: RewriteResult
    improvement: float  # score_after - score_before
    dual_score_before: Optional[DualScoreResult] = None
    dual_score_after: Optional[DualScoreResult] = None


class TailorAgent:
    """Orchestrates the full resume tailoring pipeline."""

    async def run(self, state: dict) -> dict:
        """
        LangGraph-compatible run method.

        Expected state keys:
            - resume: Resume object
            - jd: JobDescription object

        Returns updated state with:
            - tailor_result: TailorResult
            - ats_score_before: float
            - ats_score_after: float
            - standout_score_before: float
            - standout_score_after: float
            - tailored_resume: Resume
        """
        resume: Resume = state["resume"]
        jd: JobDescription = state["jd"]

        result = await self.tailor(resume, jd)

        return {
            **state,
            "tailor_result": result,
            "ats_score_before": result.score_before.total_score,
            "ats_score_after": result.score_after.total_score,
            "standout_score_before": (
                result.dual_score_before.standout.total_score
                if result.dual_score_before else None
            ),
            "standout_score_after": (
                result.dual_score_after.standout.total_score
                if result.dual_score_after else None
            ),
            "tailored_resume": result.rewritten_resume,
            "tailor_change_log": result.rewrite_result.change_log,
        }

    async def tailor(
        self,
        resume: Resume,
        jd: JobDescription,
        *,
        skip_passes: Optional[set[str]] = None,
    ) -> TailorResult:
        """
        Full tailor pipeline: score → rewrite → re-score → diff.

        Now runs both ATS (14-dim) and Standout (8-dim) scoring in parallel
        for a 22-dimension dual score.

        Args:
            resume: Parsed resume to tailor
            jd: Target job description
            skip_passes: Optional set of pass names to skip

        Returns:
            TailorResult with scores, diff, and rewrite details
        """
        # Step 1: Score the original resume (ATS + Standout in parallel)
        original = copy.deepcopy(resume)
        ats_before, standout_before = await asyncio.gather(
            score_resume(original, jd),
            score_standout(original, jd),
        )
        dual_before = _compute_dual_score(ats_before, standout_before)

        # Step 2: Run the 6-pass rewriter
        rewrite_result = await rewrite_resume(original, jd, skip_passes=skip_passes)

        # Step 3: Score the rewritten resume (ATS + Standout in parallel)
        ats_after, standout_after = await asyncio.gather(
            score_resume(rewrite_result.rewritten_resume, jd),
            score_standout(rewrite_result.rewritten_resume, jd),
        )
        dual_after = _compute_dual_score(ats_after, standout_after)

        # Step 4: Generate the diff
        diff = generate_diff(
            original,
            rewrite_result.rewritten_resume,
            rewrite_result.change_log,
            score_before=ats_before.total_score,
            score_after=ats_after.total_score,
        )

        return TailorResult(
            original_resume=original,
            rewritten_resume=rewrite_result.rewritten_resume,
            score_before=ats_before,
            score_after=ats_after,
            diff=diff,
            rewrite_result=rewrite_result,
            improvement=round(ats_after.total_score - ats_before.total_score, 1),
            dual_score_before=dual_before,
            dual_score_after=dual_after,
        )

    async def score_dual(
        self,
        resume: Resume,
        jd: JobDescription,
        *,
        role_type: Optional[str] = None,
        seniority: Optional[str] = None,
        company: Optional[str] = None,
    ) -> DualScoreResult:
        """
        Score a resume on all 22 dimensions (14 ATS + 8 Standout)
        without running the rewrite pipeline.
        """
        ats_result, standout_result = await asyncio.gather(
            score_resume(resume, jd, role_type=role_type, seniority=seniority, company=company),
            score_standout(resume, jd, role_type=role_type, seniority=seniority, company=company),
        )
        return _compute_dual_score(ats_result, standout_result)


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
