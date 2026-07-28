from typing import List, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
from api.core.logging import get_logger
from api.models import Document, DocumentChunk
from api.services.embedding_service import get_embeddings
from api.services.llm_service import generate_response_from_llm

logger = get_logger(__name__)

SYSTEM_PROMPT_TEMPLATE = """You are Coligo, an AI-powered student admission counseling assistant for the Department of Technical Education, Government of Rajasthan.
Your goal is to answer the user's questions about admissions, fees, cutoffs, scholarships, and colleges based ONLY on the context snippets provided below.

Rules:
1. Ground your answers strictly in the provided Context.
2. If the context does not contain enough information to answer the question, politely state that you do not know the answer. Do NOT make up or extrapolate facts outside the context.
3. Be professional, polite, concise, and helpful.

Context:
{context}

Question:
{question}

Answer:"""


async def handle_rag_query(db: AsyncSession, query_text: str) -> Tuple[str, List[str]]:
    """Execute the full RAG pipeline for a user chat query.

    1. Embeds query text.
    2. Performs pgvector cosine distance search.
    3. Formats prompt with retrieved context.
    4. Generates reply from Gemini LLM.

    Returns:
        Tuple of (generated_answer, list_of_source_document_refs)
    """
    logger.info("handling_rag_query_start", query_text=query_text)

    # 1. Fetch query vector embedding
    logger.debug("embedding_query_text")
    query_embeddings = await get_embeddings([query_text])
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

    # 4. Construct prompt and request answer from LLM
    prompt = SYSTEM_PROMPT_TEMPLATE.format(
        context=context_str,
        question=query_text,
    )

    logger.debug("requesting_llm_generation")
    answer = await generate_response_from_llm(prompt)

    logger.info("rag_query_handled_successfully", source_count=len(sources))
    return answer, sources
