"""Integration tests for the Planner agent orchestration."""

import pytest

from backend.agents.planner.agent import PlannerAgent, PlannerResult
from backend.agents.planner.strategy import (
    ApplicationEntry,
    WeeklyGoal,
    WeeklyReport,
)
from backend.parsers.schemas import JobDescription


def _app(status="queued", fit=70.0, **kw):
    return ApplicationEntry(
        status=status,
        fit_score=fit,
        jd=JobDescription(title="Engineer", company="TestCo"),
        **kw,
    )


class TestPlannerAgentPlanWeek:

    @pytest.mark.asyncio
    async def test_plan_week_returns_result(self):
        agent = PlannerAgent()
        apps = [_app(status="queued", fit=80), _app(status="submitted", fit=90)]
        goal = WeeklyGoal(target_applications=5)

        result = await agent.plan_week(apps, goal)
        assert isinstance(result, PlannerResult)
        assert isinstance(result.report, WeeklyReport)
        assert len(result.prioritized_apps) >= 1
        assert len(result.agent_tasks) >= 1

    @pytest.mark.asyncio
    async def test_plan_week_prioritizes(self):
        agent = PlannerAgent()
        apps = [
            _app(status="queued", fit=50),
            _app(status="queued", fit=90),
            _app(status="ready", fit=70),
        ]
        result = await agent.plan_week(apps, WeeklyGoal())
        # Highest priority should be ready (1.5 weight) or highest fit
        assert result.prioritized_apps[0].priority == 1


class TestPlannerAgentGenerateReport:

    @pytest.mark.asyncio
    async def test_generate_report(self):
        agent = PlannerAgent()
        apps = [_app(status="submitted"), _app(status="interviewing")]
        result = await agent.generate_report(apps, WeeklyGoal())

        assert result.report.applications_sent == 1
        assert result.report.interviews_scheduled == 1

    @pytest.mark.asyncio
    async def test_empty_pipeline_report(self):
        agent = PlannerAgent()
        result = await agent.generate_report([], WeeklyGoal())
        assert result.report.summary
        assert result.report.applications_sent == 0


class TestPlannerAgentLangGraph:

    @pytest.mark.asyncio
    async def test_run_plan_action(self):
        agent = PlannerAgent()
        state = {
            "action": "plan",
            "applications": [_app(status="queued", fit=80)],
            "goal": WeeklyGoal(target_applications=5),
        }
        result = await agent.run(state)
        assert "planner_result" in result
        assert "weekly_report" in result
        assert result["weekly_report"].summary

    @pytest.mark.asyncio
    async def test_run_report_action(self):
        agent = PlannerAgent()
        state = {
            "action": "report",
            "applications": [_app(status="submitted")],
        }
        result = await agent.run(state)
        assert result["weekly_report"].applications_sent == 1

    @pytest.mark.asyncio
    async def test_run_prioritize_action(self):
        agent = PlannerAgent()
        state = {
            "action": "prioritize",
            "applications": [
                _app(status="queued", fit=60),
                _app(status="ready", fit=90),
            ],
        }
        result = await agent.run(state)
        assert len(result["planner_result"].prioritized_apps) >= 1
        assert len(result["agent_tasks"]) >= 1
