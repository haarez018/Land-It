"""LangGraph graph definition — wires all agents under the Planner."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from backend.agents.coach.agent import CoachAgent
from backend.agents.pitcher.agent import PitcherAgent
from backend.agents.planner.agent import PlannerAgent
from backend.agents.scout.agent import ScoutAgent
from backend.agents.tailor.agent import TailorAgent
from backend.agents.tracker.agent import TrackerAgent
from backend.orchestration.router import router
from backend.orchestration.state import AgentState


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("planner", PlannerAgent().run)
    graph.add_node("scout", ScoutAgent().run)
    graph.add_node("tailor", TailorAgent().run)
    graph.add_node("pitcher", PitcherAgent().run)
    graph.add_node("coach", CoachAgent().run)
    graph.add_node("tracker", TrackerAgent().run)

    graph.set_entry_point("planner")

    graph.add_conditional_edges(
        "planner",
        router,
        {
            "scout": "scout",
            "tailor": "tailor",
            "pitcher": "pitcher",
            "coach": "coach",
            "tracker": "tracker",
            "end": END,
        },
    )

    for node in ("scout", "tailor", "pitcher", "coach", "tracker"):
        graph.add_edge(node, "planner")

    return graph.compile()
