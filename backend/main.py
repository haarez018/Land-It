"""FastAPI entry point with CORS, health check, scheduler, and router includes."""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel as _BaseModel

from backend.config import settings
from backend.api.routes import resume, jobs, applications, coach, planner, auth, pitcher, tracker, onboarding, exports, demo
from backend.auth_deps import get_current_user_id
from backend.tasks.scheduler import scheduler_lifespan

logger = logging.getLogger(__name__)


# ── Request models for typed endpoints ───────────────────────────────────────

class SalaryEstimateRequest(_BaseModel):
    resume_id: str
    jd_text: str

class AtsOptimizeRequest(_BaseModel):
    company: str = ""

class AddStoryRequest(_BaseModel):
    title: str = ""
    situation: str = ""
    task: str = ""
    action: str = ""
    result: str = ""
    company_context: str = ""
    metrics: list[str] = []

class MatchStoryRequest(_BaseModel):
    question: str = ""

class OutreachRequest(_BaseModel):
    resume_id: str
    company: str = ""
    role: str = ""
    channel: str = "linkedin"
    recipient_type: str = "hiring_manager"

class FormatResumeRequest(_BaseModel):
    format_type: str = "standard_pdf"

class TimingRequest(_BaseModel):
    posting_date: str | None = None
    industry: str = "tech"

class ReadinessRequest(_BaseModel):
    resume_score: float = 0
    story_coverage: float = 0
    mock_score: float = 0
    gaps_addressed: float = 0
    company_researched: bool = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks — runs the weekly scheduler in background."""
    async with scheduler_lifespan():
        logger.info("Land It backend started (env=%s)", settings.ENVIRONMENT)
        yield
    logger.info("Land It backend shutting down")


app = FastAPI(
    title="Land It API",
    version="1.0.0",
    description=(
        "Multi-agent AI career system with 22-dimension resume scoring. "
        "6 agents coordinate to manage job search from discovery to offer. "
        "14 ATS dimensions + 8 Standout dimensions with dynamic 3-axis weighting "
        "(role type × seniority × company). Includes callback probability predictor, "
        "resume A/B testing, skill gap analysis, batch scoring, salary intelligence, "
        "voice-preserved cover letters, and AI mock interviews."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# Hide docs in production
if settings.ENVIRONMENT == "production":
    app.docs_url = None
    app.redoc_url = None


def _db_row_to_entry(row: dict):
    """Convert a Supabase applications row to an ApplicationEntry for analytics."""
    from backend.agents.planner.strategy import ApplicationEntry
    return ApplicationEntry(
        id=row["id"],
        job_id=row["job_id"],
        status=row.get("status", "submitted"),
        fit_score=row.get("fit_score") or 0.0,
        ats_score_before=row.get("ats_score_before"),
        ats_score_after=row.get("ats_score_after"),
        priority=row.get("priority") or 0,
        submitted_at=row.get("submitted_at"),
        notes=row.get("notes") or "",
    )


app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(resume.router, prefix="/api/resume", tags=["Resume & Scoring"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(applications.router, prefix="/api/applications", tags=["Applications"])
app.include_router(coach.router, prefix="/api/coach", tags=["Mock Interviews"])
app.include_router(planner.router, prefix="/api/planner", tags=["Planner & Strategy"])
app.include_router(pitcher.router, prefix="/api/pitcher", tags=["Cover Letters"])
app.include_router(tracker.router, prefix="/api/tracker", tags=["Application Tracker"])
app.include_router(onboarding.router, prefix="/api/onboarding", tags=["Onboarding"])
app.include_router(exports.router, prefix="/api/export", tags=["Export Reports"])
app.include_router(demo.router, prefix="/api/demo", tags=["Demo"])


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint. Returns service status, version, and environment."""
    return {"status": "ok", "version": "1.0.0", "environment": settings.ENVIRONMENT}


# ── Analytics endpoints ────────────────────────────────────────────────────


@app.get("/api/analytics", tags=["Analytics"])
async def get_analytics(user_id: str = Depends(get_current_user_id)):
    """Compute job search analytics from all applications and score history."""
    from backend.agents.planner.strategy import ApplicationEntry
    from backend.agents.planner.analytics import compute_analytics_ai
    from backend.db import get_db

    rows = get_db().table("applications").select("*").eq("user_id", user_id).execute().data
    apps = [_db_row_to_entry(r) for r in rows]
    return await compute_analytics_ai(apps)


