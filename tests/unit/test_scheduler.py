"""Tests for the weekly scheduler cron parser and job runner."""

from datetime import datetime

import pytest

from backend.tasks.scheduler import cron_matches, _parse_cron_field, run_weekly_planner


class TestCronParser:
    """Test the minimal cron expression parser."""

    def test_star_matches_all(self):
        result = _parse_cron_field("*", 0, 59)
        assert len(result) == 60
        assert 0 in result
        assert 59 in result

    def test_single_value(self):
        result = _parse_cron_field("5", 0, 59)
        assert result == {5}

    def test_range(self):
        result = _parse_cron_field("1-5", 0, 59)
        assert result == {1, 2, 3, 4, 5}

    def test_step(self):
        result = _parse_cron_field("*/15", 0, 59)
        assert result == {0, 15, 30, 45}

    def test_step_from_base(self):
        result = _parse_cron_field("5/10", 0, 59)
        assert result == {5, 15, 25, 35, 45, 55}

    def test_comma_list(self):
        result = _parse_cron_field("1,3,5", 0, 59)
        assert result == {1, 3, 5}


class TestCronMatches:
    """Test the full 5-field cron matching."""

    def test_every_minute(self):
        dt = datetime(2026, 5, 27, 14, 30)
        assert cron_matches("* * * * *", dt)

    def test_specific_time(self):
        # Sunday 6 PM — Python weekday: Sunday=6
        dt = datetime(2026, 5, 31, 18, 0)  # 2026-05-31 is a Sunday
        assert cron_matches("0 18 * * 6", dt)

    def test_wrong_minute(self):
        dt = datetime(2026, 5, 31, 18, 5)
        assert not cron_matches("0 18 * * 6", dt)

    def test_wrong_day_of_week(self):
        dt = datetime(2026, 5, 27, 18, 0)  # Wednesday
        assert not cron_matches("0 18 * * 6", dt)

    def test_month_specific(self):
        dt = datetime(2026, 1, 15, 12, 0)
        assert cron_matches("0 12 15 1 *", dt)
        assert not cron_matches("0 12 15 2 *", dt)

    def test_invalid_fields_raises(self):
        with pytest.raises(ValueError, match="5-field"):
            cron_matches("* * *", datetime.now())


class TestRunWeeklyPlanner:

    @pytest.mark.asyncio
    async def test_runs_successfully(self):
        """The weekly planner job should run without errors on empty state."""
        result = await run_weekly_planner()
        assert "prioritized" in result
        assert "tasks" in result
        assert "report_id" in result

    @pytest.mark.asyncio
    async def test_returns_report_id(self):
        result = await run_weekly_planner()
        assert result["report_id"]  # Non-empty string
