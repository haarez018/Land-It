"""
Track interview performance across sessions over time.

Maintains session state, tracks scores per question, computes
aggregates, and identifies improvement trends.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Optional

from backend.agents.coach.question_generator import InterviewQuestion
from backend.agents.coach.answer_grader import AnswerGrade


@dataclass
class QuestionResult:
    """Result for a single question in a session."""
    question: InterviewQuestion
    grade: Optional[AnswerGrade] = None
    answer_text: str = ""
    answer_duration_seconds: float = 0.0
    skipped: bool = False


@dataclass
class SessionSummary:
    """Aggregate summary of a coaching session."""
    session_id: str
    total_score: int
    max_score: int
    score_pct: float
    questions_answered: int
    questions_skipped: int
    total_questions: int
    avg_score_per_question: float
    strongest_dimension: str
    weakest_dimension: str
    all_strengths: list[str]
    all_improvements: list[str]
    red_flags_triggered: list[str]
    duration_seconds: float
    grade_letter: str


@dataclass
class CoachingSession:
    """A single mock interview session."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    jd_id: str = ""
    user_id: str = ""
    questions: list[InterviewQuestion] = field(default_factory=list)
    results: list[QuestionResult] = field(default_factory=list)
    current_question_index: int = 0
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    ended_at: Optional[str] = None
    status: str = "active"  # active | completed | abandoned

    @property
    def is_complete(self) -> bool:
        return self.current_question_index >= len(self.questions)

    @property
    def current_question(self) -> Optional[InterviewQuestion]:
        if self.current_question_index < len(self.questions):
            return self.questions[self.current_question_index]
        return None

    def record_answer(self, grade: AnswerGrade, answer_text: str, duration: float = 0.0) -> None:
        """Record a graded answer and advance to next question."""
        if self.current_question_index >= len(self.questions):
            return

        result = QuestionResult(
            question=self.questions[self.current_question_index],
            grade=grade,
            answer_text=answer_text,
            answer_duration_seconds=duration,
        )
        self.results.append(result)
        self.current_question_index += 1

        if self.is_complete:
            self.status = "completed"
            self.ended_at = datetime.now(UTC).isoformat()

    def skip_question(self) -> None:
        """Skip the current question."""
        if self.current_question_index >= len(self.questions):
            return

        result = QuestionResult(
            question=self.questions[self.current_question_index],
            skipped=True,
        )
        self.results.append(result)
        self.current_question_index += 1

        if self.is_complete:
            self.status = "completed"
            self.ended_at = datetime.now(UTC).isoformat()

    def summarize(self) -> SessionSummary:
        """Compute session summary statistics."""
        graded = [r for r in self.results if r.grade is not None]
        skipped = [r for r in self.results if r.skipped]

        total_score = sum(r.grade.overall_score for r in graded)
        max_score = sum(r.grade.max_score for r in graded) if graded else 100

        # Aggregate dimension scores
        dim_totals: dict[str, tuple[int, int]] = {}  # name -> (score, max)
        for r in graded:
            for d in r.grade.dimensions:
                prev = dim_totals.get(d.name, (0, 0))
                dim_totals[d.name] = (prev[0] + d.score, prev[1] + d.max_score)

        # Find strongest/weakest
        dim_pcts = {
            name: score / max_s if max_s > 0 else 0
            for name, (score, max_s) in dim_totals.items()
        }
        strongest = max(dim_pcts, key=dim_pcts.get, default="N/A")  # type: ignore[arg-type]
        weakest = min(dim_pcts, key=dim_pcts.get, default="N/A")  # type: ignore[arg-type]

        # Collect all feedback
        all_strengths: list[str] = []
        all_improvements: list[str] = []
        all_red_flags: list[str] = []
        for r in graded:
            all_strengths.extend(r.grade.strengths)
            all_improvements.extend(r.grade.improvements)
            all_red_flags.extend(r.grade.red_flags_triggered)

        # Deduplicate
        all_strengths = list(dict.fromkeys(all_strengths))
        all_improvements = list(dict.fromkeys(all_improvements))
        all_red_flags = list(dict.fromkeys(all_red_flags))

        # Duration
        total_duration = sum(r.answer_duration_seconds for r in self.results)

        # Score percentage
        score_pct = (total_score / max_score * 100) if max_score > 0 else 0

        # Grade letter
        if score_pct >= 90:
            grade_letter = "A"
        elif score_pct >= 80:
            grade_letter = "B+"
        elif score_pct >= 70:
            grade_letter = "B"
        elif score_pct >= 60:
            grade_letter = "C+"
        elif score_pct >= 50:
            grade_letter = "C"
        else:
            grade_letter = "D"

        return SessionSummary(
            session_id=self.id,
            total_score=total_score,
            max_score=max_score,
            score_pct=round(score_pct, 1),
            questions_answered=len(graded),
            questions_skipped=len(skipped),
            total_questions=len(self.questions),
            avg_score_per_question=round(total_score / len(graded), 1) if graded else 0,
            strongest_dimension=strongest,
            weakest_dimension=weakest,
            all_strengths=all_strengths[:5],
            all_improvements=all_improvements[:5],
            red_flags_triggered=all_red_flags[:5],
            duration_seconds=total_duration,
            grade_letter=grade_letter,
        )


# ── Session store (in-memory for now) ──────────────────────────────────────

_session_store: dict[str, CoachingSession] = {}


def create_session(
    jd_id: str,
    questions: list[InterviewQuestion],
    user_id: str = "",
) -> CoachingSession:
    """Create a new coaching session."""
    session = CoachingSession(
        jd_id=jd_id,
        user_id=user_id,
        questions=questions,
    )
    _session_store[session.id] = session
    return session


def get_session(session_id: str) -> Optional[CoachingSession]:
    """Retrieve a session by ID."""
    return _session_store.get(session_id)


def list_sessions(user_id: str = "") -> list[CoachingSession]:
    """List all sessions, optionally filtered by user."""
    sessions = list(_session_store.values())
    if user_id:
        sessions = [s for s in sessions if s.user_id == user_id]
    return sorted(sessions, key=lambda s: s.started_at, reverse=True)
