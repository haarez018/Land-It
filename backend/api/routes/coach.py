"""Interview coaching session endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.parsers.jd_parser import parse_jd
from backend.agents.coach.agent import CoachAgent
from backend.agents.coach.session_tracker import get_session, list_sessions

router = APIRouter()

_agent = CoachAgent()


# ── Request / Response models ──────────────────────────────────────────────


class StartSessionRequest(BaseModel):
    jd_text: str
    question_count: int = 10


class SubmitAnswerRequest(BaseModel):
    answer_text: str
    duration_seconds: float = 0.0


class QuestionResponse(BaseModel):
    id: str
    text: str
    category: str
    difficulty: str
    question_number: int
    total_questions: int


class DimensionGradeResponse(BaseModel):
    name: str
    score: int
    max_score: int
    feedback: str


class GradeResponse(BaseModel):
    question_id: str
    overall_score: int
    max_score: int
    dimensions: list[DimensionGradeResponse]
    strengths: list[str]
    improvements: list[str]
    model_answer: str
    red_flags_triggered: list[str]


class SessionInfoResponse(BaseModel):
    session_id: str
    status: str
    current_question_index: int
    total_questions: int
    started_at: str


class SessionSummaryResponse(BaseModel):
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


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.post("/session/start", response_model=SessionInfoResponse)
async def start_session(request: StartSessionRequest):
    """Start a new mock interview session with JD-specific questions."""
    jd = parse_jd(request.jd_text)
    result = await _agent.start_session(
        jd, question_count=request.question_count
    )
    session = result.session

    return SessionInfoResponse(
        session_id=session.id,
        status=session.status,
        current_question_index=session.current_question_index,
        total_questions=len(session.questions),
        started_at=session.started_at,
    )


@router.get("/session/{session_id}/questions")
async def get_questions(session_id: str):
    """Get all questions for a session."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    return [
        QuestionResponse(
            id=q.id,
            text=q.text,
            category=q.category,
            difficulty=q.difficulty,
            question_number=i + 1,
            total_questions=len(session.questions),
        )
        for i, q in enumerate(session.questions)
    ]


@router.get("/session/{session_id}/current", response_model=Optional[QuestionResponse])
async def get_current_question(session_id: str):
    """Get the current question for a session."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    q = session.current_question
    if not q:
        return None

    return QuestionResponse(
        id=q.id,
        text=q.text,
        category=q.category,
        difficulty=q.difficulty,
        question_number=session.current_question_index + 1,
        total_questions=len(session.questions),
    )


@router.post("/session/{session_id}/answer", response_model=GradeResponse)
async def submit_answer(session_id: str, request: SubmitAnswerRequest):
    """Submit an answer to the current question and receive a grade."""
    grade = await _agent.submit_answer(
        session_id,
        request.answer_text,
        request.duration_seconds,
    )
    if not grade:
        raise HTTPException(400, "Session not found or already complete")

    return GradeResponse(
        question_id=grade.question_id,
        overall_score=grade.overall_score,
        max_score=grade.max_score,
        dimensions=[
            DimensionGradeResponse(
                name=d.name,
                score=d.score,
                max_score=d.max_score,
                feedback=d.feedback,
            )
            for d in grade.dimensions
        ],
        strengths=grade.strengths,
        improvements=grade.improvements,
        model_answer=grade.model_answer,
        red_flags_triggered=grade.red_flags_triggered,
    )


@router.post("/session/{session_id}/skip")
async def skip_question(session_id: str):
    """Skip the current question."""
    session = await _agent.skip_question(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    return {
        "status": "skipped",
        "current_question_index": session.current_question_index,
        "is_complete": session.is_complete,
    }


@router.get("/session/{session_id}/summary", response_model=SessionSummaryResponse)
async def session_summary(session_id: str):
    """Get the summary for a completed (or in-progress) session."""
    summary = await _agent.get_summary(session_id)
    if not summary:
        raise HTTPException(404, "Session not found")

    return SessionSummaryResponse(
        session_id=summary.session_id,
        total_score=summary.total_score,
        max_score=summary.max_score,
        score_pct=summary.score_pct,
        questions_answered=summary.questions_answered,
        questions_skipped=summary.questions_skipped,
        total_questions=summary.total_questions,
        avg_score_per_question=summary.avg_score_per_question,
        strongest_dimension=summary.strongest_dimension,
        weakest_dimension=summary.weakest_dimension,
        all_strengths=summary.all_strengths,
        all_improvements=summary.all_improvements,
        red_flags_triggered=summary.red_flags_triggered,
        duration_seconds=summary.duration_seconds,
        grade_letter=summary.grade_letter,
    )


@router.get("/sessions")
async def list_all_sessions():
    """List all coaching sessions."""
    sessions = list_sessions()
    return [
        SessionInfoResponse(
            session_id=s.id,
            status=s.status,
            current_question_index=s.current_question_index,
            total_questions=len(s.questions),
            started_at=s.started_at,
        )
        for s in sessions
    ]
