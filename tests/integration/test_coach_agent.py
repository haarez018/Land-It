"""Integration tests for the full Coach agent pipeline."""

import pytest

from backend.agents.coach.agent import CoachAgent, CoachResult
from backend.agents.coach.question_generator import InterviewQuestion, generate_questions
from backend.agents.coach.answer_grader import grade_answer
from backend.agents.coach.session_tracker import (
    CoachingSession,
    SessionSummary,
    create_session,
    get_session,
)
from backend.parsers.schemas import JobDescription, JDRequirement


def _jd() -> JobDescription:
    return JobDescription(
        title="Senior Backend Engineer",
        company="Stripe",
        seniority_level="senior",
        required_skills=["Python", "Go", "PostgreSQL"],
        preferred_skills=["Kubernetes"],
        tech_stack=["Python", "Go", "PostgreSQL", "Docker", "gRPC"],
        requirements=[
            JDRequirement(
                text="5+ years backend development",
                category="must_have",
                skill_type="technical",
                extracted_keyword="backend development",
            ),
            JDRequirement(
                text="Strong system design skills",
                category="must_have",
                skill_type="technical",
                extracted_keyword="system design",
            ),
            JDRequirement(
                text="Excellent collaboration",
                category="must_have",
                skill_type="soft",
                extracted_keyword="collaboration",
            ),
        ],
        company_values=["Users first", "Move with urgency"],
        role_priorities=["Build reliable payment infrastructure"],
    )


GOOD_ANSWER = (
    "At my previous company in 2022, our payments team of 8 engineers faced a critical "
    "scaling challenge. I was the tech lead responsible for designing the solution. "
    "I proposed migrating from a single PostgreSQL instance to a sharded architecture "
    "using Citus, with a read-replica strategy for analytics workloads. I built the "
    "migration tooling in Go, implemented automated shard rebalancing, and created a "
    "comprehensive runbook. The result was a 60% reduction in p99 latency, from 800ms "
    "to 320ms, and we supported 3x the transaction volume. We saved $200K annually "
    "in infrastructure costs by right-sizing our compute."
)

SHORT_ANSWER = "I used Python to build stuff. It worked."


class TestCoachAgentStartSession:

    @pytest.mark.asyncio
    async def test_start_session_creates_session(self):
        agent = CoachAgent()
        result = await agent.start_session(_jd(), seed=42)
        assert isinstance(result, CoachResult)
        assert isinstance(result.session, CoachingSession)
        assert result.session.status == "active"

    @pytest.mark.asyncio
    async def test_start_session_generates_questions(self):
        agent = CoachAgent()
        result = await agent.start_session(_jd(), question_count=8, seed=42)
        assert len(result.session.questions) == 8
        for q in result.session.questions:
            assert isinstance(q, InterviewQuestion)

    @pytest.mark.asyncio
    async def test_session_starts_at_first_question(self):
        agent = CoachAgent()
        result = await agent.start_session(_jd(), seed=42)
        assert result.session.current_question_index == 0
        assert result.session.current_question is not None


class TestCoachAgentSubmitAnswer:

    @pytest.mark.asyncio
    async def test_submit_answer_returns_grade(self):
        agent = CoachAgent()
        result = await agent.start_session(_jd(), question_count=3, seed=42)
        session_id = result.session.id

        grade = await agent.submit_answer(session_id, GOOD_ANSWER, duration=90.0)
        assert grade is not None
        assert grade.overall_score > 0
        assert len(grade.dimensions) == 5

    @pytest.mark.asyncio
    async def test_submit_answer_advances_question(self):
        agent = CoachAgent()
        result = await agent.start_session(_jd(), question_count=3, seed=42)
        session_id = result.session.id

        assert result.session.current_question_index == 0
        await agent.submit_answer(session_id, GOOD_ANSWER)
        session = get_session(session_id)
        assert session.current_question_index == 1

    @pytest.mark.asyncio
    async def test_good_answer_scores_higher_than_bad(self):
        agent = CoachAgent()
        result = await agent.start_session(_jd(), question_count=3, seed=42)
        sid = result.session.id

        good_grade = await agent.submit_answer(sid, GOOD_ANSWER)

        # Start fresh session for fair comparison
        result2 = await agent.start_session(_jd(), question_count=3, seed=42)
        sid2 = result2.session.id
        bad_grade = await agent.submit_answer(sid2, SHORT_ANSWER)

        assert good_grade.overall_score > bad_grade.overall_score

    @pytest.mark.asyncio
    async def test_submit_to_nonexistent_session_returns_none(self):
        agent = CoachAgent()
        grade = await agent.submit_answer("nonexistent_id", GOOD_ANSWER)
        assert grade is None


