"""Planner strategy and weekly report endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.agents.planner.agent import PlannerAgent
from backend.agents.planner.strategy import (
    ApplicationEntry,
    WeeklyGoal,
    get_goal,
    set_goal,
    get_reports,
)
from backend.auth_deps import get_current_user_id
from backend.db import get_db

router = APIRouter()

_agent = PlannerAgent()


class GoalRequest(BaseModel):
    target_applications: int = 10
    target_role: str = ""
    target_locations: list[str] = []
    preferences: str = ""


class ReportResponse(BaseModel):
    id: str
    week_of: str
    summary: str
    applications_target: int
    applications_sent: int
    interviews_scheduled: int
    avg_ats_score: float
    top_opportunities: list[dict]
    action_items: list[str]
    wins: list[str]
    created_at: str


class StatsResponse(BaseModel):
    applications_this_week: int
    interviews_scheduled: int
    avg_ats_score: float
    cover_letters_generated: int
    coaching_sessions: int
    total_applications: int


def _db_rows_to_entries(rows: list[dict]) -> list[ApplicationEntry]:
    return [
        ApplicationEntry(
            id=r["id"],
            job_id=r["job_id"],
            status=r.get("status", "submitted"),
            fit_score=r.get("fit_score") or 0.0,
            ats_score_before=r.get("ats_score_before"),
            ats_score_after=r.get("ats_score_after"),
            priority=r.get("priority") or 0,
            submitted_at=r.get("submitted_at"),
            notes=r.get("notes") or "",
        )
        for r in rows
    ]


@router.get("/report", response_model=Optional[ReportResponse])
async def get_weekly_report(user_id: str = Depends(get_current_user_id)):
    """Get the latest weekly report, or generate one if none exists."""
    reports = get_reports()
    if reports:
        r = reports[0]
        return ReportResponse(
            id=r.id,
            week_of=r.week_of,
            summary=r.summary,
            applications_target=r.applications_target,
            applications_sent=r.applications_sent,
            interviews_scheduled=r.interviews_scheduled,
            avg_ats_score=r.avg_ats_score,
            top_opportunities=r.top_opportunities,
            action_items=r.action_items,
            wins=r.wins,
            created_at=r.created_at,
        )

    # Generate a fresh report from Supabase data
    rows = get_db().table("applications").select("*").eq("user_id", user_id).execute().data
    apps = _db_rows_to_entries(rows)
    goal = get_goal()
    result = await _agent.generate_report(apps, goal)
    r = result.report

    return ReportResponse(
        id=r.id,
        week_of=r.week_of,
        summary=r.summary,
        applications_target=r.applications_target,
        applications_sent=r.applications_sent,
        interviews_scheduled=r.interviews_scheduled,
        avg_ats_score=r.avg_ats_score,
        top_opportunities=r.top_opportunities,
        action_items=r.action_items,
        wins=r.wins,
        created_at=r.created_at,
    )


@router.post("/goal")
async def set_weekly_goal(request: GoalRequest):
    """Set the user's weekly job search goal."""
    goal = WeeklyGoal(
        target_applications=request.target_applications,
        target_role=request.target_role,
        target_locations=request.target_locations,
        preferences=request.preferences,
    )
    set_goal("", goal)
    return {"status": "ok", "goal": request.model_dump()}


@router.get("/history")
async def get_history():
    """Get past weekly reports."""
    reports = get_reports()
    return [
        ReportResponse(
            id=r.id,
            week_of=r.week_of,
            summary=r.summary,
            applications_target=r.applications_target,
            applications_sent=r.applications_sent,
            interviews_scheduled=r.interviews_scheduled,
            avg_ats_score=r.avg_ats_score,
            top_opportunities=r.top_opportunities,
            action_items=r.action_items,
            wins=r.wins,
            created_at=r.created_at,
        )
        for r in reports
    ]


@router.get("/stats", response_model=StatsResponse)
async def get_stats(user_id: str = Depends(get_current_user_id)):
    """Get dashboard statistics."""
    rows = get_db().table("applications").select("*").eq("user_id", user_id).execute().data
    apps = _db_rows_to_entries(rows)
    submitted = [a for a in apps if a.status == "submitted"]
    interviewing = [a for a in apps if a.status == "interviewing"]

    ats_scores = [
        a.ats_score_after for a in apps
        if a.ats_score_after is not None and a.ats_score_after > 0
    ]
    avg_ats = sum(ats_scores) / len(ats_scores) if ats_scores else 0

    return StatsResponse(
        applications_this_week=len(submitted),
        interviews_scheduled=len(interviewing),
        avg_ats_score=round(avg_ats, 1),
        cover_letters_generated=0,  # TODO: track from pitcher
        coaching_sessions=0,  # TODO: track from coach
        total_applications=len(apps),
    )


@router.post("/run-weekly")
async def trigger_weekly_planner():
    """Manually trigger the weekly planner pipeline (for testing or on-demand use)."""
    from backend.tasks.scheduler import run_weekly_planner

    result = await run_weekly_planner()
    return {"status": "ok", "result": result}
