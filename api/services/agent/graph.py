from typing import Literal

from langgraph.graph import END, StateGraph

from api.services.agent.nodes.escalator import escalator_node
from api.services.agent.nodes.grader import grader_node
from api.services.agent.nodes.retriever import retriever_node
from api.services.agent.nodes.router import router_node
from api.services.agent.nodes.synthesizer import synthesizer_node
from api.services.agent.state import AgentState


def _route_after_router(state: AgentState) -> Literal["escalator", "retriever"]:
    """Conditional edge deciding whether to escalate or retrieve."""
    if state.get("is_escalated"):
        return "escalator"
    return "retriever"


def create_counselor_graph() -> StateGraph:
    """Build and assemble the multi-turn agentic state graph."""
    # Note: TypedDict triggers a known Pyright false-positive with LangGraph's
    # TypedDictLike protocols.
    workflow = StateGraph(AgentState)  # type: ignore

    # 1. Register Processing Nodes
    workflow.add_node("router", router_node)
    workflow.add_node("retriever", retriever_node)
    workflow.add_node("grader", grader_node)
    workflow.add_node("synthesizer", synthesizer_node)
    workflow.add_node("escalator", escalator_node)

    # 2. Define Execution Edges & Transitions
    workflow.set_entry_point("router")

    workflow.add_conditional_edges(
        "router",
        _route_after_router,
        {
            "escalator": "escalator",
            "retriever": "retriever",
        },
    )

    workflow.add_edge("retriever", "grader")
    workflow.add_edge("grader", "synthesizer")
    workflow.add_edge("synthesizer", END)
    workflow.add_edge("escalator", END)

    return workflow


# Compiled singleton graph
counselor_graph = create_counselor_graph().compile()