class TestCoachAgentSkip:

    @pytest.mark.asyncio
    async def test_skip_advances_question(self):
        agent = CoachAgent()
        result = await agent.start_session(_jd(), question_count=3, seed=42)
        sid = result.session.id

        session = await agent.skip_question(sid)
        assert session.current_question_index == 1

    @pytest.mark.asyncio
    async def test_skip_marks_as_skipped(self):
        agent = CoachAgent()
        result = await agent.start_session(_jd(), question_count=3, seed=42)
        sid = result.session.id

        await agent.skip_question(sid)
        session = get_session(sid)
        assert session.results[0].skipped is True


class TestCoachAgentSummary:

    @pytest.mark.asyncio
    async def test_summary_after_answers(self):
        agent = CoachAgent()
        result = await agent.start_session(_jd(), question_count=3, seed=42)
        sid = result.session.id

        # Answer all 3 questions
        for _ in range(3):
            await agent.submit_answer(sid, GOOD_ANSWER, duration=60.0)

        summary = await agent.get_summary(sid)
        assert isinstance(summary, SessionSummary)
        assert summary.questions_answered == 3
        assert summary.questions_skipped == 0
        assert summary.total_score > 0
        assert summary.grade_letter in ("A", "B+", "B", "C+", "C", "D")

    @pytest.mark.asyncio
    async def test_summary_with_mixed_answers_and_skips(self):
        agent = CoachAgent()
        result = await agent.start_session(_jd(), question_count=4, seed=42)
        sid = result.session.id

        await agent.submit_answer(sid, GOOD_ANSWER, duration=90.0)
        await agent.skip_question(sid)
        await agent.submit_answer(sid, SHORT_ANSWER, duration=10.0)
        await agent.skip_question(sid)

        summary = await agent.get_summary(sid)
        assert summary.questions_answered == 2
        assert summary.questions_skipped == 2
        assert summary.total_questions == 4

    @pytest.mark.asyncio
    async def test_session_completes_when_all_answered(self):
        agent = CoachAgent()
        result = await agent.start_session(_jd(), question_count=2, seed=42)
        sid = result.session.id

        await agent.submit_answer(sid, GOOD_ANSWER)
        await agent.submit_answer(sid, GOOD_ANSWER)

        session = get_session(sid)
        assert session.status == "completed"
        assert session.is_complete

    @pytest.mark.asyncio
    async def test_summary_has_dimension_analysis(self):
        agent = CoachAgent()
        result = await agent.start_session(_jd(), question_count=2, seed=42)
        sid = result.session.id

        await agent.submit_answer(sid, GOOD_ANSWER)
        await agent.submit_answer(sid, GOOD_ANSWER)

        summary = await agent.get_summary(sid)
        assert summary.strongest_dimension != "N/A"
        assert summary.weakest_dimension != "N/A"
        assert len(summary.all_strengths) >= 1


class TestCoachAgentLangGraph:

    @pytest.mark.asyncio
    async def test_langgraph_start_action(self):
        agent = CoachAgent()
        state = {"jd": _jd(), "action": "start"}
        result = await agent.run(state)

        assert "session_id" in result
        assert "current_question" in result
        assert result["current_question"] is not None

    @pytest.mark.asyncio
    async def test_langgraph_answer_action(self):
        agent = CoachAgent()
        # Start
        state = {"jd": _jd(), "action": "start"}
        state = await agent.run(state)

        # Answer
        state["action"] = "answer"
        state["answer_text"] = GOOD_ANSWER
        state["answer_duration"] = 60.0
        state = await agent.run(state)

        assert "last_grade" in state
        assert state["last_grade"].overall_score > 0

    @pytest.mark.asyncio
    async def test_langgraph_summary_action(self):
        agent = CoachAgent()
        state = {"jd": _jd(), "action": "start"}
        state = await agent.run(state)

        # Answer a question
        state["action"] = "answer"
        state["answer_text"] = GOOD_ANSWER
        state = await agent.run(state)

        # Get summary
        state["action"] = "summary"
        state = await agent.run(state)

        assert "session_summary" in state
        assert state["session_summary"].questions_answered == 1
