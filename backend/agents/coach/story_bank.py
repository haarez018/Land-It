"""STAR Story Bank: personal interview story library with question-type mapping."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class STARStory:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = ""
    situation: str = ""
    task: str = ""
    action: str = ""
    result: str = ""
    tags: list[str] = field(default_factory=list)
    company_context: str = ""
    metrics: list[str] = field(default_factory=list)
    question_types: list[str] = field(default_factory=list)
    strength_signals: list[str] = field(default_factory=list)
    specificity_score: float = 0
    impact_score: float = 0
    relevance_tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_used_for: str | None = None


@dataclass
class StoryBankAnalysis:
    total_stories: int
    question_types_covered: int
    question_types_total: int
    coverage_percentage: float
    gaps: list[str]
    weak_areas: list[str]
    strongest_areas: list[str]
    recommendation: str


QUESTION_TYPE_MAP: dict[str, list[str]] = {
    "conflict": ["disagree", "conflict", "difficult coworker", "push back", "different opinion", "challenged"],
    "failure": ["mistake", "failed", "wrong", "setback", "learned from", "didn't go well", "regret"],
    "leadership": ["led", "motivated", "team", "influence without authority", "mentored", "guided"],
    "technical_challenge": ["complex problem", "technical challenge", "debug", "architecture", "system design", "scale"],
    "ambiguity": ["unclear", "ambiguous", "no clear direction", "figured out", "uncertainty"],
    "time_pressure": ["deadline", "tight timeline", "prioritize", "time constraint", "crunch", "urgent"],
    "customer_focus": ["customer", "user", "stakeholder", "client", "user feedback"],
    "innovation": ["creative", "innovative", "new approach", "out of the box", "improved process", "initiative"],
    "collaboration": ["cross-functional", "worked with", "partnered", "collaborated", "aligned", "consensus"],
    "growth": ["feedback", "grew", "improved", "learned", "developed skill", "outside comfort zone"],
}


def classify_question(question: str) -> str:
    q_lower = question.lower()
    scores: dict[str, int] = {}
    for qtype, keywords in QUESTION_TYPE_MAP.items():
        score = sum(1 for kw in keywords if kw in q_lower)
        if score > 0:
            scores[qtype] = score
    return max(scores, key=scores.get) if scores else "general"


def score_specificity(story: STARStory) -> float:
    score = 0.0
    if story.company_context and len(story.company_context) > 10:
        score += 20
    score += min(len(story.metrics) * 15, 30)
    if len(story.situation.split()) > 50:
        score += 15
    if len(story.action.split()) > 80:
        score += 20
    if any(c.isdigit() for c in story.result):
        score += 15
    return min(score, 100)


def score_impact(story: STARStory) -> float:
    score = 0.0
    result_text = story.result.lower()
    if re.search(r"\$[\d,]+[KMBkmb]?", story.result):
        score += 25
    if re.search(r"\d+%", story.result):
        score += 20
    if re.search(r"\d+[KMBkmb]\+?\s*(?:users|customers|requests)", story.result, re.I):
        score += 20
    if any(w in result_text for w in ["promoted", "awarded", "recognized"]):
        score += 15
    if any(w in result_text for w in ["adopted", "org-wide", "company-wide"]):
        score += 20
    return min(score, 100)


def infer_question_types(story: STARStory) -> list[str]:
    combined = f"{story.situation} {story.task} {story.action} {story.result}".lower()
    types: list[str] = []
    for qtype, keywords in QUESTION_TYPE_MAP.items():
        if any(kw in combined for kw in keywords):
            types.append(qtype)
    return types or ["general"]


class StoryBank:
    def __init__(self) -> None:
        self._stories: list[STARStory] = []

    def add_story(self, story: STARStory) -> STARStory:
        story.question_types = infer_question_types(story)
        story.specificity_score = score_specificity(story)
        story.impact_score = score_impact(story)
        self._stories.append(story)
        return story

    def get_stories(self) -> list[STARStory]:
        return list(self._stories)

    def get_story_for_question(self, question: str) -> list[STARStory]:
        qtype = classify_question(question)
        matched = [s for s in self._stories if qtype in s.question_types]
        return sorted(matched, key=lambda s: s.impact_score, reverse=True)

    def analyze_coverage(self) -> StoryBankAnalysis:
        total_types = len(QUESTION_TYPE_MAP)
        covered_types: dict[str, list[STARStory]] = {}
        for s in self._stories:
            for qt in s.question_types:
                covered_types.setdefault(qt, []).append(s)

        covered = len(covered_types)
        gaps = [qt for qt in QUESTION_TYPE_MAP if qt not in covered_types]
        weak = [qt for qt, stories in covered_types.items() if all(s.impact_score < 50 for s in stories)]
        strong = [qt for qt, stories in covered_types.items() if any(s.impact_score >= 70 for s in stories)]
        pct = (covered / total_types * 100) if total_types > 0 else 0

        rec = ""
        if gaps:
            rec = f"You need stories about: {', '.join(gaps[:3])}"
        elif weak:
            rec = f"Strengthen stories for: {', '.join(weak[:3])}"
        else:
            rec = "Good coverage! Practice delivering your stories."

        return StoryBankAnalysis(
            total_stories=len(self._stories),
            question_types_covered=covered,
            question_types_total=total_types,
            coverage_percentage=round(pct, 1),
            gaps=gaps, weak_areas=weak, strongest_areas=strong,
            recommendation=rec,
        )

    def clear(self) -> None:
        self._stories.clear()


story_bank = StoryBank()