@app.get("/api/analytics/funnel", tags=["Analytics"])
async def get_funnel(user_id: str = Depends(get_current_user_id)):
    """Get just the funnel metrics and conversion rates."""
    from backend.agents.planner.analytics import compute_analytics
    from backend.db import get_db

    rows = get_db().table("applications").select("*").eq("user_id", user_id).execute().data
    analytics = compute_analytics([_db_row_to_entry(r) for r in rows])
    return analytics.funnel


@app.get("/api/analytics/dimension-heatmap", tags=["Analytics"])
async def get_dimension_heatmap():
    """Get dimension averages and strongest/weakest dimensions."""
    from backend.agents.planner.analytics import compute_analytics

    analytics = compute_analytics([])
    return analytics.dimension_heatmap


# ── Salary Intelligence endpoints ─────────────────────────────────────────


@app.post("/api/salary/estimate", tags=["Salary Intelligence"])
async def salary_estimate(request: SalaryEstimateRequest, user_id: str = Depends(get_current_user_id)):
    """Estimate salary range for a resume + JD combination."""
    from backend.api.routes.resume import load_user_resume
    from backend.parsers.jd_parser import parse_jd
    from backend.agents.scout.salary_intel import estimate_salary

    resume = load_user_resume(request.resume_id, user_id)
    jd = parse_jd(request.jd_text)

    result = estimate_salary(resume, jd)
    return {
        "role_type": result.role_type,
        "seniority": result.seniority,
        "location": result.location,
        "company": result.company,
        "estimated_range": list(result.estimated_range),
        "estimated_midpoint": result.estimated_midpoint,
        "user_position_in_range": result.user_position_in_range,
        "user_estimated_value": result.user_estimated_value,
        "premium_factors": result.premium_factors,
        "discount_factors": result.discount_factors,
        "negotiation_leverage": result.negotiation_leverage,
        "negotiation_talking_points": result.negotiation_talking_points,
        "confidence": result.confidence,
        "confidence_reason": result.confidence_reason,
    }


@app.get("/api/salary/ranges", tags=["Salary Intelligence"])
async def salary_ranges():
    """Return all base salary ranges for reference."""
    from backend.agents.scout.salary_intel import BASE_SALARY_RANGES
    return {
        f"{role}_{seniority}": {"low": low, "high": high}
        for (role, seniority), (low, high) in BASE_SALARY_RANGES.items()
    }


@app.get("/api/salary/locations", tags=["Salary Intelligence"])
async def salary_locations():
    """Return all location multipliers."""
    from backend.agents.scout.salary_intel import LOCATION_MULTIPLIERS
    return LOCATION_MULTIPLIERS


# ── New feature endpoints ─────────────────────────────────────────────────


@app.post("/api/resume/{resume_id}/bias-check", tags=["Bias Detection"])
async def bias_check(resume_id: str, user_id: str = Depends(get_current_user_id)):
    """Scan resume for gendered, age, cultural, and disability bias signals."""
    from backend.api.routes.resume import load_user_resume
    from backend.agents.tailor.bias_detector import detect_bias
    report = detect_bias(load_user_resume(resume_id, user_id))
    return {
        "total_flags": report.total_flags, "bias_free_score": report.bias_free_score,
        "gendered_flags": report.gendered_flags, "age_flags": report.age_flags,
        "cultural_flags": report.cultural_flags, "assessment": report.assessment,
        "top_priority_fix": report.top_priority_fix,
        "flags": [{"text": f.text, "bias_type": f.bias_type, "severity": f.severity,
                    "explanation": f.explanation, "suggestion": f.suggestion} for f in report.flags],
    }


@app.post("/api/resume/{resume_id}/ats-optimize", tags=["ATS Systems"])
async def ats_optimize(resume_id: str, request: AtsOptimizeRequest, user_id: str = Depends(get_current_user_id)):
    """Get ATS-specific recommendations for a resume + company combo."""
    from backend.api.routes.resume import load_user_resume
    from backend.agents.tailor.ats_systems import get_ats_recommendations
    return get_ats_recommendations(load_user_resume(resume_id, user_id), request.company)


@app.get("/api/ats-systems", tags=["ATS Systems"])
async def list_ats_systems():
    """List all ATS profiles with quirks and recommendations."""
    from backend.agents.tailor.ats_systems import ATS_PROFILES
    return [{
        "key": k, "name": p.name, "company_example": p.company_example,
        "parsing_quirks": p.parsing_quirks, "format_recommendations": p.format_recommendations,
        "preferred_format": p.preferred_format, "known_issues": p.known_issues,
    } for k, p in ATS_PROFILES.items()]


