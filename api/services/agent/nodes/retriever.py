from typing import Any, List, Tuple

from langchain_core.runnables import RunnableConfig
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
from api.core.logging import get_logger
from api.models.document import Document, DocumentChunk
from api.services.agent.state import AgentState
from api.services.embedding_service import get_embeddings
from api.services.query_rewriter import condense_question
from api.services.rag_service import (
    detect_college_keywords,
    normalize_query,
    reorder_chunks_lost_in_middle,
)

logger = get_logger(__name__)


async def _fetch_college_chunks(
    db: AsyncSession, query_vector: list[float], colleges: list[str]
) -> List[Tuple[DocumentChunk, str]]:
    """Fetch pgvector chunks with balanced allocation for multi-college queries."""
    if len(colleges) > 1:
        per_college_k = max(4, settings.RAG_TOP_K // len(colleges))
        seen_ids: set[int] = set()
        multi_rows: List[Tuple[DocumentChunk, str]] = []
        for kw in colleges:
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
                    multi_rows.append((ch, d_ref))
        return multi_rows

    stmt = select(DocumentChunk, Document.document_ref).join(
        Document, DocumentChunk.document_id == Document.id
    )
    if colleges:
        kw = colleges[0]
        stmt = stmt.where(
            Document.document_ref.ilike(f"%{kw}%")
            | DocumentChunk.text_content.ilike(f"%{kw}%")
        )

    stmt = stmt.order_by(DocumentChunk.embedding.cosine_distance(query_vector)).limit(
        max(settings.RAG_TOP_K * 2, 8)
    )

    result = await db.execute(stmt)
    chunks = [(row[0], row[1]) for row in result.all()]
    if settings.ENABLE_RERANKING and chunks:
        from api.services.hybrid_search import rerank_with_flashrank

        target_query = colleges[0] if colleges else "engineering college admissions"
        chunks = rerank_with_flashrank(target_query, chunks, top_k=settings.RAG_TOP_K)
    return chunks[: settings.RAG_TOP_K]


async def _fetch_structured_context(
    db: AsyncSession,
    intent: str,
    cutoff: float | None,
    community: str | None,
    branches: list[str] | None,
    colleges: list[str] | None,
) -> dict[str, Any] | None:
    """Fetch verified SQL cutoff or choice filling data for factual grounding."""
    from api.services.cutoff_service import (
        generate_choice_filling_recommendations,
        get_cutoff_records,
    )
    from api.services.message_formatter import calculate_admission_chance

    # 1. Choice filling / recommendations when cutoff is known
    if (intent == "choice_filling" or not colleges) and cutoff is not None:
        recs = await generate_choice_filling_recommendations(
            db,
            cutoff=cutoff,
            community=community or "OC",
            branches=branches,
            colleges=colleges or None,
        )
        comm_label = community or "OC"
        lines = [
            "=== OFFICIAL TNEA 3-TIER CHOICE FILLING PREFERENCE DATA ===",
            f"Candidate Cutoff: {cutoff:g} / 200.0 | Community: {comm_label}",
            "\n🌟 AMBITIOUS / DREAM CHOICES (Reach options):",
        ]
        for it in recs["ambitious"][:5]:
            d = it["difference"]
            diff = f"+{d:g}" if d > 0 else f"{d:g}"
            c_name = it["college_name"]
            b_name = it["branch_name"]
            c_mark = it["cutoff_mark"]
            lines.append(f"• {c_name} | {b_name} | Cutoff: {c_mark} ({diff})")

        lines.append("\n🎯 TARGET / REALISTIC CHOICES (High probability):")
        for it in recs["target"][:6]:
            c_name = it["college_name"]
            b_name = it["branch_name"]
            c_mark = it["cutoff_mark"]
            d = it["difference"]
            lines.append(f"• {c_name} | {b_name} | Cutoff: {c_mark} ({d:g})")

        lines.append("\n🛡️ SAFE / BACKUP CHOICES (Safe options):")
        for it in recs["safe"][:5]:
            c_name = it["college_name"]
            b_name = it["branch_name"]
            c_mark = it["cutoff_mark"]
            d = it["difference"]
            lines.append(f"• {c_name} | {b_name} | Cutoff: {c_mark} ({d:g})")

        return {
            "chunk_index": 0,
            "text_content": "\n".join(lines),
            "document_ref": "TNEA Official Cutoffs Database",
        }

    # 2. Specific College Cutoffs (with or without community)
    if colleges:
        target_comm = community if (community and community != "ALL") else None
        sql_records = await get_cutoff_records(
            db,
            college=colleges[0],
            branch=branches[0] if branches else None,
            community=target_comm,
            limit=12,
        )
        if sql_records:
            col_name = colleges[0].upper()
            comm_tag = f"({community})" if community else "(Major Communities)"
            header = f"=== VERIFIED CUTOFFS FOR {col_name} {comm_tag} ==="
            lines = [header]
            if cutoff is not None:
                lines.append(f"Candidate Cutoff: {cutoff:g} / 200.0\n")
            for r in sql_records:
                chance_str = ""
                if cutoff is not None:
                    badge, _ = calculate_admission_chance(cutoff, r.cutoff_mark)
                    chance_str = f" [{badge}]"
                lines.append(
                    f"• {r.college_name} | {r.branch_name} | "
                    f"{r.community}: {r.cutoff_mark}{chance_str}"
                )
            return {
                "chunk_index": 0,
                "text_content": "\n".join(lines),
                "document_ref": f"Official {col_name} Cutoff Table",
            }

    return None


async def retriever_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    """Retrieve pgvector chunks for student query with college filters."""
    db: AsyncSession = config["configurable"]["db"]
    raw_message = state.get("raw_message", "")
    history_str = state.get("history_text", "")
    intent = state.get("intent", "cutoff_query")
    cutoff = state.get("calculated_cutoff")
    community = state.get("community")
    branches = state.get("branches")

    # 1. Condense follow-up questions
    retrieval_query = raw_message
    if history_str and settings.ENABLE_QUERY_REWRITING:
        retrieval_query = await condense_question(history_str, raw_message)

    normalized_query = normalize_query(retrieval_query)

    # 2. Embed query
    query_embeddings = await get_embeddings([normalized_query])
    query_vector = query_embeddings[0]

    # 3. Detect colleges to filter
    colleges = list(state.get("colleges") or [])
    for kw in detect_college_keywords(retrieval_query):
        if kw not in colleges:
            colleges.append(kw)

    # 4. Fetch chunks with balanced allocation
    rows = await _fetch_college_chunks(db, query_vector, colleges)

    # 5. Apply Lost-in-the-Middle chunk reordering
    reordered_rows = reorder_chunks_lost_in_middle(rows)

    chunks_data: list[dict[str, Any]] = []
    sources: list[str] = []

    # 6. Inject verified SQL cutoff or choice filling data at index 0 if available
    structured_chunk = await _fetch_structured_context(
        db, intent, cutoff, community, branches, colleges
    )
    if structured_chunk:
        chunks_data.append(structured_chunk)
        sources.append(structured_chunk["document_ref"])

    for chunk, doc_ref in reordered_rows:
        chunks_data.append(
            {
                "chunk_index": chunk.chunk_index,
                "text_content": chunk.text_content,
                "document_ref": doc_ref,
            }
        )
        if doc_ref not in sources:
            sources.append(doc_ref)

    logger.info(
        "retriever_node_completed",
        retrieved_chunks=len(chunks_data),
        sources=sources,
    )

    return {
        "rewritten_query": retrieval_query,
        "colleges": colleges,
        "retrieved_chunks": chunks_data,
        "sources": sources,
    }
