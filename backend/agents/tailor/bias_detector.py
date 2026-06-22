"""Resume Bias Detector: flags gendered, age, cultural, and disability bias signals."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from backend.parsers.schemas import Resume


@dataclass
class BiasFlag:
    text: str
    bias_type: str
    severity: str
    explanation: str
    suggestion: str
    location: str


@dataclass
class BiasReport:
    total_flags: int
    flags: list[BiasFlag]
    bias_free_score: float
    gendered_flags: int
    age_flags: int
    cultural_flags: int
    assessment: str
    top_priority_fix: str | None


MASCULINE_CODED: dict[str, tuple[str | None, str]] = {
    "aggressive": ("assertive", "medium"),
    "dominant": ("leading", "medium"),
    "competitive": ("achievement-oriented", "low"),
    "ninja": ("expert", "high"),
    "rockstar": ("high-performer", "high"),
    "guru": ("specialist", "high"),
    "manpower": ("workforce", "medium"),
    "chairman": ("chairperson", "medium"),
    "guys": ("team", "low"),
    "man-hours": ("person-hours", "medium"),
    "manned": ("staffed", "low"),
    "brotherhood": ("community", "medium"),
    "fireman": ("firefighter", "low"),
    "salesman": ("sales representative", "medium"),
    "craftsman": ("artisan", "low"),
    "hacker": ("engineer", "low"),
    "warrior": ("champion", "medium"),
    "crush it": ("excel", "low"),
    "kill it": ("excel", "low"),
}

FEMININE_CODED: dict[str, tuple[str | None, str]] = {
    "nurturing": ("supportive", "low"),
    "emotional": ("empathetic", "medium"),
    "gentle": ("measured", "low"),
}

_AGE_PATTERNS: list[tuple[re.Pattern, str, str, str]] = [
    (re.compile(r"\b(19[5-8]\d)\b(?![-/]\d)"),
     "Graduation year reveals age — may trigger age discrimination",
     "Remove graduation year if over 15 years ago", "medium"),
    (re.compile(r"\b(seasoned|veteran|mature)\b", re.I),
     "Age-coded language can trigger bias",
     "Replace with specific accomplishments", "medium"),
    (re.compile(r"\b(young|energetic|digital native|fresh perspective)\b", re.I),
     "Youth-coded language can trigger bias",
     "Replace with specific skills or achievements", "medium"),
    (re.compile(r"\breferences available upon request\b", re.I),
     "Outdated resume convention signals age",
     "Remove this line entirely — it's assumed", "low"),
]

_CULTURAL_PATTERNS: list[tuple[re.Pattern, str, str, str]] = [
    (re.compile(r"(?:native|mother)\s*tongue", re.I),
     "'Native tongue' can imply non-native speaker bias",
     "Use 'fluent in' or 'native-level proficiency'", "low"),
    (re.compile(r"\b(?:nationality|citizenship|visa status)\b", re.I),
     "Citizenship/visa status can trigger bias",
     "Remove unless legally required for the role", "medium"),
    (re.compile(r"\bforeign\b", re.I),
     "'Foreign' has negative connotations",
     "Use 'international' instead", "low"),
]

_DISABILITY_PATTERNS: list[tuple[re.Pattern, str, str, str]] = [
    (re.compile(r"(?:despite|overcame?)\s+(?:my\s+)?(?:disability|condition|illness|diagnosis)", re.I),
     "Medical disclosure can trigger unconscious bias",
     "Focus on capabilities and achievements instead", "high"),
]


def detect_bias(resume: Resume) -> BiasReport:
    flags: list[BiasFlag] = []
    text = resume.raw_text

    # Gendered language
    text_lower = text.lower()
    for word, (replacement, severity) in MASCULINE_CODED.items():
        if re.search(r"\b" + re.escape(word) + r"\b", text_lower):
            suggestion = f"Replace '{word}' with '{replacement}'" if replacement else f"Consider removing '{word}'"
            flags.append(BiasFlag(
                text=word, bias_type="gendered", severity=severity,
                explanation=f"'{word}' is masculine-coded language that may deter diverse candidates",
                suggestion=suggestion, location="resume_text",
            ))

    for word, (replacement, severity) in FEMININE_CODED.items():
        if re.search(r"\b" + re.escape(word) + r"\b", text_lower):
            suggestion = f"Replace '{word}' with '{replacement}'" if replacement else f"Consider removing '{word}'"
            flags.append(BiasFlag(
                text=word, bias_type="gendered", severity=severity,
                explanation=f"'{word}' is feminine-coded language",
                suggestion=suggestion, location="resume_text",
            ))

    # Age signals
    for pattern, explanation, suggestion, severity in _AGE_PATTERNS:
        for m in pattern.finditer(text):
            matched = m.group(0)
            if m.groups() and m.group(1).isdigit():
                year = int(m.group(1))
                from datetime import date
                if date.today().year - year < 15:
                    continue
            flags.append(BiasFlag(
                text=matched, bias_type="age", severity=severity,
                explanation=explanation, suggestion=suggestion, location="resume_text",
            ))

    # Cultural signals
    for pattern, explanation, suggestion, severity in _CULTURAL_PATTERNS:
        for m in pattern.finditer(text):
            flags.append(BiasFlag(
                text=m.group(0), bias_type="cultural", severity=severity,
                explanation=explanation, suggestion=suggestion, location="resume_text",
            ))

    # Disability signals
    for pattern, explanation, suggestion, severity in _DISABILITY_PATTERNS:
        for m in pattern.finditer(text):
            flags.append(BiasFlag(
                text=m.group(0), bias_type="disability", severity=severity,
                explanation=explanation, suggestion=suggestion, location="resume_text",
            ))

    # Score
    high_count = sum(1 for f in flags if f.severity == "high")
    medium_count = sum(1 for f in flags if f.severity == "medium")
    low_count = sum(1 for f in flags if f.severity == "low")
    penalty = high_count * 10 + medium_count * 5 + low_count * 2
    score = max(0.0, min(100.0, 100 - penalty))

    if score >= 95:
        assessment = "Clean"
    elif score >= 75:
        assessment = "Minor issues"
    else:
        assessment = "Needs attention"

    top_fix = None
    high_flags = [f for f in flags if f.severity == "high"]
    if high_flags:
        top_fix = high_flags[0].suggestion

    return BiasReport(
        total_flags=len(flags),
        flags=flags,
        bias_free_score=round(score, 1),
        gendered_flags=sum(1 for f in flags if f.bias_type == "gendered"),
        age_flags=sum(1 for f in flags if f.bias_type == "age"),
        cultural_flags=sum(1 for f in flags if f.bias_type == "cultural"),
        assessment=assessment,
        top_priority_fix=top_fix,
    )
