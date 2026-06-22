"""
Weekly strategy logic: prioritize jobs, sequence agent tasks, generate reports.

Uses Claude when available for intelligent strategy narrative; falls back to
heuristic logic when the API key is absent.
"""

from __future__ import annotations

import copy
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Optional

from backend.parsers.schemas import Resume, JobDescription


@dataclass
class ApplicationEntry:
    """An application in the pipeline."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    job_id: str = ""
    jd: Optional[JobDescription] = None
    status: str = "queued"  # queued | tailoring | ready | submitted | interviewing | offer | rejected
    fit_score: float = 0.0
    ats_score_before: Optional[float] = None
    ats_score_after: Optional[float] = None
    priority: int = 0  # 1=highest, 0=unranked
    submitted_at: Optional[str] = None
    follow_up_due: Optional[str] = None
    notes: str = ""


@dataclass
class WeeklyGoal:
    """User's weekly job search goal."""
    target_applications: int = 10
    target_role: str = ""
    target_locations: list[str] = field(default_factory=list)
    preferences: str = ""


@dataclass
class AgentTask:
    """A task to be executed by an agent."""
    agent: str  # tailor | pitcher | coach | scout
    action: str
    target_id: str  # application_id or JD id
    priority: int
    reason: str


@dataclass
class WeeklyReport:
    """Generated weekly strategy report."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    week_of: str = ""
    summary: str = ""
    applications_target: int = 0
    applications_sent: int = 0
    interviews_scheduled: int = 0
    avg_ats_score: float = 0.0
    top_opportunities: list[dict] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    wins: list[str] = field(default_factory=list)
    agent_tasks: list[AgentTask] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


# ── Strategy logic ────────────────────────────────────────────────────────


def prioritize_applications(
    applications: list[ApplicationEntry],
    *,
    top_n: int = 10,
) -> list[ApplicationEntry]:
    """
    Rank applications by fit score and status urgency.

    Priority formula: fit_score * status_weight
    - queued: 1.0 (needs tailoring)
    - tailoring: 1.2 (already started)
    - ready: 1.5 (ready to submit — highest urgency)
    - submitted: 0.3 (waiting)
    - interviewing: 2.0 (active — prep needed)
    """
    status_weights = {
        "queued": 1.0,
        "tailoring": 1.2,
        "ready": 1.5,
        "submitted": 0.3,
        "interviewing": 2.0,
        "offer": 0.1,
        "rejected": 0.0,
    }

    scored = []
    for app in applications:
        weight = status_weights.get(app.status, 0.5)
        priority_score = app.fit_score * weight
        scored.append((priority_score, app))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Assign priority ranks
    for i, (_, app) in enumerate(scored[:top_n]):
        app.priority = i + 1

    return [app for _, app in scored[:top_n]]


def generate_agent_tasks(
    applications: list[ApplicationEntry],
) -> list[AgentTask]:
    """
    Generate the optimal sequence of agent tasks for this week.

    Ordering:
    1. Scout new jobs if pipeline is thin
    2. Tailor queued applications (highest fit first)
    3. Generate cover letters for ready applications
    4. Coach prep for interviewing applications
    """
    tasks: list[AgentTask] = []

    # Count pipeline
    queued = [a for a in applications if a.status == "queued"]
    ready = [a for a in applications if a.status == "ready"]
    interviewing = [a for a in applications if a.status == "interviewing"]

    # 1. Scout if pipeline is thin
    if len(queued) + len(ready) < 5:
        tasks.append(AgentTask(
            agent="scout",
            action="search",
            target_id="",
            priority=1,
            reason=f"Pipeline only has {len(queued) + len(ready)} active applications — need more leads",
        ))

    # 2. Tailor queued applications
    queued_sorted = sorted(queued, key=lambda a: a.fit_score, reverse=True)
    for i, app in enumerate(queued_sorted[:5]):
        tasks.append(AgentTask(
            agent="tailor",
            action="tailor",
            target_id=app.id,
            priority=2 + i,
            reason=f"Tailor resume for {app.jd.company if app.jd else 'job'} (fit: {app.fit_score:.0f})",
        ))

    # 3. Generate cover letters for ready applications
    for i, app in enumerate(ready[:3]):
        tasks.append(AgentTask(
            agent="pitcher",
            action="generate",
            target_id=app.id,
            priority=10 + i,
            reason=f"Generate cover letter for {app.jd.company if app.jd else 'job'}",
        ))

    # 4. Coach prep for interviews
    for i, app in enumerate(interviewing):
        tasks.append(AgentTask(
            agent="coach",
            action="start_session",
            target_id=app.id,
            priority=20 + i,
            reason=f"Interview prep for {app.jd.company if app.jd else 'job'}",
        ))

    tasks.sort(key=lambda t: t.priority)
    return tasks


def generate_weekly_report(
    applications: list[ApplicationEntry],
    goal: WeeklyGoal,
    resume: Optional[Resume] = None,
) -> WeeklyReport:
    """
    Generate the weekly strategy report.

    Analyzes the pipeline, generates action items, and identifies wins.
    """
    now = datetime.now(UTC)
    week_str = now.strftime("%B %d, %Y")

    # Counts
    submitted = [a for a in applications if a.status == "submitted"]
    interviewing = [a for a in applications if a.status == "interviewing"]
    offers = [a for a in applications if a.status == "offer"]
    ready = [a for a in applications if a.status == "ready"]
    queued = [a for a in applications if a.status == "queued"]

    # ATS scores
    ats_scores = [
        a.ats_score_after for a in applications
        if a.ats_score_after is not None and a.ats_score_after > 0
    ]
    avg_ats = sum(ats_scores) / len(ats_scores) if ats_scores else 0

    # Top opportunities (by fit score, non-rejected)
    active = [a for a in applications if a.status not in ("rejected", "offer")]
    active_sorted = sorted(active, key=lambda a: a.fit_score, reverse=True)
    top_opps = []
    for app in active_sorted[:5]:
        top_opps.append({
            "company": app.jd.company if app.jd else "Unknown",
            "role": app.jd.title if app.jd else "Unknown",
            "fit_score": round(app.fit_score),
            "status": app.status,
        })

    # Generate summary
    summary_parts = []
    summary_parts.append(f"You have {len(applications)} total applications in the pipeline.")
    if len(submitted) > 0:
        summary_parts.append(f"{len(submitted)} submitted and waiting for response.")
    if len(interviewing) > 0:
        summary_parts.append(f"{len(interviewing)} in active interview process!")
    if len(offers) > 0:
        summary_parts.append(f"{len(offers)} offer(s) on the table!")
    if len(ready) > 0:
        summary_parts.append(f"{len(ready)} ready to submit.")
    if len(queued) > 0:
        summary_parts.append(f"{len(queued)} queued for tailoring.")

    summary = " ".join(summary_parts)

    # Action items
    action_items: list[str] = []

    if len(queued) > 0 and goal.target_applications > 0:
        remaining = goal.target_applications - len(submitted)
        if remaining > 0:
            action_items.append(
                f"Tailor and submit {min(remaining, len(queued))} applications to hit your weekly target of {goal.target_applications}"
            )

    if len(ready) > 0:
        action_items.append(
            f"Submit {len(ready)} ready application(s) — they're tailored and good to go"
        )

    for app in interviewing:
        company = app.jd.company if app.jd else "upcoming"
        action_items.append(f"Run a mock interview session to prep for {company}")

    if len(submitted) > 3:
        action_items.append(
            "Consider following up on older submitted applications (1-2 week rule)"
        )

    if len(queued) + len(ready) < 5:
        action_items.append(
            "Pipeline is thin — spend 30 minutes on Scout to surface new leads"
        )

    if not action_items:
        action_items.append("Keep going! Set a weekly target to stay on track.")

    # Wins
    wins: list[str] = []
    if len(submitted) > 0:
        wins.append(f"Submitted {len(submitted)} application(s) this period")
    if len(interviewing) > 0:
        wins.append(f"Got {len(interviewing)} interview(s) — your preparation is paying off")
    if avg_ats > 75:
        wins.append(f"Average ATS score of {avg_ats:.0f} — resumes are well-optimized")
    if len(offers) > 0:
        wins.append(f"{len(offers)} offer(s) received!")

    if not wins:
        wins.append("You're building momentum — every application is a step forward")

    # Agent tasks
    agent_tasks = generate_agent_tasks(applications)

    return WeeklyReport(
        week_of=week_str,
        summary=summary,
        applications_target=goal.target_applications,
        applications_sent=len(submitted),
        interviews_scheduled=len(interviewing),
        avg_ats_score=round(avg_ats, 1),
        top_opportunities=top_opps,
        action_items=action_items,
        wins=wins,
        agent_tasks=agent_tasks,
    )


# ── Claude strategy enrichment ────────────────────────────────────────────


async def _enrich_report_with_claude(
    report: WeeklyReport,
    applications: list[ApplicationEntry],
    goal: WeeklyGoal,
) -> WeeklyReport:
    """Use Claude to generate insightful, personalized strategy narrative."""
    from backend.agents.llm import ask_json

    system = """You are an experienced career coach generating a personalized weekly job search strategy.

