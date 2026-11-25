"""Build the LangGraph RecoveryGraph state machine."""
from __future__ import annotations

from typing import TYPE_CHECKING

from langgraph.graph import END, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from backend.graph.state import RecoveryState

if TYPE_CHECKING:
    from backend.graph.base_agent import BaseAgent

MAX_REPLANS = 3


def _should_replan(state: RecoveryState) -> str:
    """Conditional edge from Verify: loop back to Plan or finish."""
    if state.get("replan_required") and state.get("replan_count", 0) < MAX_REPLANS:
        return "plan"
    return END


def build_recovery_graph(agents: dict[str, "BaseAgent"]):  # type: ignore[return]
    """Compile and return the RecoveryGraph.

    Args:
        agents: dict mapping agent names ("monitor", "diagnose", …) to instances.

    Returns:
        A compiled LangGraph ``CompiledGraph``.
    """
    graph = StateGraph(RecoveryState)

    # Add one node per agent
    for name, agent in agents.items():
        graph.add_node(name, agent.run)

    # Fixed entry point
    graph.set_entry_point("monitor")

    # Linear edges
    graph.add_edge("monitor", "diagnose")
    graph.add_edge("diagnose", "plan")
    graph.add_edge("plan", "recover")
    graph.add_edge("recover", "verify")

    # Conditional edge from verify — loop or finish
    graph.add_conditional_edges(
        "verify",
        _should_replan,
        {"plan": "plan", END: END},
    )

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)
