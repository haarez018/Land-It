"""Batch Scorer: score one resume against multiple JDs concurrently."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional

from backend.parsers.schemas import Resume, JobDescription
from backend.agents.tailor.agent import TailorAgent, DualScoreResult


@dataclass
class BatchScoreEntry:
    jd_id: str
    jd_title: str
    jd_company: str
    ats_score: float
    standout_score: float
    combined_score: float
    callback_probability: float
    tier: str
    top_gap: str
    company_profile_used: str


@dataclass
class BatchScoreResult:
    resume_id: str
    entries: list[BatchScoreEntry]
    best_fit: Optional[BatchScoreEntry]
    worst_fit: Optional[BatchScoreEntry]
    highest_callback: Optional[BatchScoreEntry]
    avg_combined_score: float
    avg_callback_probability: float
    common_gaps: list[str]
    strongest_dimension_overall: str
    weakest_dimension_overall: str
    recommendation: str


def _tier_from_score(score: float) -> str:
    if score >= 85:
        return "Standout"
    if score >= 70:
        return "Strong"
    if score >= 55:
        return "Solid"
    if score >= 40:
        return "Needs Work"
    return "Weak"


def _top_gap(dual: DualScoreResult) -> str:
    all_dims = list(dual.ats.dimension_scores) + list(dual.standout.dimension_scores)
    if not all_dims:
        return "None"
    worst = min(all_dims, key=lambda d: d.raw_score)
    return f"{worst.dimension_name}: {worst.raw_score:.0f}"


async def batch_score(
    resume: Resume,
    jds: list[JobDescription],
    role_type: str | None = None,
    seniority: str | None = None,
) -> BatchScoreResult:
    agent = TailorAgent()

    async def _score_one(jd: JobDescription) -> tuple[JobDescription, DualScoreResult]:
        company = None
        company_lower = jd.company.lower()
        for known in ["google", "stripe", "netflix", "meta", "faang"]:
            if known in company_lower:
                company = known
                break
        result = await agent.score_dual(
            resume, jd,
            role_type=role_type,
            seniority=seniority,
            company=company,
        )
        return jd, result

    results = await asyncio.gather(*[_score_one(jd) for jd in jds])

    entries: list[BatchScoreEntry] = []
    all_issue_lists: list[list[str]] = []
    all_dims: dict[str, list[float]] = {}

    for jd, dual in results:
        cb_prob = dual.callback_prediction.probability if dual.callback_prediction else 0.0
        company_used = "none"
        company_lower = jd.company.lower()
        for known in ["google", "stripe", "netflix", "meta", "faang"]:
            if known in company_lower:
                company_used = known
                break

        entry = BatchScoreEntry(
            jd_id=jd.id,
            jd_title=jd.title,
            jd_company=jd.company,
            ats_score=dual.ats.total_score,
            standout_score=dual.standout.total_score,
            combined_score=dual.combined_score,
            callback_probability=cb_prob,
            tier=_tier_from_score(dual.combined_score),
            top_gap=_top_gap(dual),
            company_profile_used=company_used,
        )
        entries.append(entry)

        all_issue_lists.append(dual.ats.top_3_issues + dual.standout.top_3_issues)

        for d in dual.ats.dimension_scores:
            all_dims.setdefault(d.dimension_name, []).append(d.raw_score)
        for d in dual.standout.dimension_scores:
            all_dims.setdefault(d.dimension_name, []).append(d.raw_score)

    best = max(entries, key=lambda e: e.combined_score) if entries else None
    worst = min(entries, key=lambda e: e.combined_score) if entries else None
    highest_cb = max(entries, key=lambda e: e.callback_probability) if entries else None

    avg_combined = sum(e.combined_score for e in entries) / len(entries) if entries else 0
    avg_callback = sum(e.callback_probability for e in entries) / len(entries) if entries else 0

    # Find issues appearing in 3+ JDs
    issue_counts: dict[str, int] = {}
    for issues in all_issue_lists:
        for issue in issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
    threshold = min(3, max(1, len(jds) // 2))
    common_gaps = [issue for issue, count in issue_counts.items() if count >= threshold]

    dim_avgs = {name: sum(scores) / len(scores) for name, scores in all_dims.items() if scores}
    strongest = max(dim_avgs, key=dim_avgs.get) if dim_avgs else "N/A"
    weakest = min(dim_avgs, key=dim_avgs.get) if dim_avgs else "N/A"

    rec = ""
    if best:
        rec = f"Strongest fit: {best.jd_title} at {best.jd_company} ({best.combined_score:.0f})."
        if worst and worst.combined_score < best.combined_score - 15:
            rec += f" Weakest: {worst.jd_title} ({worst.combined_score:.0f})."
        if common_gaps:
            rec += f" Common gap across roles: {common_gaps[0]}."

    return BatchScoreResult(
        resume_id=resume.id,
        entries=entries,
        best_fit=best,
        worst_fit=worst,
        highest_callback=highest_cb,
        avg_combined_score=round(avg_combined, 1),
        avg_callback_probability=round(avg_callback, 4),
        common_gaps=common_gaps,
        strongest_dimension_overall=strongest,
        weakest_dimension_overall=weakest,
        recommendation=rec,
    )
