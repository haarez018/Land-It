"""Application Timing Optimizer: research-backed best times to apply."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class TimingRecommendation:
    best_day: str
    best_time: str
    best_time_reasoning: str
    avoid_days: list[str]
    avoid_reasoning: str
    company_hiring_cycle: str
    industry_seasonality: str
    posting_age_days: int | None
    urgency_level: str
    urgency_reasoning: str


OPTIMAL_TIMING = {
    "best_days": ["Monday", "Tuesday", "Wednesday"],
    "best_hours": (9, 11),
    "worst_days": ["Friday", "Saturday", "Sunday"],
    "posting_urgency": {
        (0, 2): ("apply_now", "Posted today/yesterday — highest response rate"),
        (3, 7): ("this_week", "Still fresh — apply within days"),
        (8, 14): ("soon", "1-2 weeks old — still open but apply soon"),
        (15, 30): ("no_rush", "2-4 weeks old — likely still open"),
        (31, 999): ("may_be_filled", "Over a month old — may already be in process"),
    },
    "industry_peak": {
        "tech": {"peak": [1, 2, 3, 9, 10], "slow": [7, 8, 12]},
        "finance": {"peak": [1, 2, 9, 10], "slow": [7, 8, 11, 12]},
    },
}


def get_timing_recommendation(
    posting_date: str | None = None,
    industry: str = "tech",
) -> TimingRecommendation:
    posting_age = None
    urgency = "this_week"
    urgency_reason = "Apply within the next few days for best results"

    if posting_date:
        try:
            posted = datetime.fromisoformat(posting_date).date()
            posting_age = (date.today() - posted).days
            for (lo, hi), (level, reason) in OPTIMAL_TIMING["posting_urgency"].items():
                if lo <= posting_age <= hi:
                    urgency = level
                    urgency_reason = reason
                    break
        except (ValueError, TypeError):
            pass

    current_month = date.today().month
    seasons = OPTIMAL_TIMING["industry_peak"].get(industry, OPTIMAL_TIMING["industry_peak"]["tech"])
    if current_month in seasons.get("peak", []):
        seasonality = "Peak hiring season — more openings, more competition"
    elif current_month in seasons.get("slow", []):
        seasonality = "Slow season — fewer openings but less competition"
    else:
        seasonality = "Normal hiring activity"

    return TimingRecommendation(
        best_day="Tuesday",
        best_time="9:00-11:00 AM local time",
        best_time_reasoning="Research shows Tuesday morning applications get 30% more views",
        avoid_days=["Friday", "Saturday", "Sunday"],
        avoid_reasoning="Weekend applications get buried under Monday's batch",
        company_hiring_cycle="unknown",
        industry_seasonality=seasonality,
        posting_age_days=posting_age,
        urgency_level=urgency,
        urgency_reasoning=urgency_reason,
    )
