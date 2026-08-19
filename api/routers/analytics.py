from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.logging import get_logger
from api.services.analytics_service import get_analytics_summary

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