Given pipeline data, generate an insightful summary and actionable priorities.

Guidelines:
- Be specific, not generic ("Follow up on your Google SWE application" not "Send follow-ups")
- Prioritize ruthlessly — list actions in urgency order
- Acknowledge wins genuinely and specifically
- If pipeline is thin, advise on how to fill it and what to look for
- Be encouraging but honest

Output JSON:
{
  "summary": "2-3 sentence narrative — specific to this pipeline, not a template",
  "action_items": ["most urgent action", "second priority", "third priority"],
  "wins": ["specific win 1", "specific win 2"],
  "strategic_focus": "The single most important thing to do this week (one sentence)"
}"""

    pipeline = {
        "total": len(applications),
        "queued": len([a for a in applications if a.status == "queued"]),
        "tailoring": len([a for a in applications if a.status == "tailoring"]),
        "ready": len([a for a in applications if a.status == "ready"]),
        "submitted": len([a for a in applications if a.status == "submitted"]),
        "interviewing": len([a for a in applications if a.status == "interviewing"]),
        "offers": len([a for a in applications if a.status == "offer"]),
        "rejected": len([a for a in applications if a.status == "rejected"]),
    }

    top_companies = []
    for app in sorted(applications, key=lambda a: a.fit_score, reverse=True)[:5]:
        if app.jd:
            top_companies.append(
                f"{app.jd.company} — {app.jd.title or 'role'} ({app.fit_score:.0f}% fit, {app.status})"
            )

    user = f"""PIPELINE BREAKDOWN:
{json.dumps(pipeline, indent=2)}

