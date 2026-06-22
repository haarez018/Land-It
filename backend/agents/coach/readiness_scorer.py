"""Interview Readiness Score: composite metric showing preparation level."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ReadinessScore:
    total: float
    resume_score: float
    story_coverage: float
    mock_interview_score: float
    skill_gap_coverage: float
    company_research: float
    readiness_level: str
    gaps: list[str]
    next_steps: list[str]


def calculate_readiness(
    resume_combined_score: float = 0,
    story_coverage_pct: float = 0,
    mock_avg_score: float = 0,
    skill_gaps_addressed_pct: float = 0,
    company_researched: bool = False,
) -> ReadinessScore:
    resume_component = min(resume_combined_score, 100) * 0.30
    story_component = min(story_coverage_pct, 100) * 0.20
    mock_component = min(mock_avg_score, 100) * 0.25
    gap_component = min(skill_gaps_addressed_pct, 100) * 0.15
    research_component = 100.0 * 0.10 if company_researched else 0

    total = resume_component + story_component + mock_component + gap_component + research_component
    total = round(min(100, total), 1)

    if total >= 80:
        level = "ready"
    elif total >= 60:
        level = "almost"
    elif total >= 30:
        level = "needs_work"
    else:
        level = "not_started"

    gaps: list[str] = []
    next_steps: list[str] = []

    if resume_combined_score < 60:
        gaps.append("Resume needs improvement")
        next_steps.append("Score and tailor your resume against the target JD")
    if story_coverage_pct < 50:
        gaps.append("Story bank incomplete")
        next_steps.append("Add STAR stories covering conflict, failure, and leadership")
    if mock_avg_score < 50:
        gaps.append("Mock interview practice needed")
        next_steps.append("Complete at least 2 mock interview sessions")
    if skill_gaps_addressed_pct < 30:
        gaps.append("Skill gaps not addressed")
        next_steps.append("Start the learning plan for your top skill gaps")
    if not company_researched:
        gaps.append("Company research missing")
        next_steps.append("Research the target company's products, culture, and team")

    return ReadinessScore(
        total=total,
        resume_score=round(resume_component / 0.30, 1) if resume_combined_score else 0,
        story_coverage=round(story_component / 0.20, 1) if story_coverage_pct else 0,
        mock_interview_score=round(mock_component / 0.25, 1) if mock_avg_score else 0,
        skill_gap_coverage=round(gap_component / 0.15, 1) if skill_gaps_addressed_pct else 0,
        company_research=100.0 if company_researched else 0,
        readiness_level=level,
        gaps=gaps,
        next_steps=next_steps,
    )
