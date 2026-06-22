"""
Industry benchmarks for job search funnel metrics.

Published data sources:
  - Jobvite 2023 Recruiting Benchmark Report
  - Glassdoor Economic Research
  - LinkedIn Talent Insights
  - NACE Job Outlook surveys
"""

from __future__ import annotations


INDUSTRY_BENCHMARKS: dict[str, float] = {
    "applied_to_response": 0.08,          # 8% of applications get any response
    "response_to_interview": 0.50,         # 50% of responses lead to an interview
    "interview_to_offer": 0.20,            # 20% of interviews result in an offer
    "applied_to_interview": 0.04,          # 4% of applications lead to interview
    "applied_to_offer": 0.008,             # 0.8% of applications lead to offer
    "avg_days_to_response": 14.0,          # 2 weeks average
    "avg_days_to_interview": 21.0,         # 3 weeks from application
    "avg_days_to_offer": 45.0,             # ~6 weeks from application
    "avg_apps_per_week_active_seeker": 10,  # Active job seekers apply ~10/week
}


def compare_to_benchmark(user_rate: float, benchmark: float) -> str:
    """
    Compare a user's rate to the industry benchmark.

    Returns a human-readable string like "+87% above average" or "-20% below average".
    """
    if benchmark == 0:
        return "no benchmark"

    pct_diff = (user_rate - benchmark) / benchmark * 100

    if abs(pct_diff) < 5:
        return "on par with average"
    elif pct_diff > 0:
        return f"+{pct_diff:.0f}% above average"
    else:
        return f"{pct_diff:.0f}% below average"
