import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.logging import get_logger
from api.schemas import ChatRequest, ChatResponse
from api.services.message_formatter import (
    calculate_tnea_cutoff,
    get_suggested_followups,
)
from api.services.rag_service import handle_rag_query, stream_rag_query

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
    semantic search, and generates a grounded response using Gemini.

    Pass the same `session_id` across requests to hold a multi-turn
    conversation; omit it for a one-off, stateless question.
    """
    logger.info(
        "chat_endpoint_requested",
        message_length=len(request.message),
        session_id=request.session_id,
    )
    session_key = f"web:{request.session_id}" if request.session_id else None
    calculated_cutoff = calculate_tnea_cutoff(request.message)

    if session_key:
        from api.services.student_profile_service import get_student_profile

        profile = get_student_profile(session_key)
        if calculated_cutoff is None and profile.calculated_cutoff is not None:
            calculated_cutoff = profile.calculated_cutoff

    response_text, sources = await handle_rag_query(
        db,
        request.message,
        session_key=session_key,
        system_calculated_cutoff=calculated_cutoff,
    )

    suggested_followups = get_suggested_followups(request.message, response_text)

    return ChatResponse(
        response=response_text,
        sources=sources,
        session_id=request.session_id,
        suggested_followups=suggested_followups,
        calculated_cutoff=calculated_cutoff,
    )


@router.post(
    "/stream",
    summary="Submit Student Query with Real-time SSE Token Streaming",
)
async def chat_stream_endpoint(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream student counselling responses token-by-token over Server-Sent Events."""
    logger.info(
        "chat_stream_endpoint_requested",
        message_length=len(request.message),
        session_id=request.session_id,
    )
    session_key = f"web:{request.session_id}" if request.session_id else None

    async def sse_event_generator() -> AsyncIterator[str]:
        try:
            async for event_data in stream_rag_query(
                db, request.message, session_key=session_key
            ):
                payload = json.dumps(event_data)
                yield f"data: {payload}\n\n"
        except Exception as e:
            logger.error("streaming_chat_failed", error=str(e))
            err_payload = json.dumps(
                {
                    "event": "error",
                    "message": "An error occurred during response streaming.",
                }
            )
            yield f"data: {err_payload}\n\n"

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
