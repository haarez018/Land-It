"""AgentState TypedDict for the LangGraph orchestration graph."""

from __future__ import annotations

from typing import Annotated, Optional, TypedDict

from langgraph.graph import add_messages


class AgentState(TypedDict):
    user_id: str
    week_start: str
    weekly_goal: str

    # Current task context
    current_job_id: Optional[str]
    current_application_id: Optional[str]
    next_action: str

    # Agent outputs (accumulated)
    scout_results: list[dict]
    tailoring_results: dict
    cover_letters: dict
    coach_sessions: list[dict]

    # Planner tracking
    actions_taken: list[str]
    weekly_report: Optional[str]
    error_log: list[str]

    # Message history
    messages: Annotated[list, add_messages]
