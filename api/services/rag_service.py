from typing import List, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
from api.core.logging import get_logger
from api.models import Document, DocumentChunk
from api.services.conversation_service import (
    append_turn,
    format_history,
    get_or_create_conversation,
    get_recent_turns,
)
from api.services.embedding_service import get_embeddings
from api.services.llm_service import generate_response_from_llm
from api.services.query_rewriter import condense_question

logger = get_logger(__name__)

SYSTEM_PROMPT_TEMPLATE = """You are Coligo, an AI-powered student admission \
counselling assistant for Tamil Nadu Engineering Admissions (TNEA), helping \
students with engineering admissions in Tamil Nadu.
Your goal is to answer the user's questions about TNEA counselling, admissions, \
fees, cutoff marks, cutoff ranks, branches, and colleges based ONLY on the \
context snippets provided below.

Rules:
1. Ground your answers strictly in the provided Context.
2. If the context does not contain enough information to answer the question, \
politely state that you do not know the answer. Do NOT make up or extrapolate \
facts outside the context.
3. TNEA cutoff marks are out of 200, computed as Mathematics/2 + Physics/4 + \
Chemistry/4. Cutoff ranks are TNEA general ranks, where a numerically lower \
rank is better. Never confuse a cutoff mark with a cutoff rank.
4. Cutoffs differ by community (OC, BC, BCM, MBC, SC, SCA, ST). If the user \
has not stated their community, either answer for all communities present in \
the context or ask which community applies.
5. Cutoffs are historical and shift each year. Present them as guidance from \
the stated year, not as a guarantee of admission.
6. Use the Conversation so far only to understand what the user is referring \
to (pronouns, follow-ups, details they already gave such as their community or \
marks). Every fact in your answer must still come from the Context.
7. Do not repeat an earlier answer verbatim. Answer the current question.
8. Be professional, polite, concise, and helpful.
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

    # 2. Condense a follow-up ("what about ECE?") into a standalone question,
    # otherwise retrieval embeds the bare phrase and finds the wrong chunks.
    retrieval_query = query_text
    if history_str and settings.ENABLE_QUERY_REWRITING:
        retrieval_query = await condense_question(history_str, query_text)

    # 3. Fetch query vector embedding
    logger.debug("embedding_query_text")
    query_embeddings = await get_embeddings([retrieval_query])
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
