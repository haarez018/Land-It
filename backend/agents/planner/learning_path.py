"""Personalized Learning Path Generator: bridges skill gaps to resources."""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.agents.tailor.skill_gap import SkillGapAnalysis


@dataclass
class LearningResource:
    name: str
    type: str
    provider: str
    estimated_hours: int
    cost: str
    credibility_boost: float


@dataclass
class LearningStep:
    skill: str
    current_level: str
    target_level: str
    resources: list[LearningResource]
    estimated_weeks: int
    resume_impact: str
    proof_of_learning: str


@dataclass
class LearningPlan:
    total_weeks: int
    total_estimated_hours: int
    steps: list[LearningStep]
    quick_wins: list[LearningStep]
    medium_term: list[LearningStep]
    long_term: list[LearningStep]
    expected_score_improvement: float
    expected_callback_improvement: float


LEARNING_RESOURCES: dict[str, list[LearningResource]] = {
    "kubernetes": [
        LearningResource("CKA Certification", "certification", "CNCF", 40, "$395", 12.0),
        LearningResource("K8s the Hard Way", "tutorial", "GitHub", 15, "free", 5.0),
    ],
    "rust": [
        LearningResource("The Rust Book", "book", "rust-lang.org", 30, "free", 3.0),
        LearningResource("Build a CLI in Rust", "project", "self-guided", 20, "free", 8.0),
    ],
    "go": [
        LearningResource("Go by Example", "tutorial", "gobyexample.com", 10, "free", 3.0),
        LearningResource("Build a REST API in Go", "project", "self-guided", 15, "free", 7.0),
    ],
    "system_design": [
        LearningResource("DDIA Book", "book", "O'Reilly", 40, "$45", 5.0),
        LearningResource("System Design Interview Course", "course", "Various", 20, "$79", 4.0),
    ],
    "docker": [
        LearningResource("Docker Deep Dive", "book", "Pluralsight", 12, "$30", 4.0),
        LearningResource("Containerize Your App", "project", "self-guided", 8, "free", 6.0),
    ],
    "terraform": [
        LearningResource("HashiCorp Terraform Associate", "certification", "HashiCorp", 30, "$70", 10.0),
    ],
    "react": [
        LearningResource("React.dev Tutorial", "tutorial", "react.dev", 15, "free", 3.0),
        LearningResource("Build a Full-Stack App", "project", "self-guided", 25, "free", 8.0),
    ],
    "typescript": [
        LearningResource("TypeScript Handbook", "tutorial", "typescriptlang.org", 10, "free", 3.0),
    ],
    "aws": [
        LearningResource("AWS Solutions Architect", "certification", "AWS", 60, "$300", 15.0),
        LearningResource("AWS Free Tier Projects", "project", "AWS", 20, "free", 5.0),
    ],
    "python": [
        LearningResource("Python for Professionals", "course", "Various", 15, "free", 2.0),
    ],
    "graphql": [
        LearningResource("GraphQL Official Tutorial", "tutorial", "graphql.org", 8, "free", 3.0),
    ],
    "kafka": [
        LearningResource("Confluent Kafka Course", "course", "Confluent", 20, "free", 6.0),
    ],
}


def generate_learning_plan(
    skill_gaps: SkillGapAnalysis,
    available_hours_per_week: int = 10,
) -> LearningPlan:
    steps: list[LearningStep] = []
    total_hours = 0

    all_gaps = skill_gaps.critical_gaps + skill_gaps.recommended_gaps + skill_gaps.bonus_gaps

    for gap in all_gaps:
        skill_key = gap.skill.lower().replace(" ", "_").replace(".", "")
        resources = LEARNING_RESOURCES.get(skill_key, [])
        if not resources:
            resources = [LearningResource(
                f"Learn {gap.skill}", "tutorial", "Various", 15, "free", 3.0,
            )]

        hours = sum(r.estimated_hours for r in resources)
        weeks = max(1, hours // available_hours_per_week)
        total_hours += hours
        boost = sum(r.credibility_boost for r in resources)

        steps.append(LearningStep(
            skill=gap.skill,
            current_level="none" if gap.difficulty == "hard" else "beginner",
            target_level="intermediate" if gap.difficulty != "hard" else "beginner",
            resources=resources,
            estimated_weeks=weeks,
            resume_impact=f"+{gap.score_impact:.0f} pts estimated score gain",
            proof_of_learning=resources[0].name if resources else f"Build a project with {gap.skill}",
        ))

    quick = [s for s in steps if s.estimated_weeks <= 1]
    medium = [s for s in steps if 1 < s.estimated_weeks <= 4]
    long = [s for s in steps if s.estimated_weeks > 4]
    total_weeks = max(1, total_hours // available_hours_per_week) if total_hours else 0

    return LearningPlan(
        total_weeks=total_weeks,
        total_estimated_hours=total_hours,
        steps=steps,
        quick_wins=quick,
        medium_term=medium,
        long_term=long,
        expected_score_improvement=skill_gaps.total_potential_score_gain,
        expected_callback_improvement=round(skill_gaps.total_potential_score_gain * 0.3, 1),
    )
