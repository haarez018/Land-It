"""Conditional routing logic — Planner decides which agent to call next."""

from __future__ import annotations

from backend.orchestration.state import AgentState


def router(state: AgentState) -> str:
    """Planner decides next agent based on current state and weekly strategy."""
    return state["next_action"]
