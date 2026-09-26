"""Streamlit Chat & Agent Streaming Integration Service."""

import asyncio
import threading
import time
from typing import Any, Coroutine, Generator, cast

from api.core.database import async_session_factory
from api.core.logging import get_logger
from api.services.message_formatter import calculate_tnea_cutoff
from api.services.rag_service import handle_rag_query
from api.services.student_profile_service import get_student_profile

logger = get_logger(__name__)

_bg_loop: asyncio.AbstractEventLoop | None = None
_bg_thread: threading.Thread | None = None
_bg_lock = threading.Lock()


def _get_background_loop() -> asyncio.AbstractEventLoop:
    global _bg_loop, _bg_thread
    with _bg_lock:
        if _bg_loop is None or _bg_loop.is_closed():
            _bg_loop = asyncio.new_event_loop()
            _bg_thread = threading.Thread(
                target=_bg_loop.run_forever,
                name="agent_streamer_bg_loop",
                daemon=True,
            )
            _bg_thread.start()
        return _bg_loop


def run_async_safely(coro: Coroutine[Any, Any, Any]) -> Any:
    """Execute coroutine safely on the persistent background event loop."""
    loop = _get_background_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()


_run_async_safely = run_async_safely


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
        from api.services.message_formatter import strip_emojis

        answer = strip_emojis(answer)
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


def load_session_chat_history(session_key: str) -> list[dict[str, Any]]:
    """Load persistent chat history from DB for the authenticated student."""
    from api.services.conversation_service import (
        get_conversation_turns_for_session,
    )

    async def _fetch() -> list[dict[str, Any]]:
        async with async_session_factory() as db:
            turns = await get_conversation_turns_for_session(db, session_key)
            formatted = []
            for t in turns:
                role = "user" if t.role == "user" else "assistant"
                formatted.append({"role": role, "content": t.content, "sources": []})
            return formatted

    try:
        return cast(list[dict[str, Any]], _run_async_safely(_fetch()) or [])
    except Exception as e:
        logger.warning(
            "failed_to_load_chat_history",
            session_key=session_key,
            error=str(e),
        )
        return []
