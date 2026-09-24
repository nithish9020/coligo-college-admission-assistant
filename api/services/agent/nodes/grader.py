from typing import Any

from api.core.logging import get_logger
from api.services.agent.state import AgentState

logger = get_logger(__name__)


async def grader_node(state: AgentState) -> dict[str, Any]:
    """Grade retrieved chunks to verify admission & cutoff grounding."""
    chunks = state.get("retrieved_chunks") or []
    if not chunks:
        logger.warning("grader_node_no_chunks_found")
        return {"is_grounded": False}

    community = (state.get("community") or "").upper()
    colleges = state.get("colleges") or []

    # Concatenate texts for quick relevance scanning
    combined_text = " ".join(c.get("text_content", "") for c in chunks).lower()

    # Check 1: Does context contain cutoff or admission keywords?
    has_admission_data = any(
        kw in combined_text
        for kw in ["cutoff", "closing", "tnea", "admission", "rank", "mark", "quota"]
    )

    # Check 2: If community is explicitly requested, is it referenced?
    community_grounded = True
    if community and community != "ALL":
        # Check if community is mentioned in context
        community_grounded = (
            f" {community.lower()} " in combined_text
            or f"({community.lower()})" in combined_text
            or f"{community.lower()}:" in combined_text
        )

    # Check 3: If colleges were specified, is at least one present?
    college_grounded = True
    if colleges:
        college_grounded = any(kw.lower() in combined_text for kw in colleges)

    is_grounded = has_admission_data and (community_grounded or college_grounded)
    logger.info("grader_node_evaluation", is_grounded=is_grounded, community=community)

    return {"is_grounded": is_grounded}
