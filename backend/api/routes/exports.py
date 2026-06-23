"""Export endpoints — generate downloadable PDF/HTML reports."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from backend.auth_deps import get_current_user_id
from backend.db import get_db

router = APIRouter()


class ScoreReportRequest(BaseModel):
    resume_id: str
    jd_text: str
    include_salary: bool = False


class DiffReportRequest(BaseModel):
    resume_id: str
    jd_text: str


class CoachingReportRequest(BaseModel):
    session_id: str


@router.post("/score-report")
async def export_score_report(
    request: ScoreReportRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Generate a 22-dimension score report as PDF/HTML."""
    from backend.api.routes.resume import load_user_resume
    from backend.parsers.jd_parser import parse_jd
    from backend.agents.tailor.agent import TailorAgent
    from backend.utils.proof_exporter import generate_score_report

    resume = load_user_resume(request.resume_id, user_id)
    jd = parse_jd(request.jd_text)

    agent = TailorAgent()
    dual = await agent.score_dual(resume, jd)

    salary = None
    if request.include_salary:
        from backend.agents.scout.salary_intel import estimate_salary
        salary = estimate_salary(resume, jd, standout_result=dual.standout)

    content, content_type = generate_score_report(dual, resume, jd, salary=salary)
    ext = "pdf" if "pdf" in content_type else "html"

    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="score-report.{ext}"'},
    )


@router.post("/diff-report")
async def export_diff_report(
    request: DiffReportRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Generate a tailoring diff report as PDF/HTML."""
    from backend.api.routes.resume import load_user_resume
    from backend.parsers.jd_parser import parse_jd
    from backend.agents.tailor.agent import TailorAgent
    from backend.utils.proof_exporter import generate_diff_report

    resume = load_user_resume(request.resume_id, user_id)
    jd = parse_jd(request.jd_text)

    agent = TailorAgent()
    result = await agent.tailor(resume, jd)

    content, content_type = generate_diff_report(
        original_resume=result.original_resume.raw_text,
        tailored_resume=result.rewritten_resume.raw_text,
        change_log=result.rewrite_result.change_log,
        score_before=result.score_before.total_score,
        score_after=result.score_after.total_score,
    )
    ext = "pdf" if "pdf" in content_type else "html"

    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="diff-report.{ext}"'},
    )


@router.post("/coaching-report")
async def export_coaching_report(request: CoachingReportRequest):
    """Generate a mock interview report as PDF/HTML."""
    from backend.agents.coach.agent import CoachAgent
    from backend.utils.proof_exporter import generate_coaching_report

    coach = CoachAgent()
    summary = await coach.get_summary(request.session_id)

    if not summary:
        raise HTTPException(404, "Session not found or no answers recorded")

    summary_dict = {
        "session_id": summary.session_id,
        "score_pct": summary.score_pct,
        "grade_letter": summary.grade_letter,
        "questions_answered": summary.questions_answered,
        "questions_skipped": summary.questions_skipped,
        "total_questions": summary.total_questions,
        "strongest_dimension": summary.strongest_dimension,
        "weakest_dimension": summary.weakest_dimension,
        "all_strengths": summary.all_strengths,
        "all_improvements": summary.all_improvements,
        "duration_seconds": summary.duration_seconds,
        "results": [],
    }

    content, content_type = generate_coaching_report(summary_dict)
    ext = "pdf" if "pdf" in content_type else "html"

    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="coaching-report.{ext}"'},
    )


@router.post("/analytics-report")
async def export_analytics_report(user_id: str = Depends(get_current_user_id)):
    """Generate a job search analytics snapshot as PDF/HTML."""
    from backend.agents.planner.strategy import ApplicationEntry
    from backend.agents.planner.analytics import compute_analytics
    from backend.utils.proof_exporter import generate_analytics_report

    rows = get_db().table("applications").select("*").eq("user_id", user_id).execute().data
    applications = [
        ApplicationEntry(
            id=r["id"], job_id=r["job_id"], status=r.get("status", "submitted"),
            fit_score=r.get("fit_score") or 0.0,
            ats_score_before=r.get("ats_score_before"),
            ats_score_after=r.get("ats_score_after"),
            priority=r.get("priority") or 0,
            submitted_at=r.get("submitted_at"),
            notes=r.get("notes") or "",
        )
        for r in rows
    ]
    analytics = compute_analytics(applications)

    content, content_type = generate_analytics_report(analytics)
    ext = "pdf" if "pdf" in content_type else "html"

    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="analytics-report.{ext}"'},
    )


@router.get("/formats")
async def export_formats():
    """Check which export formats are available."""
    from backend.utils.proof_exporter import is_pdf_available

    pdf = is_pdf_available()
    formats = ["html"]
    if pdf:
        formats.insert(0, "pdf")

    return {"pdf_available": pdf, "formats": formats}
