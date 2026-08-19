import re
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


SYSTEM_PROMPT_TEMPLATE = """You are Coligo, a helpful senior student at SKCET guiding candidates through TNEA admissions over WhatsApp.

Tone & Formatting Guidelines for WhatsApp:
- CRITICAL LANGUAGE RULE: Detect Tanglish keywords (such as "evlo", "sollunga", "ku", "nallarkuma", "kidaikuma", "paaka", "enaku"). If detected, YOU MUST RESPOND IN NATURAL, FRIENDLY TANGLISH (e.g. "SKCET la CSE cutoff OC category ku 192.5 thambi! Unakku vere branch cutoff venuma?"). Match the user's language style.
- Be direct, concise, and punchy. Avoid robotic fluff, long intros, or repeating previous messages.
- Highlights & Tabular Data: Present cutoffs, fees, or branch comparisons cleanly using bullet points and pipe separators (e.g., • *OC*: 192.5 (Rank 4705) | *BC*: 190.0 (Rank 7448)).
- Formatting: Use single asterisk bold text (*text*). NEVER use double asterisks (**text**).
- Keep total response length under 4 to 6 short lines.
- Speak naturally like an elder college brother/sister in a live chat.
- Context Awareness: Answer follow-up questions directly without repeating old information or headers from previous turns.

Strict Knowledge Rules:
1. Base your answer ONLY on the provided Context snippets below.
2. If the context does not contain the specific answer or requested cutoff details, respond politely in friendly Tanglish/English: "Sorry pa, en kitta adhu pathina exact details/cutoff marks ippodhiku illa. Official documents update pannitu koodiya seekram solren!" NEVER ask the user the same question back or loop.
3. TNEA Cutoff marks are out of 200: Maths + (Physics/2) + (Chemistry/2). Lower general ranks are better.
4. Cutoffs depend on community (OC, BC, BCM, MBC, SC, SCA, ST).

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


def detect_college_keyword(text: str) -> str | None:
    """Detect if a specific college is named in the user query."""
    cleaned = text.lower()
    if "psg" in cleaned:
        return "psg"
    if "cit" in cleaned:
        return "cit"
    if "anna" in cleaned:
        return "anna"
    if "skcet" in cleaned:
        return "skcet"
    if "srm" in cleaned:
        return "srm"
    return None


def reorder_chunks_lost_in_middle(
    rows: List[Tuple[DocumentChunk, str]],
) -> List[Tuple[DocumentChunk, str]]:
    """Reorder retrieved chunks using Lost-in-the-Middle mitigation algorithm.

    Places the highest-ranked chunks at the very beginning and very end of the context
    sequence so the LLM pays maximum attention to top facts.
    """
    if len(rows) <= 2:
        return rows

    reordered: List[Tuple[DocumentChunk, str]] = []
    left_side = True
    for row in rows:
        if left_side:
            reordered.insert(0, row)
        else:
            reordered.append(row)
        left_side = not left_side
    return reordered


def validate_numeric_facts(generated_answer: str, context_str: str) -> bool:
    """Validate that numeric facts (cutoffs, ranks, fees) in the generated reply are grounded in context.

    Returns True if valid, False if ungrounded numeric hallucination is detected.
    """
    # Extract numbers (integers and floats) from the generated answer
    answer_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", generated_answer))
    if not answer_numbers:
        return True

    context_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", context_str))
    # Standard allowed TNEA constants (out of 200, max 100, 24 hours, etc.)
    allowed_constants = {
        "200",
        "100",
        "50",
        "2",
        "4",
        "24",
        "1",
        "2023",
        "2024",
        "2025",
        "2026",
    }

    ungrounded = []
    for num in answer_numbers:
        if num not in allowed_constants and num not in context_numbers:
            ungrounded.append(num)

    if ungrounded:
        logger.warning(
            "numeric_hallucination_detected",
            ungrounded_numbers=ungrounded,
            answer_snippet=generated_answer[:100],
        )
        return False

    return True


async def handle_rag_query(
    db: AsyncSession, query_text: str, session_key: str | None = None
) -> Tuple[str, List[str]]:
    """Execute the full RAG pipeline with chunk reordering & hallucination guardrails."""
    logger.info(
        "handling_rag_query_start", query_text=query_text, session_key=session_key
    )

    # 1. Load conversation history
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

    # 2. Condense follow-ups & normalize query
    retrieval_query = query_text
    if history_str and settings.ENABLE_QUERY_REWRITING:
        retrieval_query = await condense_question(history_str, query_text)

    normalized_retrieval_query = normalize_query(retrieval_query)

    # 3. Fetch query vector embedding
    logger.debug("embedding_query_text")
    query_embeddings = await get_embeddings([normalized_retrieval_query])
    query_vector = query_embeddings[0]

    # 4. Query database for closest chunks using cosine distance
    logger.debug("querying_pgvector_for_closest_chunks", top_k=settings.RAG_TOP_K)
    college_kw = detect_college_keyword(retrieval_query) or detect_college_keyword(
        query_text
    )
    stmt = select(DocumentChunk, Document.document_ref).join(
        Document, DocumentChunk.document_id == Document.id
    )
    if college_kw:
        logger.info("filtering_pgvector_by_college", college_keyword=college_kw)
        stmt = stmt.where(Document.document_ref.ilike(f"%{college_kw}%"))

    stmt = stmt.order_by(DocumentChunk.embedding.cosine_distance(query_vector)).limit(
        settings.RAG_TOP_K
    )

    result = await db.execute(stmt)
    rows: List[Tuple[DocumentChunk, str]] = [(row[0], row[1]) for row in result.all()]

    # 5. Apply Lost-in-the-Middle Chunk Re-ordering
    reordered_rows = reorder_chunks_lost_in_middle(rows)

    # 6. Compile context string and unique sources
    context_parts: List[str] = []
    sources: List[str] = []

    for chunk, document_ref in reordered_rows:
        context_parts.append(
            f"--- Source: {document_ref} (Chunk Index: {chunk.chunk_index}) ---\n"
            f"{chunk.text_content}"
        )
        if document_ref not in sources:
            sources.append(document_ref)

    if not context_parts:
        logger.warning("rag_search_returned_empty_context")
        if session_key:
            try:
                db.add(Escalation(sender=session_key, query_text=query_text))
                await db.commit()
            except Exception as e:
                logger.error("escalation_logging_failed", error=str(e))

        college_display = (college_kw or "that college").upper()
        return (
            f"Sorry pa, {college_display} pathina official documents/details innum "
            "database la add aagala. Streamlit Admin portal web scraper la link feed "
            "panni scrape pannunga, naan padichuttu solren!",
            [],
        )
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

    # 7. Execute Numeric Fact Verification Guardrail
    is_factually_grounded = validate_numeric_facts(answer, context_str)
    if not is_factually_grounded:
        logger.warning(
            "numeric_validation_failed_flagged_for_review",
            query=query_text,
            session_key=session_key,
        )

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
