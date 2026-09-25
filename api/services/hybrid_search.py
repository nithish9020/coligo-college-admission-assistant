"""Hybrid vector + keyword search with FlashRank neural reranking for Coligo."""

import re
from typing import Any, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
from api.core.logging import get_logger
from api.models.document import Document, DocumentChunk

logger = get_logger(__name__)

_ranker_instance: Optional[Any] = None
_ranker_load_failed = False

STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "is",
    "are",
    "was",
    "were",
    "what",
    "which",
    "who",
    "when",
    "where",
    "how",
    "can",
    "i",
    "my",
    "me",
    "tell",
    "about",
    "give",
    "details",
}


def get_reranker() -> Optional[Any]:
    """Return a cached FlashRank Ranker instance, or None on failure."""
    global _ranker_instance, _ranker_load_failed
    if _ranker_load_failed or not settings.ENABLE_RERANKING:
        return None

    if _ranker_instance is not None:
        return _ranker_instance

    try:
        from flashrank import Ranker

        _ranker_instance = Ranker(
            model_name=settings.RERANKER_MODEL,
            cache_dir="/tmp/flashrank_cache",
        )
        logger.info("flashrank_ranker_initialized", model=settings.RERANKER_MODEL)
        return _ranker_instance
    except Exception as e:
        logger.warning("flashrank_init_failed", error=str(e))
        _ranker_load_failed = True
        return None


def extract_keywords(query: str) -> list[str]:
    """Extract significant keywords from user query for full-text filtering."""
    tokens = re.findall(r"\b[a-zA-Z0-9_\-]{3,}\b", query.lower())
    return [t for t in tokens if t not in STOPWORDS]


def rerank_with_flashrank(
    query: str,
    candidates: list[tuple[DocumentChunk, str]],
    top_k: int,
) -> list[tuple[DocumentChunk, str]]:
    """Rerank candidate passages with local neural cross-encoder."""
    if not candidates:
        return []

    ranker = get_reranker()
    if ranker is None:
        return candidates[:top_k]

    try:
        from flashrank import RerankRequest

        passages = [
            {"id": idx, "text": ch.text_content[:800]}
            for idx, (ch, _) in enumerate(candidates)
        ]
        rerank_req = RerankRequest(query=query, passages=passages)
        results = ranker.rerank(rerank_req)

        ordered: list[tuple[DocumentChunk, str]] = []
        for r in results:
            orig_idx = int(r["id"])
            if 0 <= orig_idx < len(candidates):
                ordered.append(candidates[orig_idx])

        logger.info(
            "flashrank_reranking_completed",
            candidates_in=len(candidates),
            top_k_out=min(len(ordered), top_k),
        )
        return ordered[:top_k]
    except Exception as e:
        logger.warning("flashrank_rerank_exception_fallback", error=str(e))
        return candidates[:top_k]


async def hybrid_search_chunks(
    db: AsyncSession,
    query: str,
    query_vector: list[float],
    college: Optional[str] = None,
    top_k: int = 4,
) -> list[tuple[DocumentChunk, str]]:
    """Execute hybrid search (vector cosine + keyword) with FlashRank reranking."""
    candidate_limit = max(top_k * 3, 10)

    # 1. Vector Search Query
    vec_stmt = select(DocumentChunk, Document.document_ref).join(
        Document, DocumentChunk.document_id == Document.id
    )
    if college:
        vec_stmt = vec_stmt.where(
            Document.document_ref.ilike(f"%{college}%")
            | DocumentChunk.text_content.ilike(f"%{college}%")
        )
    vec_stmt = vec_stmt.order_by(
        DocumentChunk.embedding.cosine_distance(query_vector)
    ).limit(candidate_limit)

    vec_res = await db.execute(vec_stmt)
    vector_rows = vec_res.all()

    # 2. Keyword Search Query
    keywords = extract_keywords(query)
    keyword_rows: list[Any] = []
    if settings.ENABLE_HYBRID_SEARCH and keywords:
        kw_conditions = [DocumentChunk.text_content.ilike(f"%{kw}%") for kw in keywords]
        kw_stmt = (
            select(DocumentChunk, Document.document_ref)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(or_(*kw_conditions))
        )
        if college:
            kw_stmt = kw_stmt.where(
                Document.document_ref.ilike(f"%{college}%")
                | DocumentChunk.text_content.ilike(f"%{college}%")
            )
        kw_stmt = kw_stmt.limit(candidate_limit)
        kw_res = await db.execute(kw_stmt)
        keyword_rows = list(kw_res.all())

    # 3. Reciprocal Rank Fusion (RRF)
    # RRF score = sum(1.0 / (60 + rank))
    scores: dict[int, float] = {}
    chunk_map: dict[int, tuple[DocumentChunk, str]] = {}

    for rank, (ch, ref) in enumerate(vector_rows):
        chunk_map[ch.id] = (ch, ref)
        scores[ch.id] = scores.get(ch.id, 0.0) + (1.0 / (60.0 + rank))

    for rank, (ch, ref) in enumerate(keyword_rows):
        chunk_map[ch.id] = (ch, ref)
        scores[ch.id] = scores.get(ch.id, 0.0) + (1.0 / (60.0 + rank))

    # Sort chunks by RRF score descending
    sorted_chunk_ids = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)
    fused_candidates = [chunk_map[cid] for cid in sorted_chunk_ids]

    logger.debug(
        "hybrid_search_fusion_done",
        vector_count=len(vector_rows),
        keyword_count=len(keyword_rows),
        fused_total=len(fused_candidates),
    )

    # 4. Neural Cross-Encoder Reranking
    return rerank_with_flashrank(query, fused_candidates, top_k=top_k)
