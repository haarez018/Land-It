"""
PlannerAgent: orchestrates weekly strategy and delegates to specialized agents.

Pipeline: gather state → prioritize → generate tasks → produce report
Works entirely with heuristic logic — no LLM required.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from backend.parsers.schemas import Resume, JobDescription
from backend.agents.planner.strategy import (
    ApplicationEntry,
    WeeklyGoal,
    WeeklyReport,
    AgentTask,
    prioritize_applications,
    generate_agent_tasks,
    generate_weekly_report,
    generate_weekly_report_ai,
    list_applications,
    get_goal,
    store_report,
)


@dataclass
class PlannerResult:
    """Result from the planner pipeline."""
    report: WeeklyReport
    prioritized_apps: list[ApplicationEntry]
    agent_tasks: list[AgentTask]


class PlannerAgent:
    """Orchestrates weekly strategy and delegates to specialized agents."""

    async def run(self, state: dict) -> dict:
        """
        LangGraph-compatible run method.

        Expected state keys:
            - resume: Resume object
            - action: str — "plan" | "report" | "prioritize"
            - applications: list[ApplicationEntry] (optional, pulled from store if absent)
            - goal: WeeklyGoal (optional, pulled from store if absent)

        Returns updated state with:
            - planner_result: PlannerResult
            - weekly_report: WeeklyReport
            - agent_tasks: list[AgentTask]
        """
        resume: Resume = state.get("resume")
        action = state.get("action", "plan")

        applications = state.get("applications") or list_applications()
        goal = state.get("goal") or get_goal()

        if action == "plan":
            result = await self.plan_week(applications, goal, resume)
        elif action == "report":
            result = await self.generate_report(applications, goal, resume)
        elif action == "prioritize":
            prioritized = prioritize_applications(applications)
            tasks = generate_agent_tasks(applications)
            report = WeeklyReport(summary="Prioritization only — no full report generated.")
            result = PlannerResult(
                report=report,
                prioritized_apps=prioritized,
                agent_tasks=tasks,
            )
        else:
            report = WeeklyReport(summary=f"Unknown action: {action}")
            result = PlannerResult(report=report, prioritized_apps=[], agent_tasks=[])

        return {
            **state,
            "planner_result": result,
            "weekly_report": result.report,
            "agent_tasks": result.agent_tasks,
        }

    async def plan_week(
        self,
        applications: list[ApplicationEntry],
        goal: Optional[WeeklyGoal] = None,
        resume: Optional[Resume] = None,
    ) -> PlannerResult:
        """
        Full weekly planning pipeline.

        Args:
            applications: All current applications
            goal: User's weekly goal
            resume: Candidate resume

        Returns:
            PlannerResult with report, priorities, and tasks
        """
        goal = goal or WeeklyGoal()

        # 1. Prioritize applications
        prioritized = prioritize_applications(applications)

        # 2. Generate agent tasks
        tasks = generate_agent_tasks(applications)

        # 3. Generate weekly report (Claude-enhanced, heuristic fallback)
        report = await generate_weekly_report_ai(applications, goal, resume)

        # 4. Store the report
        store_report(report)

        return PlannerResult(
            report=report,
            prioritized_apps=prioritized,
            agent_tasks=tasks,
        )

    async def generate_report(
        self,
        applications: list[ApplicationEntry],
        goal: Optional[WeeklyGoal] = None,
        resume: Optional[Resume] = None,
    ) -> PlannerResult:
        """Generate just the weekly report (no task scheduling)."""
        goal = goal or WeeklyGoal()
        report = await generate_weekly_report_ai(applications, goal, resume)
        store_report(report)

        return PlannerResult(
            report=report,
            prioritized_apps=[],
            agent_tasks=report.agent_tasks,
        )
