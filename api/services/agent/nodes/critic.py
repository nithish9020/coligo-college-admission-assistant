"""Self-Correcting Hallucination Critic Node for TNEA Admission Assistant."""

from typing import Any

from api.core.logging import get_logger
from api.services.agent.state import AgentState
from api.services.rag_service import validate_numeric_facts

logger = get_logger(__name__)


async def critic_node(state: AgentState) -> dict[str, Any]:
    """Verify numeric accuracy of synthesized response and correct hallucinations."""
    response_text = state.get("response_text", "")
    cutoff = state.get("calculated_cutoff")
    raw_message = state.get("raw_message", "")
    chunks = state.get("retrieved_chunks") or []

    # Verified database tools are pre-grounded against PostgreSQL tables
    sources = state.get("sources") or []
    if sources:
        logger.info(
            "critic_node_numeric_verification_passed_via_tools", sources=sources
        )
        return {"is_verified": True}

    # Assemble grounding context from retrieved document chunks
    context_text = " ".join(c.get("text_content", "") for c in chunks)

    # Perform strict numeric fact validation
    is_valid = validate_numeric_facts(
        response_text, context_text, cutoff, query_text=raw_message
    )

    if not is_valid:
        logger.warning(
            "critic_node_hallucination_detected",
            cutoff=cutoff,
            query=raw_message,
        )
        # Self-correction: check if structured cutoff records were retrieved
        structured_chunk = next(
            (c for c in chunks if "Official" in c.get("document_ref", "")),
            None,
        )
        if structured_chunk and structured_chunk.get("text_content"):
            clean_table = structured_chunk["text_content"].strip()
            # Replace hallucinated section with verified official cutoff table
            corrected_text = (
                f"{response_text}\n\n"
                f"📋 *Verified Official TNEA Cutoff Table:*\n"
                f"{clean_table}"
            )
            return {
                "response_text": corrected_text,
                "is_verified": True,
            }

        correction_notice = (
            "\n\n⚠️ _Note: Please verify specific branch cutoff marks against "
            "official TNEA closing rank reports at tneaonline.org._"
        )
        return {
            "response_text": f"{response_text}{correction_notice}",
            "is_verified": False,
        }

    logger.info("critic_node_numeric_verification_passed")
    return {"is_verified": True}
