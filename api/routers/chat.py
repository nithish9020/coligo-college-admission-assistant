from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.logging import get_logger
from api.schemas import ChatRequest, ChatResponse
from api.services import handle_rag_query

router = APIRouter(prefix="/chat", tags=["AI Counseling"])
logger = get_logger(__name__)


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit Student Query (RAG Chat)",
)
async def chat_endpoint(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Submit a query to the AI counseling assistant.

    The assistant retrieves relevant PDF document context from the database using
    semantic search, and generates a grounded response using Gemini-1.5-Flash.
    """
    logger.info("chat_endpoint_requested", message_length=len(request.message))
    response_text, sources = await handle_rag_query(db, request.message)
    return ChatResponse(response=response_text, sources=sources)
