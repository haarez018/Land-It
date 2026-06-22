"""
Analytics & Insights: pure computation over application + score data.

No database calls — takes data in, returns analytics out.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional

from backend.agents.planner.benchmarks import INDUSTRY_BENCHMARKS, compare_to_benchmark


# ── Data models ──────────────────────────────────────────────────────────────

@dataclass
class WeekBucket:
    week: str          # ISO week like "2026-W22"
    avg_score: float
    count: int


@dataclass
class FunnelMetrics:
    jobs_discovered: int
    jobs_queued: int
    jobs_applied: int
    responses_received: int
    interviews_scheduled: int
    offers_received: int
    rejections: int
    conversion_rates: dict[str, float]
    benchmark_comparisons: dict[str, str]


@dataclass
class DimensionHeatmap:
    dimension_averages: dict[str, float]       # dim_id -> avg raw score
    strongest_dimensions: list[str]            # top 3
    weakest_dimensions: list[str]              # bottom 3
    dimension_consistency: dict[str, float]    # dim_id -> stdev


@dataclass
class TimingAnalysis:
    avg_days_to_first_response: float
    avg_days_to_interview: float
    avg_days_applied_to_offer: float
    most_active_day_of_week: str
    most_active_hour: int
    applications_per_week: list[WeekBucket]


@dataclass
class PatternInsights:
    company_size_distribution: dict[str, int]
    role_type_distribution: dict[str, int]
    top_responding_company_type: str
    highest_avg_score_role_type: str
    most_applied_to_company: str


@dataclass
class Predictions:
    estimated_weeks_to_offer: float
    recommended_weekly_volume: int
    current_trajectory: str  # "on_track" | "needs_more_volume" | "needs_better_targeting"


@dataclass
class JobSearchAnalytics:
    funnel: FunnelMetrics
    score_trends: dict[str, list[WeekBucket]]  # "ats" | "standout" | "combined"
    score_improvement: float
    is_improving: bool
    dimension_heatmap: DimensionHeatmap
    timing: TimingAnalysis
    patterns: PatternInsights
    predictions: Predictions
    this_week_wins: list[str]
    focus_areas: list[str]
    one_sentence_summary: str


# ── Status classification ────────────────────────────────────────────────────

_APPLIED_STATUSES = {"submitted", "followed_up", "phone_screen", "interviewing", "offer", "rejected"}
_RESPONSE_STATUSES = {"phone_screen", "interviewing", "offer", "rejected"}
_INTERVIEW_STATUSES = {"phone_screen", "interviewing", "offer"}
_OFFER_STATUSES = {"offer"}
_REJECTION_STATUSES = {"rejected"}

_DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# ── Compute analytics ────────────────────────────────────────────────────────

def compute_analytics(
    applications: list,
    score_history: list[dict] | None = None,
) -> JobSearchAnalytics:
    """
    Compute full analytics from application data and score history.

    Args:
        applications: list of ApplicationEntry or dicts with status, fit_score,
                      ats_score_before, ats_score_after, created_at, applied_at,
                      last_activity, jd (with company, title)
        score_history: optional list of {ats_score, standout_score, combined_score,
                       dimension_scores: [{dimension_id, raw_score}], scored_at}

    Returns:
        JobSearchAnalytics with all sections populated
    """
    score_history = score_history or []

    # ── Funnel ────────────────────────────────────────────────────────────
    funnel = _compute_funnel(applications)

    # ── Score trends ──────────────────────────────────────────────────────
    score_trends, score_improvement, is_improving = _compute_score_trends(score_history)

    # ── Dimension heatmap ─────────────────────────────────────────────────
    dimension_heatmap = _compute_dimension_heatmap(score_history)

    # ── Timing ────────────────────────────────────────────────────────────
    timing = _compute_timing(applications)

    # ── Patterns ──────────────────────────────────────────────────────────
    patterns = _compute_patterns(applications)

    # ── Predictions ───────────────────────────────────────────────────────
    predictions = _compute_predictions(funnel, timing)

    # ── Actionable summary ────────────────────────────────────────────────
    this_week_wins = _compute_wins(applications)
    focus_areas = _compute_focus_areas(dimension_heatmap)
    one_sentence = _build_summary(funnel, timing, is_improving)

    return JobSearchAnalytics(
        funnel=funnel,
        score_trends=score_trends,
        score_improvement=score_improvement,
        is_improving=is_improving,
        dimension_heatmap=dimension_heatmap,
        timing=timing,
        patterns=patterns,
        predictions=predictions,
        this_week_wins=this_week_wins,
        focus_areas=focus_areas,
        one_sentence_summary=one_sentence,
    )


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_status(app) -> str:
    if hasattr(app, "status"):
        val = getattr(app, "status", "")
        # Handle enum values (.value) and strings
        return val.value if hasattr(val, "value") else str(val)
    if isinstance(app, dict):
        return app.get("status", "")
    return ""


def _get_attr(app, key, default=None):
    if hasattr(app, key):
        return getattr(app, key, default)
    if isinstance(app, dict):
        return app.get(key, default)
    return default


def _compute_funnel(applications: list) -> FunnelMetrics:
    statuses = [_get_status(a) for a in applications]
    total = len(applications)
    queued = sum(1 for s in statuses if s in {"queued", "tailoring", "ready"} or s in _APPLIED_STATUSES)
    applied = sum(1 for s in statuses if s in _APPLIED_STATUSES)
    responses = sum(1 for s in statuses if s in _RESPONSE_STATUSES)
    interviews = sum(1 for s in statuses if s in _INTERVIEW_STATUSES)
    offers = sum(1 for s in statuses if s in _OFFER_STATUSES)
    rejections = sum(1 for s in statuses if s in _REJECTION_STATUSES)

    # Conversion rates
    rates = {}
    rates["discovered_to_applied"] = round(applied / total, 3) if total > 0 else 0.0
    rates["applied_to_response"] = round(responses / applied, 3) if applied > 0 else 0.0
    rates["response_to_interview"] = round(interviews / responses, 3) if responses > 0 else 0.0
    rates["interview_to_offer"] = round(offers / interviews, 3) if interviews > 0 else 0.0

    benchmarks = {}
    for rate_key in ["applied_to_response", "response_to_interview", "interview_to_offer"]:
        if rate_key in INDUSTRY_BENCHMARKS:
            benchmarks[rate_key] = compare_to_benchmark(rates[rate_key], INDUSTRY_BENCHMARKS[rate_key])

    return FunnelMetrics(
        jobs_discovered=total,
        jobs_queued=queued,
        jobs_applied=applied,
        responses_received=responses,
        interviews_scheduled=interviews,
        offers_received=offers,
        rejections=rejections,
        conversion_rates=rates,
        benchmark_comparisons=benchmarks,
    )


def _compute_score_trends(
    score_history: list[dict],
) -> tuple[dict[str, list[WeekBucket]], float, bool]:
    if not score_history:
        return {"ats": [], "standout": [], "combined": []}, 0.0, False

    # Group by ISO week
    week_data: dict[str, list[dict]] = defaultdict(list)
    for entry in score_history:
        scored_at = entry.get("scored_at", "")
        try:
            dt = datetime.fromisoformat(scored_at) if scored_at else datetime.now()
            week = f"{dt.isocalendar()[0]}-W{dt.isocalendar()[1]:02d}"
        except (ValueError, TypeError):
            week = "unknown"
        week_data[week].append(entry)

    trends: dict[str, list[WeekBucket]] = {"ats": [], "standout": [], "combined": []}

    for week in sorted(week_data.keys()):
        entries = week_data[week]
        for score_type in ("ats", "standout", "combined"):
            key = f"{score_type}_score"
            vals = [e.get(key, 0) for e in entries if e.get(key) is not None]
            if vals:
                trends[score_type].append(WeekBucket(
                    week=week, avg_score=round(sum(vals) / len(vals), 1), count=len(vals),
                ))

    # Improvement
    combined_weeks = trends["combined"]
    if len(combined_weeks) >= 2:
        improvement = combined_weeks[-1].avg_score - combined_weeks[0].avg_score
        is_improving = improvement > 0
    else:
        improvement = 0.0
        is_improving = False

    return trends, round(improvement, 1), is_improving


def _compute_dimension_heatmap(score_history: list[dict]) -> DimensionHeatmap:
    dim_scores: dict[str, list[float]] = defaultdict(list)

    for entry in score_history:
        for dim in entry.get("dimension_scores", []):
            dim_id = dim.get("dimension_id", "")
            raw = dim.get("raw_score")
            if dim_id and raw is not None:
                dim_scores[dim_id].append(raw)

    averages = {}
    consistency = {}
    for dim_id, scores in dim_scores.items():
        avg = sum(scores) / len(scores)
        averages[dim_id] = round(avg, 1)
        if len(scores) >= 2:
            variance = sum((s - avg) ** 2 for s in scores) / (len(scores) - 1)
            consistency[dim_id] = round(math.sqrt(variance), 1)
        else:
            consistency[dim_id] = 0.0

    sorted_dims = sorted(averages.items(), key=lambda x: x[1])
    weakest = [d[0] for d in sorted_dims[:3]]
    strongest = [d[0] for d in sorted_dims[-3:]]

    return DimensionHeatmap(
        dimension_averages=averages,
        strongest_dimensions=strongest,
        weakest_dimensions=weakest,
        dimension_consistency=consistency,
    )


def _parse_date(val) -> Optional[datetime]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, str) and val:
        try:
            return datetime.fromisoformat(val)
        except (ValueError, TypeError):
            return None
    return None


def _compute_timing(applications: list) -> TimingAnalysis:
    days_to_response: list[float] = []
    days_to_interview: list[float] = []
    days_to_offer: list[float] = []
    day_counter: Counter = Counter()
    hour_counter: Counter = Counter()
    week_counter: Counter = Counter()

    for app in applications:
        created = _parse_date(_get_attr(app, "created_at"))
        applied = _parse_date(_get_attr(app, "applied_at"))
        last = _parse_date(_get_attr(app, "last_activity"))
        status = _get_status(app)

        ts = applied or created
        if ts:
            day_counter[_DAY_NAMES[ts.weekday()]] += 1
            hour_counter[ts.hour] += 1
            week = f"{ts.isocalendar()[0]}-W{ts.isocalendar()[1]:02d}"
            week_counter[week] += 1

        if status in _RESPONSE_STATUSES and ts and last:
            delta = (last - ts).days
            if delta >= 0:
                days_to_response.append(delta)

        if status in _INTERVIEW_STATUSES and ts and last:
            delta = (last - ts).days
            if delta >= 0:
                days_to_interview.append(delta)

        if status in _OFFER_STATUSES and ts and last:
            delta = (last - ts).days
            if delta >= 0:
                days_to_offer.append(delta)

    avg_response = round(sum(days_to_response) / len(days_to_response), 1) if days_to_response else 0.0
    avg_interview = round(sum(days_to_interview) / len(days_to_interview), 1) if days_to_interview else 0.0
    avg_offer = round(sum(days_to_offer) / len(days_to_offer), 1) if days_to_offer else 0.0
    best_day = day_counter.most_common(1)[0][0] if day_counter else "Monday"
    best_hour = hour_counter.most_common(1)[0][0] if hour_counter else 10

    apps_per_week = [
        WeekBucket(week=w, avg_score=0, count=c)
        for w, c in sorted(week_counter.items())
    ]

    return TimingAnalysis(
        avg_days_to_first_response=avg_response,
        avg_days_to_interview=avg_interview,
        avg_days_applied_to_offer=avg_offer,
        most_active_day_of_week=best_day,
        most_active_hour=best_hour,
        applications_per_week=apps_per_week,
    )


def _compute_patterns(applications: list) -> PatternInsights:
    company_counter: Counter = Counter()
    role_counter: Counter = Counter()
    response_by_type: dict[str, int] = defaultdict(int)
    score_by_role: dict[str, list[float]] = defaultdict(list)

    for app in applications:
        jd = _get_attr(app, "jd")
        company = ""
        title = ""
        if jd:
            company = _get_attr(jd, "company", "") or ""
            title = _get_attr(jd, "title", "") or ""
            if company:
                company_counter[company] += 1
            if title:
                role_counter[title] += 1

        ats = _get_attr(app, "ats_score_after") or _get_attr(app, "ats_score_before")
        status = _get_status(app)
        if ats and title:
            score_by_role[title].append(ats)
        if status in _RESPONSE_STATUSES and company:
            response_by_type[company] += 1

    top_company = company_counter.most_common(1)[0][0] if company_counter else ""
    top_responding = max(response_by_type, key=response_by_type.get) if response_by_type else ""
    best_role = ""
    if score_by_role:
        best_role = max(score_by_role, key=lambda k: sum(score_by_role[k]) / len(score_by_role[k]))

    # Simple size classification based on count (heuristic)
    size_dist: dict[str, int] = {"startup": 0, "mid": 0, "enterprise": 0}
    for company, count in company_counter.items():
        lower = company.lower()
        from backend.agents.tailor.weightage.company_profiles import get_company_profile
        profile = get_company_profile(company)
        if profile and profile.id == "early_stage_startup":
            size_dist["startup"] += count
        elif profile and profile.id in ("faang_generic", "google", "meta", "netflix"):
            size_dist["enterprise"] += count
        else:
            size_dist["mid"] += count

    return PatternInsights(
        company_size_distribution=size_dist,
        role_type_distribution=dict(role_counter.most_common(10)),
        top_responding_company_type=top_responding,
        highest_avg_score_role_type=best_role,
        most_applied_to_company=top_company,
    )


def _compute_predictions(funnel: FunnelMetrics, timing: TimingAnalysis) -> Predictions:
    rates = funnel.conversion_rates
    interview_rate = rates.get("applied_to_response", 0) * rates.get("response_to_interview", 0)
    offer_rate = rates.get("interview_to_offer", 0)

    # Apps per week from timing data
    week_counts = [w.count for w in timing.applications_per_week]
    apps_per_week = sum(week_counts) / len(week_counts) if week_counts else 0

    if offer_rate > 0 and interview_rate > 0 and apps_per_week > 0:
        interviews_needed = 1.0 / offer_rate
        apps_needed = interviews_needed / interview_rate
        weeks = apps_needed / apps_per_week
        estimated_weeks = round(min(weeks, 52), 1)  # cap at 1 year
    else:
        estimated_weeks = 0.0  # insufficient data

    # Recommended volume: to get offer in 8 weeks
    if interview_rate > 0 and offer_rate > 0:
        target_weeks = 8
        apps_needed = (1.0 / offer_rate) / interview_rate
        recommended = max(1, math.ceil(apps_needed / target_weeks))
    else:
        recommended = INDUSTRY_BENCHMARKS.get("avg_apps_per_week_active_seeker", 10)

    # Trajectory
    if funnel.offers_received > 0:
        trajectory = "on_track"
    elif funnel.interviews_scheduled > 0 and apps_per_week >= 5:
        trajectory = "on_track"
    elif funnel.jobs_applied > 0 and funnel.responses_received == 0:
        trajectory = "needs_better_targeting"
    elif apps_per_week < 5:
        trajectory = "needs_more_volume"
    else:
        trajectory = "needs_more_volume"

    return Predictions(
        estimated_weeks_to_offer=estimated_weeks,
        recommended_weekly_volume=recommended,
        current_trajectory=trajectory,
    )


def _compute_wins(applications: list) -> list[str]:
    wins = []
    for app in applications:
        status = _get_status(app)
        jd = _get_attr(app, "jd")
        company = ""
        if jd:
            company = _get_attr(jd, "company", "") or ""

        if status == "offer":
            wins.append(f"Offer received from {company}" if company else "Offer received")
        elif status == "interviewing":
            wins.append(f"Interview scheduled at {company}" if company else "Interview scheduled")
        elif status == "submitted":
            wins.append(f"Application submitted to {company}" if company else "Application submitted")

    return wins[:5]


def _compute_focus_areas(heatmap: DimensionHeatmap) -> list[str]:
    areas = []
    for dim_id in heatmap.weakest_dimensions:
        avg = heatmap.dimension_averages.get(dim_id, 0)
        name = dim_id.replace("_", " ").title()
        if avg < 50:
            areas.append(f"Improve {name} (avg: {avg:.0f}/100)")
        elif avg < 70:
            areas.append(f"Strengthen {name} (avg: {avg:.0f}/100)")
    if not areas:
        areas.append("Scores are strong across the board — focus on volume")
    return areas[:3]


async def compute_analytics_ai(
    applications: list,
    score_history: list[dict] | None = None,
) -> JobSearchAnalytics:
    """
    compute_analytics + Claude-generated one_sentence_summary.
    Falls back to heuristic summary if Claude is unavailable.
    """
    result = compute_analytics(applications, score_history)
    try:
        from backend.agents.llm import ask
        system = """You are a career advisor. Generate a single, insightful sentence summarizing a job seeker's current situation.

