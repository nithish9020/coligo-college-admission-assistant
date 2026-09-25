"""Streamlit Chat & Agent Streaming Integration Service."""

import asyncio
import concurrent.futures
import time
from typing import Any, Coroutine, Generator

from api.core.database import async_session_factory
from api.core.logging import get_logger
from api.services.message_formatter import calculate_tnea_cutoff
from api.services.rag_service import handle_rag_query
from api.services.student_profile_service import get_student_profile

logger = get_logger(__name__)


def _run_async_safely(coro: Coroutine[Any, Any, Any]) -> Any:
    """Execute coroutine safely even if an asyncio loop is active in the current thread."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(lambda: asyncio.run(coro))
            return future.result()
    else:
        return asyncio.run(coro)


def stream_agent_response(
    query: str, session_key: str
) -> tuple[Generator[str, None, None], list[str], str]:
    """Execute LangGraph agent and return a token streaming generator, source citations, and full text."""
    profile = get_student_profile(session_key)
    cutoff = calculate_tnea_cutoff(query)
    if cutoff is None and profile.calculated_cutoff is not None:
        cutoff = profile.calculated_cutoff

    async def _run_query() -> tuple[str, list[str]]:
        async with async_session_factory() as db:
            return await handle_rag_query(
                db=db,
                query_text=query,
                session_key=session_key,
                system_calculated_cutoff=cutoff,
            )

    try:
        answer, sources = _run_async_safely(_run_query())
    except Exception as e:
        logger.error(
            "agent_stream_execution_failed",
            error=str(e),
            session_key=session_key,
        )
        answer = (
            "I encountered a momentary issue accessing the knowledge base. "
            "Please try asking your question again!"
        )
        sources = []

    def token_generator() -> Generator[str, None, None]:
        words = answer.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            time.sleep(0.012)

    return token_generator(), sources, answer