@app.post("/api/coach/stories", tags=["Story Bank"])
async def add_story(request: AddStoryRequest):
    """Add a STAR story to the interview story bank."""
    from backend.agents.coach.story_bank import STARStory, story_bank
    story = STARStory(
        title=request.title, situation=request.situation,
        task=request.task, action=request.action,
        result=request.result, company_context=request.company_context,
        metrics=request.metrics,
    )
    story_bank.add_story(story)
    return {"id": story.id, "question_types": story.question_types,
            "specificity_score": story.specificity_score, "impact_score": story.impact_score}


@app.get("/api/coach/stories", tags=["Story Bank"])
async def list_stories():
    """List all STAR stories."""
    from backend.agents.coach.story_bank import story_bank
    return [{"id": s.id, "title": s.title, "question_types": s.question_types,
             "specificity_score": s.specificity_score, "impact_score": s.impact_score} for s in story_bank.get_stories()]


@app.get("/api/coach/stories/analysis", tags=["Story Bank"])
async def story_analysis():
    """Analyze story bank coverage across question types."""
    from backend.agents.coach.story_bank import story_bank
    a = story_bank.analyze_coverage()
    return {"total_stories": a.total_stories, "coverage_percentage": a.coverage_percentage,
            "gaps": a.gaps, "weak_areas": a.weak_areas, "recommendation": a.recommendation}


@app.post("/api/coach/stories/match", tags=["Story Bank"])
async def match_story(request: MatchStoryRequest):
    """Match an interview question to best STAR stories."""
    from backend.agents.coach.story_bank import story_bank
    stories = story_bank.get_story_for_question(request.question)
    return [{"id": s.id, "title": s.title, "impact_score": s.impact_score} for s in stories[:5]]


@app.post("/api/career/simulate/{resume_id}", tags=["Career Simulator"])
async def simulate_career(resume_id: str, user_id: str = Depends(get_current_user_id)):
    """Simulate 3-track career path based on current resume."""
    from backend.api.routes.resume import load_user_resume
    from backend.agents.planner.career_simulator import simulate_career as _sim
    result = _sim(load_user_resume(resume_id, user_id))
    return {
        "recommended_path": result.recommended_path, "reasoning": result.reasoning,
        "likely_title_2yr": result.likely_title_2yr, "likely_salary_2yr": list(result.likely_salary_2yr),
        "likely_title_5yr": result.likely_title_5yr, "likely_salary_5yr": list(result.likely_salary_5yr),
        "skills_to_develop_2yr": result.skills_to_develop_2yr,
        "paths": [{"name": p.name, "years_to_end": p.years_to_reach_end,
                    "skills_gaps": p.skills_gaps_for_path[:5]} for p in result.paths],
    }


@app.get("/api/market/trends/{role_type}", tags=["Market Trends"])
async def market_trends(role_type: str):
    """Get curated market trend data for a role type."""
    from backend.agents.scout.market_trends import get_market_snapshot
    s = get_market_snapshot(role_type)
    return {
        "role_type": s.role_type, "avg_salary_trend": s.avg_salary_trend,
        "remote_percentage": s.remote_percentage, "emerging_requirements": s.emerging_requirements,
        "hot_skills": [{"skill": t.skill, "yoy_change": t.yoy_change, "demand": t.demand_level} for t in s.hot_skills],
        "declining_skills": [{"skill": t.skill, "yoy_change": t.yoy_change} for t in s.declining_skills],
    }


@app.get("/api/market/fit/{resume_id}/{role_type}", tags=["Market Trends"])
async def market_fit(resume_id: str, role_type: str, user_id: str = Depends(get_current_user_id)):
    """Compare user's skills against market trends."""
    from backend.api.routes.resume import load_user_resume
    from backend.agents.scout.market_trends import get_user_market_fit
    fit = get_user_market_fit(load_user_resume(resume_id, user_id), role_type)
    return {"market_fit_score": fit.market_fit_score, "hot_skills_you_have": fit.hot_skills_you_have,
            "hot_skills_you_lack": fit.hot_skills_you_lack, "declining_skills_you_have": fit.declining_skills_you_have,
            "advice": fit.advice}


@app.post("/api/pitcher/outreach", tags=["Cold Outreach"])
async def generate_outreach_endpoint(request: OutreachRequest, user_id: str = Depends(get_current_user_id)):
    """Generate personalized cold outreach messages."""
    from backend.api.routes.resume import load_user_resume
    from backend.agents.pitcher.outreach_generator import generate_outreach
    msg = generate_outreach(
        load_user_resume(request.resume_id, user_id), request.company, request.role,
        request.channel, request.recipient_type,
    )
    return {"channel": msg.channel, "recipient_type": msg.recipient_type,
            "subject": msg.subject, "body": msg.body, "tone": msg.tone, "word_count": msg.word_count}


