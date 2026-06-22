"""
Lightweight weekly scheduler for the Planner agent.

Three execution modes:
  1. FastAPI lifespan — runs an asyncio background task (default, zero deps)
  2. CLI one-shot     — `python -m backend.tasks.scheduler` for cron / Task Scheduler
  3. Celery beat      — when Redis + Celery are configured (future)

The WEEKLY_PLANNER_CRON setting in config.py controls when the job fires.
Default is "0 18 * * 0" (Sunday 6 PM).
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

from backend.config import settings

logger = logging.getLogger(__name__)


# ── Cron parser (minimal, no deps) ──────────────────────────────────────────

def _parse_cron_field(field: str, min_val: int, max_val: int) -> set[int]:
    """Parse a single cron field into a set of matching integers."""
    if field == "*":
        return set(range(min_val, max_val + 1))

    values: set[int] = set()
    for part in field.split(","):
        if "/" in part:
            base, step = part.split("/", 1)
            start = min_val if base == "*" else int(base)
            for v in range(start, max_val + 1, int(step)):
                values.add(v)
        elif "-" in part:
            lo, hi = part.split("-", 1)
            for v in range(int(lo), int(hi) + 1):
                values.add(v)
        else:
            values.add(int(part))
    return values


def cron_matches(cron_expr: str, dt: datetime) -> bool:
    """Check whether *dt* matches a 5-field cron expression."""
    fields = cron_expr.strip().split()
    if len(fields) != 5:
        raise ValueError(f"Expected 5-field cron, got: {cron_expr!r}")

    minute, hour, dom, month, dow = fields
    return (
        dt.minute in _parse_cron_field(minute, 0, 59)
        and dt.hour in _parse_cron_field(hour, 0, 23)
        and dt.day in _parse_cron_field(dom, 1, 31)
        and dt.month in _parse_cron_field(month, 1, 12)
        and dt.weekday() in _parse_cron_field(dow, 0, 6)  # 0=Mon in Python
    )


# ── The actual job ──────────────────────────────────────────────────────────

async def run_weekly_planner() -> dict:
    """Execute the Planner agent's weekly planning pipeline."""
    from backend.agents.planner.agent import PlannerAgent
    from backend.agents.planner.strategy import list_applications, get_goal

    logger.info("⏰ Weekly planner job started")

    agent = PlannerAgent()
    apps = list_applications()
    goal = get_goal()

    result = await agent.plan_week(apps, goal)

    logger.info(
        "✅ Weekly planner complete: %d prioritized apps, %d tasks, report=%s",
        len(result.prioritized_apps),
        len(result.agent_tasks),
        result.report.summary[:80] if result.report.summary else "(empty)",
    )
    return {
        "prioritized": len(result.prioritized_apps),
        "tasks": len(result.agent_tasks),
        "report_id": result.report.id,
    }


# ── Background loop (for FastAPI lifespan) ──────────────────────────────────

async def _scheduler_loop() -> None:
    """Poll every 60 s and fire when the cron expression matches."""
    cron = settings.WEEKLY_PLANNER_CRON
    logger.info("Scheduler started with cron=%s", cron)
    last_run_minute: str = ""

    while True:
        now = datetime.now()
        minute_key = now.strftime("%Y-%m-%d %H:%M")

        if minute_key != last_run_minute and cron_matches(cron, now):
            last_run_minute = minute_key
            try:
                await run_weekly_planner()
            except Exception:
                logger.exception("Weekly planner job failed")

        await asyncio.sleep(60)


@asynccontextmanager
async def scheduler_lifespan() -> AsyncGenerator[None, None]:
    """Start/stop the scheduler as an async context manager."""
    task = asyncio.create_task(_scheduler_loop())
    logger.info("Scheduler background task created")
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        logger.info("Scheduler background task stopped")


# ── CLI one-shot ─────────────────────────────────────────────────────────────

def main() -> None:
    """Run the weekly planner once (for external cron / Task Scheduler)."""
    logging.basicConfig(level=logging.INFO)
    result = asyncio.run(run_weekly_planner())
    print(f"Done: {result}")


if __name__ == "__main__":
    main()
