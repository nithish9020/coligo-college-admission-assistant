from typing import Any, Optional

from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    """Central state container for the LangGraph TNEA Admission Assistant."""

    # Input message & session context
    session_key: str
    raw_message: str
    history_text: str

    # Extracted entities & deterministic attributes
    intent: str  # "cutoff_query" | "choice_filling" | "general_faq" | "escalation"
    marks: Optional[dict[str, float]]  # {"maths": 100.0, "physics": 90.0, ...}
    calculated_cutoff: Optional[float]  # e.g. 180.0
    community: Optional[str]  # e.g. "BC", "OC", "MBC", "SC", "ST", "BCM"
    colleges: list[str]  # e.g. ["skcet", "psg"]
    branches: list[str]  # e.g. ["cse", "it", "aids"]

    # Retrieval & evaluation
    rewritten_query: str
    retrieved_chunks: list[dict[str, Any]]
    sources: list[str]
    is_grounded: bool

    # Out-of-scope & human escalation
    is_escalated: bool
    escalation_reason: Optional[str]

    # Synthesized final output
    response_text: str
