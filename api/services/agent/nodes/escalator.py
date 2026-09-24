from typing import Any

from langchain_core.runnables import RunnableConfig
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.logging import get_logger
from api.models.escalation import Escalation
from api.services.agent.state import AgentState

logger = get_logger(__name__)


async def escalator_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    """Record sensitive or out-of-scope inquiry to the human escalation queue."""
    db: AsyncSession = config["configurable"]["db"]
    raw_message = state.get("raw_message", "")
    session_key = state.get("session_key") or "web:unauthenticated"
    reason = state.get("escalation_reason", "Out of scope admission inquiry")

    logger.warning(
        "agent_escalating_query_to_human_counselor",
        session_key=session_key,
        reason=reason,
    )

    try:
        escalation = Escalation(
            sender=session_key,
            query_text=f"[{reason}] {raw_message}",
            status="pending",
        )
        db.add(escalation)
        await db.commit()
    except Exception as e:
        logger.error("failed_to_persist_escalation", error=str(e))

    response_text = (
        "⚠️ This inquiry involves admission policies or seats "
        "that require official human verification.\n\n"
        "• Your query has been flagged for our **Human Counselor** team.\n"
        "• An officer will review your request. For immediate assistance, "
        "please visit the college admissions office or tneaonline.org."
    )

    return {
        "response_text": response_text,
        "is_escalated": True,
        "sources": [],
    }
