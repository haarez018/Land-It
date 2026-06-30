"""Tests for the weekly strategy module."""

import pytest

from backend.agents.planner.strategy import (
    ApplicationEntry,
    WeeklyGoal,
    WeeklyReport,
    AgentTask,
    prioritize_applications,
    generate_agent_tasks,
    generate_weekly_report,
)
from backend.parsers.schemas import JobDescription


def _app(status: str = "queued", fit: float = 70.0, **kw) -> ApplicationEntry:
    return ApplicationEntry(
        status=status,
        fit_score=fit,
        jd=JobDescription(title="Engineer", company="Co"),
        **kw,
    )


class TestPrioritizeApplications:

    def test_sorts_by_fit_and_status(self):
        apps = [
            _app(status="queued", fit=60),
            _app(status="ready", fit=80),
            _app(status="interviewing", fit=70),
        ]
        result = prioritize_applications(apps)
        # interviewing*2.0=140, ready*1.5=120, queued*1.0=60
        assert result[0].status == "interviewing"
        assert result[1].status == "ready"

    def test_assigns_priority_ranks(self):
        apps = [_app(fit=90), _app(fit=50), _app(fit=70)]
        result = prioritize_applications(apps)
        assert result[0].priority == 1
        assert result[1].priority == 2
        assert result[2].priority == 3

    def test_respects_top_n(self):
        apps = [_app(fit=i * 10) for i in range(20)]
        result = prioritize_applications(apps, top_n=5)
        assert len(result) == 5

    def test_rejected_sorted_last(self):
        apps = [_app(status="rejected", fit=100), _app(status="queued", fit=50)]
        result = prioritize_applications(apps)
        assert result[0].status == "queued"


class TestGenerateAgentTasks:

    def test_generates_tailor_tasks_for_queued(self):
        apps = [_app(status="queued", fit=80)]
        tasks = generate_agent_tasks(apps)
        tailor_tasks = [t for t in tasks if t.agent == "tailor"]
        assert len(tailor_tasks) >= 1

    def test_generates_pitcher_tasks_for_ready(self):
        apps = [_app(status="ready", fit=80)]
        tasks = generate_agent_tasks(apps)
        pitcher_tasks = [t for t in tasks if t.agent == "pitcher"]
        assert len(pitcher_tasks) >= 1

    def test_generates_coach_tasks_for_interviewing(self):
        apps = [_app(status="interviewing", fit=80)]
        tasks = generate_agent_tasks(apps)
        coach_tasks = [t for t in tasks if t.agent == "coach"]
        assert len(coach_tasks) >= 1

    def test_generates_scout_task_when_pipeline_thin(self):
        apps = [_app(status="submitted")]  # Only 1 submitted, none queued/ready
        tasks = generate_agent_tasks(apps)
        scout_tasks = [t for t in tasks if t.agent == "scout"]
        assert len(scout_tasks) >= 1

    def test_no_scout_when_pipeline_full(self):
        apps = [_app(status="queued", fit=70 + i) for i in range(10)]
        tasks = generate_agent_tasks(apps)
        scout_tasks = [t for t in tasks if t.agent == "scout"]
        assert len(scout_tasks) == 0

    def test_tasks_sorted_by_priority(self):
        apps = [
            _app(status="queued", fit=80),
            _app(status="interviewing", fit=90),
        ]
        tasks = generate_agent_tasks(apps)
        for i in range(1, len(tasks)):
            assert tasks[i].priority >= tasks[i - 1].priority


class TestGenerateWeeklyReport:

    def test_generates_report(self):
        apps = [_app(status="submitted", fit=80)]
        report = generate_weekly_report(apps, WeeklyGoal(target_applications=10))
        assert isinstance(report, WeeklyReport)
        assert report.summary
        assert report.week_of

    def test_report_counts_correct(self):
        apps = [
            _app(status="submitted"),
            _app(status="submitted"),
            _app(status="interviewing"),
            _app(status="queued"),
        ]
        report = generate_weekly_report(apps, WeeklyGoal())
        assert report.applications_sent == 2
        assert report.interviews_scheduled == 1

    def test_report_has_action_items(self):
        apps = [_app(status="queued", fit=80)]
        report = generate_weekly_report(apps, WeeklyGoal(target_applications=5))
        assert len(report.action_items) >= 1

    def test_report_has_wins(self):
        apps = [_app(status="submitted"), _app(status="interviewing")]
        report = generate_weekly_report(apps, WeeklyGoal())
        assert len(report.wins) >= 1

    def test_report_with_empty_pipeline(self):
        report = generate_weekly_report([], WeeklyGoal())
        assert report.applications_sent == 0
        assert len(report.action_items) >= 1

    def test_report_includes_ats_avg(self):
        apps = [
            _app(status="submitted", ats_score_after=80.0),
            _app(status="submitted", ats_score_after=90.0),
        ]
        report = generate_weekly_report(apps, WeeklyGoal())
        assert report.avg_ats_score == 85.0

    def test_report_top_opportunities(self):
        apps = [_app(status="queued", fit=90), _app(status="queued", fit=50)]
        report = generate_weekly_report(apps, WeeklyGoal())
        assert len(report.top_opportunities) >= 1
        assert report.top_opportunities[0]["fit_score"] >= report.top_opportunities[-1]["fit_score"]
