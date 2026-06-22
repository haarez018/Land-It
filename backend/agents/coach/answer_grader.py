"""
Grade interview answers on 5 dimensions:
  1. Structure (0-25): STAR/CAR format, logical flow
  2. Specificity (0-25): Real examples, named projects, concrete details
  3. Relevance (0-25): Actually answers the question asked
  4. Impact (0-15): Outcomes, metrics, quantifiable results
  5. Communication (0-10): Clarity, conciseness, no filler

Uses heuristic-based grading (no LLM required).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from backend.agents.coach.question_generator import InterviewQuestion


@dataclass
class DimensionGrade:
    """Score for a single grading dimension."""
    name: str
    score: int
    max_score: int
    feedback: str


@dataclass
class AnswerGrade:
    """Complete grade for an interview answer."""
    question_id: str
    overall_score: int  # 0-100
    max_score: int  # 100
    dimensions: list[DimensionGrade]
    strengths: list[str]
    improvements: list[str]
    model_answer: str
    red_flags_triggered: list[str]


# ── Heuristic grading helpers ──────────────────────────────────────────────

_STAR_INDICATORS = {
    "situation": [
        r"\b(at|when|while|during|in my)\b.*\b(role|position|project|team|company)\b",
        r"\b(situation|context|background)\b",
        r"\b(we (were|had|faced|needed))\b",
    ],
    "task": [
        r"\b(my (role|responsibility|job|task) was)\b",
        r"\b(i (was tasked|needed to|was responsible|was asked))\b",
        r"\b(the (goal|objective|challenge) was)\b",
    ],
    "action": [
        r"\b(i (built|designed|implemented|created|led|wrote|developed|architected|proposed|analyzed|coordinated|refactored))\b",
        r"\b(i (decided to|chose to|started by|then i))\b",
        r"\b(my approach was)\b",
    ],
    "result": [
        r"\b(result(ed)?|outcome|impact|led to|saved|reduced|increased|improved|grew)\b",
        r"\d+[%$KMBxX]",
        r"\b(as a result|this (led|resulted)|ultimately|in the end)\b",
    ],
}

_FILLER_WORDS = [
    r"\b(um|uh|like|you know|basically|actually|honestly|literally|so yeah|i mean)\b",
]

_METRIC_PATTERNS = [
    r"\d+%",
    r"\$[\d,]+[KMBkmb]?",
    r"\d+x\b",
    r"\d+\s*(users|customers|requests|transactions|team members|engineers|people)",
    r"\d+\s*(ms|seconds|minutes|hours|days|weeks|months)",
    r"(saved|reduced|improved|increased)\s+\w+\s+by\s+\d+",
]

_SPECIFIC_INDICATORS = [
    r"\b(at [A-Z]\w+)\b",  # "at Google", "at my previous company"
    r"\b(using [A-Z]\w+)\b",  # "using Kubernetes"
    r"\b(in 20\d\d)\b",  # "in 2023"
    r"(our|my|the) team of \d+",
    r"\b([A-Z]\w+(?:DB|SQL|JS|API|AWS|GCP|Azure))\b",  # named tech
]


def _score_structure(answer: str) -> tuple[int, str]:
    """Score STAR structure (0-25)."""
    answer_lower = answer.lower()
    components_found: list[str] = []

    for component, patterns in _STAR_INDICATORS.items():
        for pattern in patterns:
            if re.search(pattern, answer_lower):
                components_found.append(component)
                break

    unique_components = set(components_found)
    count = len(unique_components)

    # Score based on components present
    if count >= 4:
        score = 22 + min(3, len(answer.split("\n")))  # bonus for paragraph structure
        feedback = "Excellent STAR structure with all key components."
    elif count == 3:
        missing = {"situation", "task", "action", "result"} - unique_components
        score = 16
        feedback = f"Good structure but missing: {', '.join(missing)}."
    elif count == 2:
        score = 10
        feedback = "Partial structure. Try organizing with Situation, Task, Action, Result."
    else:
        score = 5
        feedback = "Unstructured answer. Use STAR format: Situation, Task, Action, Result."

    return min(25, score), feedback


def _score_specificity(answer: str) -> tuple[int, str]:
    """Score specificity and concrete details (0-25)."""
    score = 5  # base
    details: list[str] = []

    # Named entities / specific indicators
    specific_count = 0
    for pattern in _SPECIFIC_INDICATORS:
        matches = re.findall(pattern, answer)
        specific_count += len(matches)

    if specific_count >= 4:
        score += 10
        details.append("rich specific details")
    elif specific_count >= 2:
        score += 6
        details.append("some specific details")
    else:
        details.append("lacks concrete details — name projects, tools, and companies")

    # Metrics
    metric_count = sum(
        1 for p in _METRIC_PATTERNS if re.search(p, answer, re.IGNORECASE)
    )
    if metric_count >= 3:
        score += 10
        details.append("multiple quantified outcomes")
    elif metric_count >= 1:
        score += 5
        details.append("some quantified outcomes")
    else:
        details.append("add numbers and metrics")

    feedback = "; ".join(details).capitalize() + "."
    return min(25, score), feedback


def _score_relevance(answer: str, question: InterviewQuestion) -> tuple[int, str]:
    """Score how well the answer addresses the question (0-25)."""
    answer_lower = answer.lower()
    question_lower = question.text.lower()

    # Extract key topics from the question
    question_keywords = set(re.findall(r"\b\w{4,}\b", question_lower))
    # Remove common words
    stopwords = {"what", "when", "where", "which", "about", "have", "your", "that",
                 "this", "with", "from", "they", "been", "were", "does", "will",
                 "would", "could", "should", "tell", "describe", "walk", "through",
                 "time", "ever", "give", "example"}
    question_keywords -= stopwords

    # Check keyword overlap
    answer_words = set(re.findall(r"\b\w{4,}\b", answer_lower))
    overlap = len(question_keywords & answer_words)
    overlap_pct = overlap / max(len(question_keywords), 1)

    # Check targeting keywords
    targeting_match = 0
    for target in question.targeting:
        if target.lower() in answer_lower:
            targeting_match += 1

    # Score
    if overlap_pct >= 0.4 and targeting_match >= 1:
        score = 23
        feedback = "Directly addresses the question with relevant experience."
    elif overlap_pct >= 0.3:
        score = 18
        feedback = "Good relevance but could connect more directly to what was asked."
    elif overlap_pct >= 0.2:
        score = 12
        feedback = "Partially relevant. Focus more on the specific topic asked about."
    else:
        score = 6
        feedback = "Answer doesn't clearly address the question. Re-read what was asked."

    return min(25, score), feedback


def _score_impact(answer: str) -> tuple[int, str]:
    """Score demonstrated outcomes and impact (0-15)."""
    metric_count = sum(
        1 for p in _METRIC_PATTERNS if re.search(p, answer, re.IGNORECASE)
    )

    # Impact language
    impact_phrases = re.findall(
        r"\b(result(ed)?|outcome|impact|saved|reduced|increased|improved|grew|delivered|shipped|launched|achieved)\b",
        answer.lower(),
    )

    score = 3  # base
    if metric_count >= 3:
        score += 8
        feedback = "Strong impact with multiple quantified outcomes."
    elif metric_count >= 1:
        score += 5
        feedback = "Some metrics shown. Add more quantified results."
    elif len(impact_phrases) >= 2:
        score += 3
        feedback = "Impact language present but needs numbers. Quantify your results."
    else:
        feedback = "No clear impact shown. Always end with measurable outcomes."

    if len(impact_phrases) >= 3:
        score += 2

    return min(15, score), feedback


def _score_communication(answer: str) -> tuple[int, str]:
    """Score clarity and communication quality (0-10)."""
    word_count = len(answer.split())
    filler_count = sum(
        len(re.findall(p, answer.lower())) for p in _FILLER_WORDS
    )
    sentence_count = len(re.split(r"[.!?]+", answer.strip()))

    score = 5  # base

    # Length check (ideal: 150-400 words for a 1-2 min answer)
    if 150 <= word_count <= 400:
        score += 2
        length_note = "Good length."
    elif word_count < 80:
        score -= 2
        length_note = "Too short — elaborate more."
    elif word_count > 500:
        score -= 1
        length_note = "A bit long — tighten for clarity."
    else:
        score += 1
        length_note = "Acceptable length."

    # Filler words
    filler_rate = filler_count / max(word_count, 1)
    if filler_rate > 0.03:
        score -= 2
        filler_note = f"Reduce filler words ({filler_count} detected)."
    elif filler_count > 0:
        filler_note = f"Minor filler words ({filler_count})."
    else:
        score += 1
        filler_note = "Clean delivery, no filler words."

    # Sentence variety (not all same length)
    if sentence_count >= 4:
        score += 1

    feedback = f"{length_note} {filler_note}"
    return max(0, min(10, score)), feedback.strip()


def _check_red_flags(answer: str, question: InterviewQuestion) -> list[str]:
    """Check for red flags in the answer."""
    triggered: list[str] = []
    answer_lower = answer.lower()

    for flag in question.red_flags:
        # Simple heuristic: check if the flag concept appears
        flag_keywords = set(re.findall(r"\b\w{4,}\b", flag.lower()))
        answer_keywords = set(re.findall(r"\b\w{4,}\b", answer_lower))
        overlap = len(flag_keywords & answer_keywords)
        if overlap >= 2:
            triggered.append(flag)

    # Generic red flags
    if len(answer.split()) < 30:
        triggered.append("Answer is too short to demonstrate depth")

    if "we" in answer_lower and answer_lower.count(" we ") > answer_lower.count(" i ") * 2:
        triggered.append("Overuse of 'we' — clarify your individual contribution")

    return triggered


# ── Main grader ────────────────────────────────────────────────────────────


async def grade_answer(
    question: InterviewQuestion,
    answer_text: str,
) -> AnswerGrade:
    """
    Grade a candidate's answer to an interview question.
    Uses Claude when available; falls back to heuristic scoring.
    """
    try:
        return await _grade_with_claude(question, answer_text)
    except Exception:
        return _grade_heuristic(question, answer_text)


async def _grade_with_claude(
    question: InterviewQuestion,
    answer_text: str,
) -> AnswerGrade:
    """Grade an answer using Claude — nuanced, role-aware feedback."""
    from backend.agents.llm import ask_json

    system = """You are a senior engineering interviewer evaluating a candidate's answer.
