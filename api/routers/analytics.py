from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.logging import get_logger
from api.services.analytics_service import (
    get_analytics_summary,
    get_conversation_detail,
    list_recent_conversations,
)

router = APIRouter(prefix="/analytics", tags=["Admin Analytics"])
logger = get_logger(__name__)


class DocumentStats(BaseModel):
    total_documents: int = Field(..., examples=[2])
    total_chunks: int = Field(..., examples=[150])


class ConversationStats(BaseModel):
    total_threads: int = Field(..., examples=[45])
    total_messages: int = Field(..., examples=[180])
    avg_turns_per_thread: float = Field(..., examples=[4.0])


class EscalationStats(BaseModel):
    pending: int = Field(..., examples=[3])
    resolved: int = Field(..., examples=[12])
    total: int = Field(..., examples=[15])


class AnalyticsSummaryResponse(BaseModel):
    documents: DocumentStats
    conversations: ConversationStats
    escalations: EscalationStats


class ConversationSummaryItem(BaseModel):
    id: int
    session_key: str
    created_at: str | None = None
    last_message_at: str | None = None
    message_count: int
    last_message: str


class ConversationDetailMessage(BaseModel):
    id: int
    role: str
    content: str
    created_at: str | None = None


class ConversationDetailResponse(BaseModel):
    id: int
    session_key: str
    created_at: str | None = None
    last_message_at: str | None = None
    messages: list[ConversationDetailMessage]


@router.get(
    "/summary",
    response_model=AnalyticsSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Admission Analytics Summary",
)
async def get_analytics_summary_endpoint(
    db: AsyncSession = Depends(get_db),
) -> AnalyticsSummaryResponse:
    """Retrieve high-level admission chatbot metrics, thread usage, and escalation counts."""
    logger.info("analytics_summary_requested")
    data = await get_analytics_summary(db)
    return AnalyticsSummaryResponse(**data)


@router.get(
    "/conversations",
    response_model=list[ConversationSummaryItem],
    status_code=status.HTTP_200_OK,
    summary="List Recent Student WhatsApp / Web Chat Sessions",
)
async def list_conversations_endpoint(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[ConversationSummaryItem]:
    """Retrieve recent student chat threads with turn count and latest message preview."""
    conversations = await list_recent_conversations(db, limit=limit)
    return [ConversationSummaryItem(**c) for c in conversations]


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Message History for a Specific Student Chat Session",
)
async def get_conversation_endpoint(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
) -> ConversationDetailResponse:
    """Retrieve full message transcript for a student conversation session."""
    conv = await get_conversation_detail(db, conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )
    return ConversationDetailResponse(**conv)
