import time
from typing import Dict, List, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
from api.core.logging import get_logger
from api.models import Document, DocumentChunk, Escalation
from api.services.conversation_service import (
    append_turn,
    format_history,
    get_or_create_conversation,
    get_recent_turns,
)
from api.services.embedding_service import get_embeddings
from api.services.llm_service import generate_response_from_llm
from api.services.query_normalizer import normalize_query
from api.services.query_rewriter import condense_question

logger = get_logger(__name__)

CACHE_TTL_SECONDS = 3600  # 1 hour TTL
MAX_CACHE_ENTRIES = 500
_RAG_RESPONSE_CACHE: Dict[str, Tuple[str, List[str], float]] = {}


def get_cached_rag_response(query_text: str) -> Tuple[str, List[str]] | None:
    """Return cached RAG answer and sources for common queries if unexpired."""
    cache_key = query_text.strip().lower()
    if cache_key in _RAG_RESPONSE_CACHE:
        answer, sources, timestamp = _RAG_RESPONSE_CACHE[cache_key]
        if time.time() - timestamp < CACHE_TTL_SECONDS:
            logger.info("rag_response_cache_hit", query=query_text)
            return answer, sources
        del _RAG_RESPONSE_CACHE[cache_key]
    return None


def set_cached_rag_response(query_text: str, answer: str, sources: List[str]) -> None:
    """Cache generated RAG answer in memory with timestamp."""
    cache_key = query_text.strip().lower()
    if len(_RAG_RESPONSE_CACHE) >= MAX_CACHE_ENTRIES:
        oldest_key = min(_RAG_RESPONSE_CACHE, key=lambda k: _RAG_RESPONSE_CACHE[k][2])
        del _RAG_RESPONSE_CACHE[oldest_key]
    _RAG_RESPONSE_CACHE[cache_key] = (answer, sources, time.time())


SYSTEM_PROMPT_TEMPLATE = """You are Coligo, a friendly and encouraging senior \
student guide for Tamil Nadu Engineering Admissions (TNEA). You talk to students \
like a supportive senior peer or elder friend who has already navigated TNEA \
counselling and is helping them explore college options.

Tone and Style:
- Warm, empathetic, conversational, and approachable.
- Avoid stiff, robotic, or overly corporate language.
- Use short, clear, easy-to-read paragraphs.

Rules:
1. Ground every single fact strictly in the provided Context snippets below.
2. If the context does not contain enough information to answer, warmly state \
that you don't have that specific detail in the official documents yet. Never \
make up or extrapolate facts outside the context.
3. TNEA cutoff marks are out of 200 (Maths/2 + Physics/4 + Chemistry/4). Cutoff \
ranks are general TNEA ranks where a lower number is better. Never confuse cutoff \
marks with cutoff ranks.
4. Cutoffs differ by community (OC, BC, BCM, MBC, SC, SCA, ST). If not specified, \
share available community details or gently ask which community applies.
5. Remind students encouragingly that past cutoffs serve as guidance.
6. Use the Conversation history so far to understand follow-ups naturally.
{history}
Context:
{context}

Question:
{question}

Answer:"""

HISTORY_BLOCK_TEMPLATE = """
Conversation so far:
{history}
"""


