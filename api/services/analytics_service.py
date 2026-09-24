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


async def list_recent_conversations(db: AsyncSession, limit: int = 50) -> list[dict]:
    """Retrieve recent student chat threads with turn count and latest message preview."""
    from sqlalchemy.orm import selectinload

    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .order_by(Conversation.last_message_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    conversations = result.scalars().all()

    items = []
    for conv in conversations:
        msgs = conv.messages or []
        last_msg = msgs[-1].content if msgs else ""
        items.append(
            {
                "id": conv.id,
                "session_key": conv.session_key,
                "created_at": conv.created_at.isoformat() if conv.created_at else None,
                "last_message_at": (
                    conv.last_message_at.isoformat() if conv.last_message_at else None
                ),
                "message_count": len(msgs),
                "last_message": (
                    last_msg[:120] + "..." if len(last_msg) > 120 else last_msg
                ),
            }
        )
    return items


async def get_conversation_detail(
    db: AsyncSession, conversation_id: int
) -> dict | None:
    """Retrieve full message history for a given student conversation session."""
    from sqlalchemy.orm import selectinload

    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    result = await db.execute(stmt)
    conv = result.scalar_one_or_none()
    if not conv:
        return None

    return {
        "id": conv.id,
        "session_key": conv.session_key,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
        "last_message_at": (
            conv.last_message_at.isoformat() if conv.last_message_at else None
        ),
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in (conv.messages or [])
        ],
    }
