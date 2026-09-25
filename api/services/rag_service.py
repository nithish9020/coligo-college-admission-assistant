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

_FALLBACK_PHRASES = (
    "high inquiry volume",
    "tiny hiccup",
    "experiencing high demand",
    "try asking again",
    "check back shortly",
    "trouble connecting",
    "could not generate",
)


def _is_fallback_or_error_response(answer: str) -> bool:
    """Return True if answer is an error or fallback message that should never be cached."""
    if not answer or not answer.strip():
        return True
    lowered = answer.lower()
    return any(phrase in lowered for phrase in _FALLBACK_PHRASES)


def clear_rag_response_cache() -> None:
    """Clear all entries in the in-memory RAG response cache."""
    _RAG_RESPONSE_CACHE.clear()
    logger.info("rag_response_cache_cleared")


def get_cached_rag_response(query_text: str) -> Tuple[str, List[str]] | None:
    """Return cached RAG answer and sources for common queries if unexpired and valid."""
    cache_key = query_text.strip().lower()
    if cache_key in _RAG_RESPONSE_CACHE:
        answer, sources, timestamp = _RAG_RESPONSE_CACHE[cache_key]
        if time.time() - timestamp < CACHE_TTL_SECONDS:
            if not _is_fallback_or_error_response(answer):
                logger.info("rag_response_cache_hit", query=query_text)
                return answer, sources
            logger.info("evicting_polluted_cache_entry", query=query_text)
        del _RAG_RESPONSE_CACHE[cache_key]
    return None


def set_cached_rag_response(query_text: str, answer: str, sources: List[str]) -> None:
    """Cache generated RAG answer in memory with timestamp, never caching fallbacks."""
    if _is_fallback_or_error_response(answer):
        logger.debug("skipping_cache_for_fallback_response", query=query_text)
        return
    cache_key = query_text.strip().lower()
    if len(_RAG_RESPONSE_CACHE) >= MAX_CACHE_ENTRIES:
        oldest_key = min(_RAG_RESPONSE_CACHE, key=lambda k: _RAG_RESPONSE_CACHE[k][2])
        del _RAG_RESPONSE_CACHE[oldest_key]
    _RAG_RESPONSE_CACHE[cache_key] = (answer, sources, time.time())


SYSTEM_PROMPT_TEMPLATE = """You are *Coligo*, an independent Tamil Nadu Engineering Admissions (TNEA) counselling assistant. You serve students looking at ALL engineering colleges in Tamil Nadu — you are NOT affiliated with, and do NOT represent or favour, any single college.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IDENTITY GUARDRAILS (NON-NEGOTIABLE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- You are a neutral, multi-college TNEA guide. You have NO home college.
- NEVER assume or default to any specific college when the student does not name one.
- If the student gives only marks or only a department (e.g., "CSE cutoff" or "my cutoff is 175"), you MUST list results for ALL colleges present in the context, not just one.
- ALWAYS explicitly state the College Name next to any branch or cutoff you list, so the student knows which college it belongs to.
- NEVER invent, assume, or hallucinate college names, cutoffs, ranks, or fees. Ground every number in the Context below.
- If you do not have data for a specific college or query, say exactly: "I don't have that information right now." Do not fill the gap with data from another college.
- NEVER list or name specific colleges in the abstract. Only mention a college when its data is present in the Context below.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW TO HANDLE DIFFERENT QUERY TYPES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. MARK / CUTOFF QUERY (student gives marks OR asks for cutoff without naming a college):
   - Use the pre-calculated cutoff if one is provided. DO NOT calculate the cutoff yourself.
   - Show the cutoff eligibility result for EVERY college and branch present in the Context, formatted as a comparison list.
   - Do NOT show only one college.

2. DEPARTMENT QUERY (student asks "CSE cutoff" or "which college has ECE?" without naming a college):
   - List the relevant branch cutoffs from EVERY college present in the Context.
   - Present as a side-by-side or bullet comparison so the student can evaluate options.

3. COLLEGE-SPECIFIC QUERY (student names a college, e.g. "Tell me about PSG"):
   - Focus ONLY on that college's data from the Context.
   - For a general "tell me about" query: first list the courses/branches offered.
   - For a cutoff query: show cutoffs per community.
   - Do NOT mix in data from other colleges unless directly asked to compare.

4. COMPARISON QUERY (student says "compare SKCET and PSG", "which is better"):
   - Present a structured side-by-side comparison using bullet points with | separators.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT KNOWLEDGE & GROUNDING RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Answer ONLY using the Context snippets provided below. Never fabricate any data.
- If the context does not contain enough information to answer, say: "I don't have the exact details for this at the moment." — then stop. Do NOT loop, do NOT ask the same question back, do NOT suggest checking another college unless the data is missing.
- TNEA cutoffs are out of 200. Lower rank numbers are more competitive.
- Community categories: OC, BC, BCM, MBC, SC, SCA, ST.
- Never repeat a number, rank, or fee that is not explicitly present in the Context.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHATSAPP FORMATTING RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Bold: use *single asterisks*. NEVER use **double asterisks**.
- Keep responses concise: 6–10 lines max. No long preambles.
- Use bullet points (•) for lists. Use pipe (|) for inline comparisons.
- Do NOT add greeting phrases, sign-offs, or filler text.
- Answer follow-up questions directly without restating previous answers.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELF-CHECK BEFORE RESPONDING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Before writing your answer, internally ask yourself:
1. Did the student name a specific college? If NO → include ALL colleges from the Context.
2. Is every number I'm about to write found in the Context? If NO → remove it.
3. Am I defaulting to a specific college because it appears first in the Context? If YES → include all colleges.
4. Am I asking the student a question they already answered? If YES → do not ask it again.

{history}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXT (source documents — use ONLY these):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STUDENT QUESTION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{question}

Answer:"""

