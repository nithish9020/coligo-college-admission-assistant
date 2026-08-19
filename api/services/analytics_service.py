from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import (
    Conversation,
    ConversationMessage,
    Document,
    DocumentChunk,
    Escalation,
)


async def get_analytics_summary(db: AsyncSession) -> dict:
    """Compute high-level admission analytics and performance metrics for the Admin Dashboard."""
    total_docs = (await db.execute(select(func.count(Document.id)))).scalar() or 0
    total_chunks = (
        await db.execute(select(func.count(DocumentChunk.id)))
    ).scalar() or 0
    total_conversations = (
        await db.execute(select(func.count(Conversation.id)))
    ).scalar() or 0
    total_messages = (
        await db.execute(select(func.count(ConversationMessage.id)))
    ).scalar() or 0
    pending_escalations = (
        await db.execute(
            select(func.count(Escalation.id)).where(Escalation.status == "pending")
        )
    ).scalar() or 0
    resolved_escalations = (
        await db.execute(
            select(func.count(Escalation.id)).where(Escalation.status == "resolved")
        )
    ).scalar() or 0

    return {
        "documents": {
            "total_documents": total_docs,
            "total_chunks": total_chunks,
        },
        "conversations": {
            "total_threads": total_conversations,
            "total_messages": total_messages,
            "avg_turns_per_thread": (
                round(total_messages / total_conversations, 1)
                if total_conversations > 0
                else 0.0
            ),
        },
        "escalations": {
            "pending": pending_escalations,
            "resolved": resolved_escalations,
            "total": pending_escalations + resolved_escalations,
        },
    }
