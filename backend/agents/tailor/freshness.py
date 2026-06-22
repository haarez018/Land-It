"""Resume Freshness Decay: scores how current and up-to-date a resume is."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from backend.parsers.schemas import Resume


@dataclass
class FreshnessReport:
    freshness_score: float
    decay_factors: list[str]
    stale_sections: list[str]
    last_role_recency: str
    skills_currency: float
    format_modernity: float
    refresh_suggestions: list[str]


_OUTDATED_SIGNALS = [
    (re.compile(r"\bobjective\b", re.I), "Has 'Objective' section instead of 'Summary'", 20),
    (re.compile(r"\breferences available\b", re.I), "'References available upon request' is outdated", 15),
    (re.compile(r"\bMS Office\b", re.I), "Listing 'MS Office' is no longer necessary", 5),
    (re.compile(r"\bMicrosoft Word\b", re.I), "Listing 'Microsoft Word' adds no value", 5),
]

_DEPRECATED_TECH = {"jquery", "backbone", "coffeescript", "perl", "flash", "actionscript", "coldfusion", "soap"}


def analyze_freshness(resume: Resume) -> FreshnessReport:
    score = 100.0
    decay: list[str] = []
    stale: list[str] = []
    suggestions: list[str] = []
    today = date.today()

    # 1. Latest role recency
    recency = "no_jobs"
    if resume.work_experience:
        latest = resume.work_experience[0]
        if latest.end_date is None:
            recency = "current"
        else:
            months_since = (today.year - latest.end_date.year) * 12 + (today.month - latest.end_date.month)
            if months_since <= 3:
                recency = "ended_recently"
                score -= 10
            elif months_since <= 12:
                recency = "ended_6_months"
                score -= 25
                decay.append(f"Most recent role ended {months_since} months ago")
                suggestions.append("Update with recent freelance, projects, or volunteer work")
            elif months_since <= 24:
                recency = "ended_long_ago"
                score -= 45
                decay.append(f"Most recent role ended {months_since} months ago")
            else:
                recency = "very_stale"
                score -= 60
                decay.append("No roles in the last 2+ years")
                stale.append("experience")
    else:
        score -= 40
        decay.append("No work experience listed")

    # 2. Skills currency
    all_skills = set()
    for sl in resume.skills.values():
        all_skills.update(s.lower() for s in sl)
    deprecated_found = all_skills & _DEPRECATED_TECH
    if deprecated_found:
        penalty = len(deprecated_found) * 5
        score -= penalty
        decay.append(f"Deprecated technologies listed: {', '.join(deprecated_found)}")
        stale.append("skills")
        suggestions.append(f"Remove or deprioritize: {', '.join(deprecated_found)}")
    skills_currency = max(0, 100 - len(deprecated_found) * 10)

    # 3. Format modernity
    format_score = 100.0
    for pattern, desc, pen in _OUTDATED_SIGNALS:
        if pattern.search(resume.raw_text):
            format_score -= pen
            score -= pen * 0.5
            decay.append(desc)
            suggestions.append(f"Fix: {desc}")
    if format_score < 60:
        stale.append("format")

    # 4. Too much history
    if len(resume.work_experience) > 6:
        score -= 5
        decay.append("Too many roles listed — consider trimming older positions")
        suggestions.append("Keep only the last 10-15 years of experience")

    score = max(0, min(100, score))

    return FreshnessReport(
        freshness_score=round(score, 1),
        decay_factors=decay,
        stale_sections=stale,
        last_role_recency=recency,
        skills_currency=round(skills_currency, 1),
        format_modernity=round(max(0, format_score), 1),
        refresh_suggestions=suggestions,
    )