HISTORY_BLOCK_TEMPLATE = """
Conversation so far:
{history}
"""


# ── College alias map for keyword detection ──
# Each entry: (list of aliases to match in the query, search term for DB filtering)
COLLEGE_ALIASES: list[tuple[list[str], str]] = [
    (["psg"], "psg"),
    (["cit", "coimbatore institute"], "coimbatore institute"),
    (["anna university", "anna univ"], "anna"),
    (["skcet", "sri krishna"], "sri krishna"),
    (["srm"], "srm"),
    (["bannari", "bit sathy", "bit erode"], "bannari"),
    (["kongu", "kec"], "kongu"),
    (["mahalingam"], "mahalingam"),
    (["kumaraguru", "kct"], "kumaraguru"),
    (["sri eshwar"], "sri eshwar"),
    (["karpagam"], "karpagam"),
    (["sri ramakrishna", "srec"], "sri ramakrishna"),
    (["gct", "government college of technology"], "government college of technology"),
    (["kgisl"], "kgisl"),
    (["hindusthan", "hicet"], "hindusthan"),
]


def detect_college_keywords(text: str) -> list[str]:
    """Detect all specific colleges named in the user query using an alias map."""
    cleaned = text.lower()
    matched: list[str] = []
    for aliases, search_term in COLLEGE_ALIASES:
        if any(re.search(rf"\b{re.escape(a)}\b", cleaned) for a in aliases):
            if search_term not in matched:
                matched.append(search_term)
    return matched


def detect_college_keyword(text: str) -> str | None:
    """Detect if a specific college is named in the user query using an alias map."""
    kws = detect_college_keywords(text)
    return kws[0] if kws else None


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