@app.post("/api/resume/{resume_id}/format", tags=["Multi-Format"])
async def format_resume(resume_id: str, request: FormatResumeRequest, user_id: str = Depends(get_current_user_id)):
    """Generate resume in a specific format (standard, LinkedIn, one-page, technical CV, portfolio)."""
    from backend.api.routes.resume import load_user_resume
    from backend.agents.tailor.format_generator import generate_format
    result = generate_format(load_user_resume(resume_id, user_id), request.format_type)
    return {"format_type": result.format_type, "format_name": result.format_name,
            "content": result.content, "word_count": result.word_count, "sections": result.sections}


@app.post("/api/timing/recommend", tags=["Timing Optimizer"])
async def timing_recommend(request: TimingRequest):
    """Get research-backed timing recommendation for job application."""
    from backend.agents.tracker.timing_optimizer import get_timing_recommendation
    rec = get_timing_recommendation(request.posting_date, request.industry)
    return {"best_day": rec.best_day, "best_time": rec.best_time, "avoid_days": rec.avoid_days,
            "urgency_level": rec.urgency_level, "urgency_reasoning": rec.urgency_reasoning,
            "industry_seasonality": rec.industry_seasonality}


@app.post("/api/resume/{resume_id}/freshness", tags=["Freshness Decay"])
async def freshness_check(resume_id: str, user_id: str = Depends(get_current_user_id)):
    """Score how fresh and current a resume is."""
    from backend.api.routes.resume import load_user_resume
    from backend.agents.tailor.freshness import analyze_freshness
    report = analyze_freshness(load_user_resume(resume_id, user_id))
    return {"freshness_score": report.freshness_score, "decay_factors": report.decay_factors,
            "stale_sections": report.stale_sections, "last_role_recency": report.last_role_recency,
            "skills_currency": report.skills_currency, "refresh_suggestions": report.refresh_suggestions}


@app.post("/api/resume/{resume_id}/consistency", tags=["Consistency"])
async def consistency_check(resume_id: str, user_id: str = Depends(get_current_user_id)):
    """Check resume for internal contradictions and inconsistencies."""
    from backend.api.routes.resume import load_user_resume
    from backend.agents.tailor.consistency_checker import check_consistency
    issues = check_consistency(load_user_resume(resume_id, user_id))
    return [{"type": i.type, "severity": i.severity, "description": i.description,
             "suggestion": i.suggestion} for i in issues]


@app.post("/api/readiness", tags=["Interview Readiness"])
async def readiness_score(request: ReadinessRequest):
    """Calculate composite interview readiness score."""
    from backend.agents.coach.readiness_scorer import calculate_readiness
    score = calculate_readiness(
        resume_combined_score=request.resume_score,
        story_coverage_pct=request.story_coverage,
        mock_avg_score=request.mock_score,
        skill_gaps_addressed_pct=request.gaps_addressed,
        company_researched=request.company_researched,
    )
    return {"total": score.total, "readiness_level": score.readiness_level,
            "gaps": score.gaps, "next_steps": score.next_steps}


@app.get("/api/notifications", tags=["Notifications"])
async def get_notifications():
    """Get pending notifications."""
    from backend.agents.planner.notifications import notification_engine
    return [{"id": n.id, "type": n.type, "priority": n.priority,
             "title": n.title, "body": n.body, "action_url": n.action_url}
            for n in notification_engine.get_pending("default")]


@app.post("/api/notifications/{notification_id}/dismiss", tags=["Notifications"])
async def dismiss_notification(notification_id: str):
    """Dismiss a notification."""
    from backend.agents.planner.notifications import notification_engine
    dismissed = notification_engine.dismiss("default", notification_id)
    return {"dismissed": dismissed}


@app.get("/api/company-profiles", tags=["Company Profiles"])
async def list_company_profiles():
    """List all known company scoring profiles with hiring philosophies and weight overrides."""
    from backend.agents.tailor.weightage.company_profiles import COMPANY_PROFILES

    return [
        {
            "id": p.id,
            "name": p.name,
            "hiring_philosophy": p.hiring_philosophy,
            "interview_signals": p.interview_signals,
            "red_flags": p.red_flags,
            "ats_overrides": {k: v for k, v in p.ats_multipliers.items() if v != 1.0},
            "standout_overrides": {k: v for k, v in p.standout_multipliers.items() if v != 1.0},
        }
        for p in COMPANY_PROFILES.values()
    ]