Be rigorous and specific. Generic praise is useless — give actionable feedback.
Score honestly: 80+ means genuinely impressive, 60–79 is solid, below 60 needs real work.

Dimensions and max scores (must sum to overall_score):
- Structure (STAR): 0–25  (Situation, Task, Action, Result format)
- Specificity: 0–25       (Named projects, tools, real examples, not vague)
- Relevance: 0–25         (Actually answers the question, on-topic)
- Impact: 0–15            (Measurable outcomes, business impact)
- Communication: 0–10     (Clarity, conciseness, no filler)"""

    user = f"""Grade this interview answer.

QUESTION: {question.text}
CATEGORY: {question.category}
WHAT EXCELLENT LOOKS LIKE: {question.what_good_looks_like}

CANDIDATE'S ANSWER:
{answer_text}

Return JSON (overall_score must equal sum of dimension scores):
{{
  "dimensions": [
    {{"name": "Structure (STAR)", "score": <0-25>, "max_score": 25, "feedback": "<specific, actionable>"}},
    {{"name": "Specificity", "score": <0-25>, "max_score": 25, "feedback": "<specific, actionable>"}},
    {{"name": "Relevance", "score": <0-25>, "max_score": 25, "feedback": "<specific, actionable>"}},
    {{"name": "Impact", "score": <0-15>, "max_score": 15, "feedback": "<specific, actionable>"}},
    {{"name": "Communication", "score": <0-10>, "max_score": 10, "feedback": "<specific, actionable>"}}
  ],
  "overall_score": <exact sum of scores above>,
  "strengths": ["<specific strength from the answer>", "<another strength>"],
  "improvements": ["<actionable improvement with example>", "<another improvement>"],
  "model_answer": "<brief outline of what an A+ answer would include for this question>",
  "red_flags": ["<red flag if any, or empty list>"]
}}"""

    data = await ask_json(system, user, model="claude-haiku-4-5-20251001", max_tokens=1400)

    dims = [
        DimensionGrade(
            name=d["name"],
            score=max(0, min(d["max_score"], int(d["score"]))),
            max_score=d["max_score"],
            feedback=d["feedback"],
        )
        for d in data["dimensions"]
    ]

    # Recompute overall from parsed dimension scores for consistency
    overall = sum(d.score for d in dims)

    return AnswerGrade(
        question_id=question.id,
        overall_score=overall,
        max_score=100,
        dimensions=dims,
        strengths=data.get("strengths") or ["Keep practicing!"],
        improvements=data.get("improvements") or ["Good effort — keep building!"],
        model_answer=data.get("model_answer") or question.what_good_looks_like,
        red_flags_triggered=data.get("red_flags") or [],
    )


def _grade_heuristic(
    question: InterviewQuestion,
    answer_text: str,
) -> AnswerGrade:
    """Heuristic-based grading fallback (no LLM required)."""
    # Score each dimension
    struct_score, struct_fb = _score_structure(answer_text)
    spec_score, spec_fb = _score_specificity(answer_text)
    rel_score, rel_fb = _score_relevance(answer_text, question)
    impact_score, impact_fb = _score_impact(answer_text)
    comm_score, comm_fb = _score_communication(answer_text)

    dimensions = [
        DimensionGrade("Structure (STAR)", struct_score, 25, struct_fb),
        DimensionGrade("Specificity", spec_score, 25, spec_fb),
        DimensionGrade("Relevance", rel_score, 25, rel_fb),
        DimensionGrade("Impact", impact_score, 15, impact_fb),
        DimensionGrade("Communication", comm_score, 10, comm_fb),
    ]

    overall = sum(d.score for d in dimensions)

    dim_ratios = [(d.score / d.max_score, d) for d in dimensions]
    dim_ratios.sort(key=lambda x: x[0], reverse=True)
    strengths = [d.feedback for ratio, d in dim_ratios[:2] if ratio >= 0.6]

    dim_ratios.sort(key=lambda x: x[0])
    improvements = [d.feedback for ratio, d in dim_ratios[:2] if ratio < 0.8]

    red_flags = _check_red_flags(answer_text, question)

    return AnswerGrade(
        question_id=question.id,
        overall_score=overall,
        max_score=100,
        dimensions=dimensions,
        strengths=strengths if strengths else ["Keep practicing!"],
        improvements=improvements if improvements else ["Strong answer — keep it up!"],
        model_answer=question.what_good_looks_like,
        red_flags_triggered=red_flags,
    )