Rules:
- Reference actual numbers from the data
- Be specific and actionable, not generic
- Max 35 words
- No filler phrases like "You are doing great!" unless genuinely warranted
- Output ONLY the sentence — no labels, no quotes"""

        f = result.funnel
        rates = f.conversion_rates
        user = f"""Applied: {f.jobs_applied} | Responses: {f.responses_received} | Interviews: {f.interviews_scheduled} | Offers: {f.offers_received}
Response rate: {rates.get('applied_to_response', 0):.0%} | Interview rate: {rates.get('applied_to_response', 0) * rates.get('response_to_interview', 0):.0%}
Improving: {result.is_improving} | Trajectory: {result.predictions.current_trajectory}
Weakest dimensions: {', '.join(result.dimension_heatmap.weakest_dimensions) or 'none yet'}"""

        sentence = (await ask(system, user, model="claude-haiku-4-5-20251001", max_tokens=80)).strip().strip('"')
        result.one_sentence_summary = sentence
    except Exception:
        pass
    return result


def _build_summary(funnel: FunnelMetrics, timing: TimingAnalysis, is_improving: bool) -> str:
    weeks = len(timing.applications_per_week)
    week_counts = [w.count for w in timing.applications_per_week]
    apps_per_week = round(sum(week_counts) / len(week_counts), 1) if week_counts else 0

    response_rate = funnel.conversion_rates.get("applied_to_response", 0)
    rate_str = f"{response_rate:.0%}" if response_rate > 0 else "unknown"

    benchmark = INDUSTRY_BENCHMARKS["applied_to_response"]
    comparison = "above" if response_rate > benchmark else "below" if response_rate < benchmark else "at"

    trend = "improving" if is_improving else "stable"

    if funnel.jobs_applied == 0:
        return "No applications submitted yet — start by tailoring your resume to your top target roles."

    return (
        f"You're averaging {apps_per_week} apps/week with a {rate_str} response rate "
        f"({comparison} average). Scores are {trend}. "
        f"Total: {funnel.jobs_applied} applied, {funnel.interviews_scheduled} interviews, "
        f"{funnel.offers_received} offers."
    )