TOP OPPORTUNITIES BY FIT SCORE:
{chr(10).join(top_companies) or 'No jobs tracked yet'}

WEEKLY GOAL: {goal.target_applications} applications | Target role: {goal.target_role or 'Not specified'}
APPLICATIONS SENT: {report.applications_sent}
AVERAGE ATS SCORE: {f'{report.avg_ats_score:.0f}' if report.avg_ats_score else 'N/A'}

Heuristic summary (improve on this with specific context): {report.summary}"""

    data = await ask_json(system, user, model="claude-haiku-4-5-20251001", max_tokens=700)

    enriched = copy.deepcopy(report)
    if isinstance(data, dict):
        if data.get("summary"):
            enriched.summary = data["summary"]
        if data.get("action_items"):
            enriched.action_items = [i for i in data["action_items"] if i]
        if data.get("wins"):
            enriched.wins = [w for w in data["wins"] if w]
        if data.get("strategic_focus"):
            enriched.action_items = [data["strategic_focus"]] + enriched.action_items

    return enriched


async def generate_weekly_report_ai(
    applications: list[ApplicationEntry],
    goal: WeeklyGoal,
    resume: Optional[Resume] = None,
) -> WeeklyReport:
    """
    Generate weekly report with Claude enhancement.
    Falls back to heuristic report if Claude is unavailable.
    """
    report = generate_weekly_report(applications, goal, resume)
    try:
        report = await _enrich_report_with_claude(report, applications, goal)
    except Exception:
        pass
    return report


# ── In-memory stores ──────────────────────────────────────────────────────

_app_store: dict[str, ApplicationEntry] = {}
_goal_store: dict[str, WeeklyGoal] = {}  # user_id -> goal
_report_store: list[WeeklyReport] = []


def store_application(app: ApplicationEntry) -> None:
    _app_store[app.id] = app


def get_application(app_id: str) -> Optional[ApplicationEntry]:
    return _app_store.get(app_id)


def list_applications(user_id: str = "") -> list[ApplicationEntry]:
    return list(_app_store.values())


def update_application_status(app_id: str, status: str) -> Optional[ApplicationEntry]:
    app = _app_store.get(app_id)
    if app:
        app.status = status
    return app


def set_goal(user_id: str, goal: WeeklyGoal) -> None:
    _goal_store[user_id] = goal


def get_goal(user_id: str = "") -> WeeklyGoal:
    return _goal_store.get(user_id, WeeklyGoal())


def store_report(report: WeeklyReport) -> None:
    _report_store.append(report)


def get_reports() -> list[WeeklyReport]:
    return list(reversed(_report_store))
