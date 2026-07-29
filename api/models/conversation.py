from datetime import datetime, timezone
from typing import List

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.core.database import Base


class Conversation(Base):
    """One ongoing chat thread with a student.

    Identified by a namespaced `session_key` so channels cannot collide:
    "whatsapp:<phone>" for WhatsApp, "web:<id>" for the /chat endpoint.
    A thread is reused while it stays within CONVERSATION_TTL_HOURS of its
    last message; after that a new row is started and the old one is left in
    place for later analytics.
    """

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    messages: Mapped[List["ConversationMessage"]] = relationship(
        "ConversationMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class ConversationMessage(Base):
    """A single turn in a conversation, from either the student or the bot."""

    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )

    # Supports the "last N turns for this conversation" read on every message.
    __table_args__ = (
        Index("ix_conversation_messages_conv_created", "conversation_id", "created_at"),
    )
