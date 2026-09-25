from typing import Literal

from langgraph.graph import END, StateGraph

from api.services.agent.nodes.critic import critic_node
from api.services.agent.nodes.escalator import escalator_node
from api.services.agent.nodes.router import router_node
from api.services.agent.nodes.tool_agent import tool_agent_node
from api.services.agent.state import AgentState


def _route_after_router(
    state: AgentState,
) -> Literal["escalator", "agent", "__end__"]:
    """Decide whether to escalate, exit off-topic, or run tool agent."""
    if state.get("is_off_topic"):
        return "__end__"
    if state.get("is_escalated"):
        return "escalator"
    return "agent"


def create_counselor_graph() -> StateGraph:
    """Build multi-turn agentic state graph with LangChain Tool Calling."""
    # Note: TypedDict triggers a known Pyright false-positive with LangGraph's
    # TypedDictLike protocols.
    workflow = StateGraph(AgentState)  # type: ignore

    # 1. Register Processing Nodes
    workflow.add_node("router", router_node)
    workflow.add_node("agent", tool_agent_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("escalator", escalator_node)

    # 2. Define Execution Edges & Transitions
    workflow.set_entry_point("router")

    workflow.add_conditional_edges(
        "router",
        _route_after_router,
        {
            "escalator": "escalator",
            "agent": "agent",
            "__end__": END,
        },
    )

    workflow.add_edge("agent", "critic")
    workflow.add_edge("critic", END)
    workflow.add_edge("escalator", END)

    return workflow


# Compiled singleton graph
counselor_graph = create_counselor_graph().compile()
