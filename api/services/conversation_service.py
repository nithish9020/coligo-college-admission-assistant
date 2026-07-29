from datetime import datetime, timedelta, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
from api.core.logging import get_logger
from api.models import Conversation, ConversationMessage

logger = get_logger(__name__)

# Cap a single stored turn before it reaches the prompt, so one pasted essay
# can't crowd out the retrieved context.
MAX_TURN_CHARS = 1000


async def get_or_create_conversation(
    db: AsyncSession, session_key: str
) -> Conversation:
    """Return the live conversation for `session_key`, or start a new one.

    A thread stays live while its last message is within
    CONVERSATION_TTL_HOURS. Past that the old row is left untouched (useful
    later for analytics) and a fresh conversation begins.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(
        hours=settings.CONVERSATION_TTL_HOURS
    )

    stmt = (
        select(Conversation)
        .where(
            Conversation.session_key == session_key,
            Conversation.last_message_at >= cutoff,
        )
        .order_by(Conversation.last_message_at.desc())
        .limit(1)
    )
    conversation = (await db.execute(stmt)).scalars().first()

    if conversation is not None:
        logger.debug(
            "conversation_resumed",
            session_key=session_key,
            conversation_id=conversation.id,
        )
        return conversation

    conversation = Conversation(session_key=session_key)
    db.add(conversation)
    await db.flush()  # populates conversation.id
    logger.info(
        "conversation_started",
        session_key=session_key,
        conversation_id=conversation.id,
    )
    return conversation


async def get_recent_turns(
    db: AsyncSession, conversation_id: int
) -> List[ConversationMessage]:
    """Last CONVERSATION_MAX_TURNS messages, oldest-first for prompt rendering."""
    stmt = (
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.created_at.desc(), ConversationMessage.id.desc())
        .limit(settings.CONVERSATION_MAX_TURNS)
    )
    turns = list((await db.execute(stmt)).scalars().all())
    turns.reverse()  # chronological order for the prompt
    logger.debug(
        "conversation_history_loaded",
        conversation_id=conversation_id,
        turn_count=len(turns),
    )
    return turns


async def append_turn(
    db: AsyncSession, conversation: Conversation, role: str, content: str
) -> None:
    """Store one turn and mark the conversation as freshly active."""
    db.add(
        ConversationMessage(
            conversation_id=conversation.id,
            role=role,
            content=content,
        )
    )
    conversation.last_message_at = datetime.now(timezone.utc)
    await db.flush()


def format_history(turns: List[ConversationMessage]) -> str:
    """Render turns as `User:` / `Assistant:` lines for the prompt."""
    if not turns:
        return ""
    lines = []
    for turn in turns:
        speaker = "User" if turn.role == "user" else "Assistant"
        content = turn.content.strip()
        if len(content) > MAX_TURN_CHARS:
            content = content[:MAX_TURN_CHARS] + "..."
        lines.append(f"{speaker}: {content}")
    return "\n".join(lines)
