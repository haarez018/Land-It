"""Unit tests for the Analytics & Insights engine."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from backend.agents.planner.analytics import (
    compute_analytics,
    JobSearchAnalytics,
    FunnelMetrics,
    DimensionHeatmap,
    TimingAnalysis,
    Predictions,
    _compute_funnel,
    _compute_dimension_heatmap,
    _compute_timing,
    _compute_predictions,
)
from backend.agents.planner.benchmarks import (
    INDUSTRY_BENCHMARKS,
    compare_to_benchmark,
)


# ── Helpers to create mock data ──────────────────────────────────────────────

def _make_app(
    status: str = "submitted",
    fit_score: float = 75.0,
    ats_score_before: float = 60.0,
    ats_score_after: float = 72.0,
    company: str = "Acme",
    title: str = "Backend Engineer",
    created_at: str | None = None,
    applied_at: str | None = None,
    last_activity: str | None = None,
):
    now = datetime.now()
    return {
        "status": status,
        "fit_score": fit_score,
        "ats_score_before": ats_score_before,
        "ats_score_after": ats_score_after,
        "created_at": created_at or (now - timedelta(days=7)).isoformat(),
        "applied_at": applied_at or (now - timedelta(days=5)).isoformat(),
        "last_activity": last_activity or now.isoformat(),
        "jd": {"company": company, "title": title},
    }


def _make_score_entry(
    ats: float = 65.0,
    standout: float = 55.0,
    combined: float = 61.0,
    scored_at: str | None = None,
    dims: list[dict] | None = None,
):
    return {
        "ats_score": ats,
        "standout_score": standout,
        "combined_score": combined,
        "scored_at": scored_at or datetime.now().isoformat(),
        "dimension_scores": dims or [
            {"dimension_id": f"dim_{i}", "raw_score": 50 + i * 3}
            for i in range(22)
        ],
    }


# ── Benchmark tests ──────────────────────────────────────────────────────────


class TestBenchmarks:
    def test_all_benchmarks_positive(self):
        for key, val in INDUSTRY_BENCHMARKS.items():
            assert val > 0, f"{key} = {val}"

    def test_compare_above(self):
        result = compare_to_benchmark(0.15, 0.08)
        assert "above" in result

    def test_compare_below(self):
        result = compare_to_benchmark(0.05, 0.08)
        assert "below" in result

    def test_compare_on_par(self):
        result = compare_to_benchmark(0.08, 0.08)
        assert "on par" in result

    def test_compare_zero_benchmark(self):
        result = compare_to_benchmark(0.10, 0)
        assert "no benchmark" in result


# ── Empty data tests ─────────────────────────────────────────────────────────


class TestEmptyData:
    def test_empty_applications(self):
        analytics = compute_analytics([])
        assert isinstance(analytics, JobSearchAnalytics)
        assert analytics.funnel.jobs_discovered == 0
        assert analytics.funnel.jobs_applied == 0
        assert analytics.score_improvement == 0.0
        assert analytics.is_improving is False
        assert len(analytics.one_sentence_summary) > 0

    def test_empty_score_history(self):
        analytics = compute_analytics([], [])
        assert analytics.score_trends["ats"] == []
        assert analytics.dimension_heatmap.dimension_averages == {}


# ── Funnel tests ─────────────────────────────────────────────────────────────


class TestFunnel:
    def test_10_apps_correct_counts(self):
        apps = [
            _make_app(status="queued"),
            _make_app(status="queued"),
            _make_app(status="tailoring"),
            _make_app(status="ready"),
            _make_app(status="submitted"),
            _make_app(status="submitted"),
            _make_app(status="phone_screen"),
            _make_app(status="interviewing"),
            _make_app(status="rejected"),
            _make_app(status="offer"),
        ]
        funnel = _compute_funnel(apps)
        assert funnel.jobs_discovered == 10
        assert funnel.jobs_applied == 6  # submitted(2) + phone_screen + interviewing + rejected + offer
        assert funnel.responses_received == 4  # phone_screen + interviewing + rejected + offer
        assert funnel.interviews_scheduled == 3  # phone_screen + interviewing + offer
        assert funnel.offers_received == 1
        assert funnel.rejections == 1

    def test_conversion_rates_correct(self):
        apps = [
            _make_app(status="submitted"),
            _make_app(status="submitted"),
            _make_app(status="submitted"),
            _make_app(status="submitted"),
            _make_app(status="interviewing"),
        ]
        funnel = _compute_funnel(apps)
        assert funnel.jobs_applied == 5
        assert funnel.responses_received == 1
        assert funnel.conversion_rates["applied_to_response"] == 0.2

    def test_benchmark_comparisons_populated(self):
        apps = [_make_app(status="submitted"), _make_app(status="interviewing")]
        funnel = _compute_funnel(apps)
        assert "applied_to_response" in funnel.benchmark_comparisons


# ── Score trends tests ────────────────────────────────────────────────────────


class TestScoreTrends:
    def test_improving_trend(self):
        now = datetime.now()
        history = [
            _make_score_entry(combined=50.0, scored_at=(now - timedelta(weeks=4)).isoformat()),
            _make_score_entry(combined=55.0, scored_at=(now - timedelta(weeks=3)).isoformat()),
            _make_score_entry(combined=60.0, scored_at=(now - timedelta(weeks=2)).isoformat()),
            _make_score_entry(combined=70.0, scored_at=(now - timedelta(weeks=1)).isoformat()),
        ]
        analytics = compute_analytics([], history)
        assert analytics.is_improving is True
        assert analytics.score_improvement > 0

    def test_flat_trend(self):
        now = datetime.now()
        history = [
            _make_score_entry(combined=60.0, scored_at=now.isoformat()),
        ]
        analytics = compute_analytics([], history)
        assert analytics.is_improving is False
        assert analytics.score_improvement == 0.0


# ── Dimension heatmap tests ──────────────────────────────────────────────────


class TestDimensionHeatmap:
    def test_averages_computed_correctly(self):
        history = [
            _make_score_entry(dims=[
                {"dimension_id": "keyword_density", "raw_score": 80},
                {"dimension_id": "skill_depth", "raw_score": 40},
            ]),
            _make_score_entry(dims=[
                {"dimension_id": "keyword_density", "raw_score": 60},
                {"dimension_id": "skill_depth", "raw_score": 50},
            ]),
        ]
        heatmap = _compute_dimension_heatmap(history)
        assert heatmap.dimension_averages["keyword_density"] == 70.0
        assert heatmap.dimension_averages["skill_depth"] == 45.0

    def test_strongest_and_weakest(self):
        history = [
            _make_score_entry(dims=[
                {"dimension_id": "dim_high", "raw_score": 95},
                {"dimension_id": "dim_mid", "raw_score": 60},
                {"dimension_id": "dim_low", "raw_score": 20},
            ]),
        ]
        heatmap = _compute_dimension_heatmap(history)
        assert "dim_high" in heatmap.strongest_dimensions
        assert "dim_low" in heatmap.weakest_dimensions

    def test_consistency_stdev(self):
        history = [
            _make_score_entry(dims=[{"dimension_id": "test", "raw_score": 50}]),
            _make_score_entry(dims=[{"dimension_id": "test", "raw_score": 50}]),
        ]
        heatmap = _compute_dimension_heatmap(history)
        assert heatmap.dimension_consistency["test"] == 0.0  # No variance

    def test_empty_history(self):
        heatmap = _compute_dimension_heatmap([])
        assert heatmap.dimension_averages == {}
        assert heatmap.strongest_dimensions == []


# ── Timing tests ─────────────────────────────────────────────────────────────


class TestTiming:
    def test_known_dates(self):
        now = datetime.now()
        apps = [
            _make_app(
                status="interviewing",
                created_at=(now - timedelta(days=14)).isoformat(),
                applied_at=(now - timedelta(days=10)).isoformat(),
                last_activity=now.isoformat(),
            ),
        ]
        timing = _compute_timing(apps)
        assert timing.avg_days_to_interview == 10.0  # 10 days from applied to last_activity

    def test_no_apps(self):
        timing = _compute_timing([])
        assert timing.avg_days_to_first_response == 0.0
        assert timing.most_active_day_of_week == "Monday"  # default

    def test_apps_per_week(self):
        now = datetime.now()
        apps = [
            _make_app(applied_at=(now - timedelta(days=i)).isoformat())
            for i in range(14)  # 14 apps over 2 weeks
        ]
        timing = _compute_timing(apps)
        assert len(timing.applications_per_week) >= 1


# ── Predictions tests ────────────────────────────────────────────────────────


class TestPredictions:
    def test_reasonable_weeks_to_offer(self):
        funnel = FunnelMetrics(
            jobs_discovered=50, jobs_queued=40, jobs_applied=20,
            responses_received=4, interviews_scheduled=2, offers_received=0,
            rejections=2,
            conversion_rates={
                "discovered_to_applied": 0.4,
                "applied_to_response": 0.2,
                "response_to_interview": 0.5,
                "interview_to_offer": 0.25,
            },
            benchmark_comparisons={},
        )
        now = datetime.now()
        timing = TimingAnalysis(
            avg_days_to_first_response=14,
            avg_days_to_interview=21,
            avg_days_applied_to_offer=0,
            most_active_day_of_week="Tuesday",
            most_active_hour=10,
            applications_per_week=[
                type("W", (), {"week": f"W{i}", "count": 5, "avg_score": 0})()
                for i in range(4)
            ],
        )
        predictions = _compute_predictions(funnel, timing)
        assert predictions.estimated_weeks_to_offer > 0
        assert predictions.estimated_weeks_to_offer <= 52
        assert predictions.recommended_weekly_volume >= 1

    def test_no_data_zero_weeks(self):
        funnel = FunnelMetrics(
            jobs_discovered=0, jobs_queued=0, jobs_applied=0,
            responses_received=0, interviews_scheduled=0, offers_received=0,
            rejections=0,
            conversion_rates={"discovered_to_applied": 0, "applied_to_response": 0,
                              "response_to_interview": 0, "interview_to_offer": 0},
            benchmark_comparisons={},
        )
        timing = TimingAnalysis(
            avg_days_to_first_response=0, avg_days_to_interview=0,
            avg_days_applied_to_offer=0, most_active_day_of_week="Monday",
            most_active_hour=10, applications_per_week=[],
        )
        predictions = _compute_predictions(funnel, timing)
        assert predictions.estimated_weeks_to_offer == 0.0  # insufficient data

    def test_trajectory_needs_volume(self):
        funnel = FunnelMetrics(
            jobs_discovered=3, jobs_queued=3, jobs_applied=2,
            responses_received=0, interviews_scheduled=0, offers_received=0,
            rejections=0,
            conversion_rates={"discovered_to_applied": 0.67, "applied_to_response": 0,
                              "response_to_interview": 0, "interview_to_offer": 0},
            benchmark_comparisons={},
        )
        timing = TimingAnalysis(
            avg_days_to_first_response=0, avg_days_to_interview=0,
            avg_days_applied_to_offer=0, most_active_day_of_week="Monday",
            most_active_hour=10,
            applications_per_week=[type("W", (), {"week": "W1", "count": 2, "avg_score": 0})()],
        )
        predictions = _compute_predictions(funnel, timing)
        assert predictions.current_trajectory in ("needs_more_volume", "needs_better_targeting")


# ── Full analytics tests ─────────────────────────────────────────────────────


class TestFullAnalytics:
    def test_full_analytics_shape(self):
        apps = [
            _make_app(status="submitted", company="Google"),
            _make_app(status="interviewing", company="Stripe"),
            _make_app(status="rejected", company="Acme"),
            _make_app(status="offer", company="Netflix"),
        ]
        analytics = compute_analytics(apps)
        assert isinstance(analytics, JobSearchAnalytics)
        assert analytics.funnel.jobs_discovered == 4
        assert analytics.funnel.offers_received == 1
        assert len(analytics.this_week_wins) >= 1
        assert len(analytics.one_sentence_summary) > 20

    def test_wins_populated(self):
        apps = [
            _make_app(status="offer", company="Google"),
            _make_app(status="interviewing", company="Stripe"),
        ]
        analytics = compute_analytics(apps)
        assert any("Google" in w for w in analytics.this_week_wins)
        assert any("Stripe" in w for w in analytics.this_week_wins)

    def test_focus_areas_from_weak_dims(self):
        history = [
            _make_score_entry(dims=[
                {"dimension_id": "keyword_density", "raw_score": 30},
                {"dimension_id": "skill_depth", "raw_score": 40},
                {"dimension_id": "tech_stack_alignment", "raw_score": 90},
            ]),
        ]
        analytics = compute_analytics([], history)
        # Weakest should appear in focus areas
        assert len(analytics.focus_areas) >= 1