def validate_numeric_facts(
    generated_answer: str,
    context_str: str,
    system_calculated_cutoff: float | None = None,
) -> bool:
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

    if system_calculated_cutoff is not None:
        allowed_constants.add(str(system_calculated_cutoff))
        # Also add integer version if it's a whole number (e.g. 180.0 -> "180")
        if system_calculated_cutoff.is_integer():
            allowed_constants.add(str(int(system_calculated_cutoff)))

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
    db: AsyncSession,
    query_text: str,
    session_key: str | None = None,
    system_calculated_cutoff: float | None = None,
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
            # Remove python-appended disclaimers from history so the LLM doesn't learn to repeat them
            if history_str:
                history_str = re.sub(
                    r"\n\n⚠️ _Some numbers may not match official records[^_]*_",
                    "",
                    history_str,
                )
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
            # Still persist conversation turns so follow-ups have context
            if conversation is not None:
                try:
                    answer_cached, _ = cached
                    await append_turn(db, conversation, "user", query_text)
                    await append_turn(db, conversation, "assistant", answer_cached)
                    await db.commit()
                except Exception:
                    pass
            return cached

    # 1c. LangGraph Multi-Turn Agentic RAG Execution
    if settings.USE_LANGGRAPH:
        from api.services.agent.graph import counselor_graph

        agent_state = {
            "session_key": session_key or "web:anonymous",
            "raw_message": query_text,
            "history_text": history_str,
        }
        res = await counselor_graph.ainvoke(
            agent_state, config={"configurable": {"db": db}}
        )
        answer = res.get("response_text", "")
        agent_sources = res.get("sources", [])

        if not history_str:
            set_cached_rag_response(query_text, answer, agent_sources)

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

        logger.info("rag_query_handled_via_langgraph", source_count=len(agent_sources))
        return answer, agent_sources
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
    college_kws = detect_college_keywords(retrieval_query)
    for kw in detect_college_keywords(query_text):
        if kw not in college_kws:
            college_kws.append(kw)

    rows: List[Tuple[DocumentChunk, str]] = []
    if len(college_kws) > 1:
        logger.info("balanced_pgvector_by_colleges", college_keywords=college_kws)
        per_college_k = max(4, settings.RAG_TOP_K // len(college_kws))
        seen_ids: set[int] = set()
        for kw in college_kws:
            col_filter = Document.document_ref.ilike(
                f"%{kw}%"
            ) | DocumentChunk.text_content.ilike(f"%{kw}%")
            col_stmt = (
                select(DocumentChunk, Document.document_ref)
                .join(Document, DocumentChunk.document_id == Document.id)
                .where(col_filter)
                .order_by(DocumentChunk.embedding.cosine_distance(query_vector))
                .limit(per_college_k)
            )
            col_res = await db.execute(col_stmt)
            for ch, d_ref in col_res.all():
                if ch.id not in seen_ids:
                    seen_ids.add(ch.id)
                    rows.append((ch, d_ref))
    else:
        stmt = select(DocumentChunk, Document.document_ref).join(
            Document, DocumentChunk.document_id == Document.id
        )
        if college_kws:
            kw = college_kws[0]
            stmt = stmt.where(
                Document.document_ref.ilike(f"%{kw}%")
                | DocumentChunk.text_content.ilike(f"%{kw}%")
            )

        stmt = stmt.order_by(
            DocumentChunk.embedding.cosine_distance(query_vector)
        ).limit(settings.RAG_TOP_K)

        result = await db.execute(stmt)
        rows = [(row[0], row[1]) for row in result.all()]

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

        college_display = (
            " & ".join(kw.title() for kw in college_kws)
            if college_kws
            else "that college"
        )
        return (
            f"Sorry, I don't have the official documents or details for {college_display} "
            "in the database yet. Please provide the link in the Admin portal web scraper, "
            "and I will get back to you with the info!",
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
    llm_question = query_text
    if system_calculated_cutoff is not None:
        llm_question = (
            f"[System Calculated Cutoff: {system_calculated_cutoff} / 200] {query_text}"
        )

    prompt = SYSTEM_PROMPT_TEMPLATE.format(
        history=(
            HISTORY_BLOCK_TEMPLATE.format(history=history_str) if history_str else ""
        ),
        context=context_str,
        question=llm_question,
    )

    logger.debug("requesting_llm_generation")
    answer = await generate_response_from_llm(prompt)

    # 7. Execute Numeric Fact Verification Guardrail
    is_factually_grounded = validate_numeric_facts(
        answer, context_str, system_calculated_cutoff
    )
    if not is_factually_grounded:
        logger.warning(
            "numeric_validation_failed_flagged_for_review",
            query=query_text,
            session_key=session_key,
        )
        answer += (
            "\n\n⚠️ _Some numbers may not match official records. "
            "Please verify with the college website or TNEA portal._"
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
