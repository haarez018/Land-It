"""
CoachAgent: runs voice-first mock interview sessions with graded feedback.

Pipeline: generate questions → present question → grade answer → track session
Falls back to heuristic grading when no LLM is available.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from backend.parsers.schemas import JobDescription, Resume
from backend.agents.coach.question_generator import (
    InterviewQuestion,
    generate_questions,
)
from backend.agents.coach.answer_grader import AnswerGrade, grade_answer
from backend.agents.coach.session_tracker import (
    CoachingSession,
    SessionSummary,
    create_session,
    get_session,
)


@dataclass
class CoachResult:
    """Result from the coach pipeline."""
    session: CoachingSession
    summary: Optional[SessionSummary] = None


class CoachAgent:
    """Manages mock interview coaching sessions."""

    async def run(self, state: dict) -> dict:
        """
        LangGraph-compatible run method.

        Expected state keys:
            - jd: JobDescription object
            - resume: Resume object (optional)
            - action: str — "start" | "answer" | "skip" | "summary"
            - session_id: str (for answer/skip/summary)
            - answer_text: str (for answer action)
            - answer_duration: float (for answer action, seconds)

        Returns updated state with:
            - coach_result: CoachResult
            - session_id: str
            - current_question: InterviewQuestion | None
        """
        action = state.get("action", "start")

        if action == "start":
            result = await self.start_session(
                jd=state["jd"],
                resume=state.get("resume"),
            )
            return {
                **state,
                "coach_result": result,
                "session_id": result.session.id,
                "current_question": result.session.current_question,
            }

        elif action == "answer":
            session_id = state["session_id"]
            answer_text = state.get("answer_text", "")
            duration = state.get("answer_duration", 0.0)

            grade = await self.submit_answer(session_id, answer_text, duration)
            session = get_session(session_id)

            return {
                **state,
                "coach_result": CoachResult(session=session) if session else None,
                "last_grade": grade,
                "current_question": session.current_question if session else None,
            }

        elif action == "skip":
            session_id = state["session_id"]
            session = await self.skip_question(session_id)

            return {
                **state,
                "coach_result": CoachResult(session=session) if session else None,
                "current_question": session.current_question if session else None,
            }

        elif action == "summary":
            session_id = state["session_id"]
            summary = await self.get_summary(session_id)

            return {
                **state,
                "coach_result": CoachResult(
                    session=get_session(session_id),  # type: ignore
                    summary=summary,
                ),
                "session_summary": summary,
            }

        return state

    async def start_session(
        self,
        jd: JobDescription,
        resume: Optional[Resume] = None,
        *,
        question_count: int = 10,
        seed: Optional[int] = None,
    ) -> CoachResult:
        """
        Start a new coaching session.

        Args:
            jd: Target job description for question generation
            resume: Optional candidate resume for personalization
            question_count: Number of questions (default 10)
            seed: Random seed for reproducible question sets

        Returns:
            CoachResult with the new session
        """
        questions = await generate_questions(
            jd, resume, count=question_count, seed=seed
        )
        session = create_session(jd_id=jd.id, questions=questions)
        return CoachResult(session=session)

    async def submit_answer(
        self,
        session_id: str,
        answer_text: str,
        duration: float = 0.0,
    ) -> Optional[AnswerGrade]:
        """
        Submit and grade an answer to the current question.

        Args:
            session_id: Active session ID
            answer_text: The candidate's transcribed/typed answer
            duration: How long the answer took (seconds)

        Returns:
            AnswerGrade for the submitted answer, or None if session not found
        """
        session = get_session(session_id)
        if not session or session.is_complete:
            return None

        question = session.current_question
        if not question:
            return None

        grade = await grade_answer(question, answer_text)
        session.record_answer(grade, answer_text, duration)

        return grade

    async def skip_question(self, session_id: str) -> Optional[CoachingSession]:
        """Skip the current question in a session."""
        session = get_session(session_id)
        if not session or session.is_complete:
            return session

        session.skip_question()
        return session

    async def get_summary(self, session_id: str) -> Optional[SessionSummary]:
        """Get the summary for a session."""
        session = get_session(session_id)
        if not session:
            return None
        return session.summarize()

    async def get_question(self, session_id: str) -> Optional[InterviewQuestion]:
        """Get the current question for a session."""
        session = get_session(session_id)
        if not session:
            return None
        return session.current_question