async def handle_rag_query(
    db: AsyncSession, query_text: str, session_key: str | None = None
) -> Tuple[str, List[str]]:
    """Execute the full RAG pipeline for a user chat query.

    1. Loads conversation history (when session_key is given).
    2. Condenses follow-ups into a standalone question for retrieval.
    3. Embeds the (condensed) query text.
    4. Performs pgvector cosine distance search.
    5. Formats prompt with history + retrieved context.
    6. Generates reply from Gemini LLM and stores both turns.

    Without a session_key this behaves exactly as the original stateless
    pipeline: no history is read, nothing is persisted.

    Returns:
        Tuple of (generated_answer, list_of_source_document_refs)
    """
    logger.info(
        "handling_rag_query_start", query_text=query_text, session_key=session_key
    )

    # 1. Load conversation history. Memory is an enhancement, never a hard
    # dependency: if any of this fails we answer statelessly rather than error.
    conversation = None
    history_str = ""
    if session_key:
        try:
            conversation = await get_or_create_conversation(db, session_key)
            turns = await get_recent_turns(db, conversation.id)
            history_str = format_history(turns)
        except Exception as e:
            logger.error(
                "conversation_history_load_failed",
                session_key=session_key,
                error=str(e),
            )
            conversation = None
            history_str = ""

    # 1b. Check In-Memory RAG Response Cache (for queries without prior history)
    if not history_str:
        cached = get_cached_rag_response(query_text)
        if cached is not None:
            return cached

    # 2. Condense a follow-up ("what about ECE?") into a standalone question,
    # otherwise retrieval embeds the bare phrase and finds the wrong chunks.
    retrieval_query = query_text
    if history_str and settings.ENABLE_QUERY_REWRITING:
        retrieval_query = await condense_question(history_str, query_text)

    # Normalize query typos and expand abbreviations for vector embedding search
    normalized_retrieval_query = normalize_query(retrieval_query)

    # 3. Fetch query vector embedding
    logger.debug("embedding_query_text")
    query_embeddings = await get_embeddings([normalized_retrieval_query])
    query_vector = query_embeddings[0]

    # 2. Query database for closest chunks using cosine distance
    logger.debug("querying_pgvector_for_closest_chunks", top_k=settings.RAG_TOP_K)
    stmt = (
        select(DocumentChunk, Document.document_ref)
        .join(Document, DocumentChunk.document_id == Document.id)
        .order_by(DocumentChunk.embedding.cosine_distance(query_vector))
        .limit(settings.RAG_TOP_K)
    )

    result = await db.execute(stmt)
    rows = result.all()

    # 3. Compile context string and unique sources
    context_parts: List[str] = []
    sources: List[str] = []

    for chunk, document_ref in rows:
        context_parts.append(
            f"--- Source: {document_ref} (Chunk Index: {chunk.chunk_index}) ---\n"
            f"{chunk.text_content}"
        )
        if document_ref not in sources:
            sources.append(document_ref)

    if not context_parts:
        logger.warning("rag_search_returned_empty_context")
        context_str = "No relevant context is available in the database."
        if session_key:
            try:
                db.add(Escalation(sender=session_key, query_text=query_text))
                await db.flush()
            except Exception as e:
                logger.error("escalation_logging_failed", error=str(e))
    else:
        context_str = "\n\n".join(context_parts)
        logger.info(
            "rag_context_compiled_successfully",
            chunk_count=len(context_parts),
            source_count=len(sources),
        )

    # 4. Construct prompt and request answer from LLM. The user's original
    # wording goes in as the question -- the condensed form was only ever a
    # retrieval device, and feeding it back would flatten how they actually asked.
    prompt = SYSTEM_PROMPT_TEMPLATE.format(
        history=(
            HISTORY_BLOCK_TEMPLATE.format(history=history_str) if history_str else ""
        ),
        context=context_str,
        question=query_text,
    )

    logger.debug("requesting_llm_generation")
    answer = await generate_response_from_llm(prompt)

    if not history_str:
        set_cached_rag_response(query_text, answer, sources)

    # 5. Persist both turns so the next message can see them. A write failure
    # must not lose an answer the user is already waiting on.
    if conversation is not None:
        try:
            await append_turn(db, conversation, "user", query_text)
            await append_turn(db, conversation, "assistant", answer)
            await db.commit()
        except Exception as e:
            logger.error(
                "conversation_history_save_failed",
                session_key=session_key,
                error=str(e),
            )

    logger.info("rag_query_handled_successfully", source_count=len(sources))
    return answer, sources
