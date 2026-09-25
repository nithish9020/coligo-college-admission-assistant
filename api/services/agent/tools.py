import os
from typing import Any, List, Optional

from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.logging import get_logger
from api.models.cutoff import TNEACutoff
from api.models.document import Document, DocumentChunk
from api.services.cutoff_service import (
    generate_choice_filling_recommendations,
    get_cutoff_records,
)
from api.services.embedding_service import get_embeddings

logger = get_logger(__name__)


async def _list_colleges_impl(db: AsyncSession) -> str:
    """Query distinct documents and cutoffs to list verified colleges."""
    try:
        doc_stmt = select(Document.document_ref)
        doc_res = await db.execute(doc_stmt)
        doc_refs = [r[0] for r in doc_res.all()]

        cutoff_stmt = select(
            TNEACutoff.college_name, TNEACutoff.college_code
        ).distinct()
        cutoff_res = await db.execute(cutoff_stmt)
        cutoff_colleges = cutoff_res.all()

        lines = ["Verified Colleges with TNEA Data in Coligo:"]
        seen_names = set()

        for col_name, col_code in cutoff_colleges:
            clean_name = col_name.strip()
            if clean_name and clean_name not in seen_names:
                seen_names.add(clean_name)
                code_tag = f" (Code: {col_code})" if col_code else ""
                lines.append(f"• {clean_name}{code_tag} — Cutoffs & Intake")

        for ref in doc_refs:
            base = os.path.basename(ref).replace("_", " ").replace("-", " ")
            for ext in (".pdf", ".txt"):
                base = base.replace(ext, "")
            if "cutoffs" not in base.lower() and "scraped" not in base.lower():
                title = base.title()
                if title not in seen_names:
                    seen_names.add(title)
                    lines.append(f"• {title} — Official Brochure & Fees")

        if not seen_names:
            lines.append(
                "• Sri Krishna College of Engg & Tech (SKCET 2722)\n"
                "• PSG College of Technology (PSG 2006)\n"
                "• Coimbatore Institute of Technology (CIT 2007)\n"
                "• Bannari Amman Institute of Tech (BIT 2702)\n"
                "• Kongu Engineering College (KEC 2711)\n"
                "• Kumaraguru College of Tech (KCT 2712)"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error("tool_list_colleges_failed", error=str(e))
        return (
            "Available Colleges: SKCET 2722, PSG Tech 2006, CIT 2007, "
            "Bannari Amman 2702, Kongu KEC 2711, Kumaraguru KCT 2712."
        )


async def _query_cutoffs_impl(
    db: AsyncSession,
    college: str,
    branch: Optional[str] = None,
    community: Optional[str] = None,
) -> str:
    """Fetch verified TNEA cutoffs from the database."""
    try:
        from api.services.rag_service import detect_college_keyword

        search_col = detect_college_keyword(college) or college
        records = await get_cutoff_records(
            db,
            college=search_col,
            branch=branch,
            community=community,
            limit=15,
        )
        if not records:
            return (
                f"No exact cutoff record found for '{college}' (Branch: "
                f"{branch or 'All'}, Community: {community or 'All'})."
            )

        comm_label = f"[{community.upper()}]" if community else "[All Communities]"
        lines = [f"Official TNEA Cutoffs for {college.upper()} {comm_label}:"]
        for r in records:
            lines.append(
                f"• {r.college_name} | {r.branch_name} | "
                f"{r.community}: {r.cutoff_mark:g}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error("tool_query_cutoffs_failed", error=str(e))
        return f"Error retrieving cutoffs for {college}: {str(e)}"


async def _compare_colleges_impl(
    db: AsyncSession,
    colleges: list[str],
    branch: Optional[str] = None,
    community: Optional[str] = None,
) -> str:
    """Fetch verified TNEA cutoffs comparing two or more colleges."""
    try:
        from api.services.rag_service import detect_college_keyword

        search_colleges = [
            detect_college_keyword(c) or c for c in colleges if c and c.strip()
        ]
        records = await get_cutoff_records(
            db,
            colleges=search_colleges,
            branch=branch,
            community=community,
            limit=40,
        )
        if not records:
            return (
                f"No comparative cutoff records found for {', '.join(colleges)} "
                f"(Branch: {branch or 'All'}, Community: {community or 'All'})."
            )

        comm_label = f"[{community.upper()}]" if community else "[All Communities]"
        lines = [
            f"Official TNEA Cutoff Comparison for "
            f"{', '.join(c.upper() for c in colleges)} {comm_label}:"
        ]

        seen: set[tuple[str, str, str]] = set()
        by_college: dict[str, list[TNEACutoff]] = {}
        for r in records:
            key = (r.college_code, r.branch_name, r.community)
            if key not in seen:
                seen.add(key)
                by_college.setdefault(r.college_name, []).append(r)

        for col_name, recs in by_college.items():
            lines.append(f"\n🏛️ *{col_name}*")
            for r in recs[:6]:
                lines.append(
                    f"• *{r.branch_name}*: *{r.cutoff_mark:g}* ({r.community})"
                )
        return "\n".join(lines)
    except Exception as e:
        logger.error("tool_compare_colleges_failed", error=str(e))
        return f"Error comparing colleges: {str(e)}"


async def _choice_recs_impl(
    db: AsyncSession,
    cutoff: float,
    community: str,
    preferred_branches: Optional[List[str]],
) -> str:
    """Generate 3-tier choice filling list."""
    try:
        recs = await generate_choice_filling_recommendations(
            db,
            cutoff=cutoff,
            community=community,
            branches=preferred_branches,
        )
        lines = [
            f"TNEA 3-Tier Choice Filling List ({cutoff:g} / 200.0 | "
            f"{community.upper()}):",
            "\n🌟 AMBITIOUS (Reach Options):",
        ]
        for it in recs["ambitious"][:5]:
            d = it["difference"]
            diff = f"+{d:g}" if d > 0 else f"{d:g}"
            lines.append(
                f"• {it['college_name']} | {it['branch_name']} | "
                f"Cutoff: {it['cutoff_mark']:g} ({diff})"
            )

        lines.append("\n🎯 TARGET (Realistic Options):")
        for it in recs["target"][:6]:
            lines.append(
                f"• {it['college_name']} | {it['branch_name']} | "
                f"Cutoff: {it['cutoff_mark']:g} ({it['difference']:g})"
            )

        lines.append("\n🛡️ SAFE (Backup Options):")
        for it in recs["safe"][:5]:
            lines.append(
                f"• {it['college_name']} | {it['branch_name']} | "
                f"Cutoff: {it['cutoff_mark']:g} ({it['difference']:g})"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error("tool_choice_recommendations_failed", error=str(e))
        return f"Error generating choice recommendations: {str(e)}"


async def _search_brochures_impl(
    db: AsyncSession, query: str, college: Optional[str]
) -> str:
    """Vector search brochure documents for fees, hostels, and rules."""
    try:
        query_embeddings = await get_embeddings([query])
        query_vector = query_embeddings[0]

        stmt = select(DocumentChunk, Document.document_ref).join(
            Document, DocumentChunk.document_id == Document.id
        )
        if college:
            stmt = stmt.where(
                Document.document_ref.ilike(f"%{college}%")
                | DocumentChunk.text_content.ilike(f"%{college}%")
            )
        stmt = stmt.order_by(
            DocumentChunk.embedding.cosine_distance(query_vector)
        ).limit(4)

        result = await db.execute(stmt)
        chunks = result.all()
        if not chunks:
            return f"No brochure chunks found matching query '{query}'."

        parts = []
        for ch, ref in chunks:
            parts.append(f"--- Source: {ref} ---\n{ch.text_content.strip()[:1000]}")
        return "\n\n".join(parts)
    except Exception as e:
        logger.error("tool_search_brochures_failed", error=str(e))
        return f"Error searching brochures: {str(e)}"


def _calc_cutoff_impl(maths: float, physics: float, chemistry: float) -> str:
    """Calculate TNEA cutoff mark."""
    if any(m < 0 or m > 100 for m in (maths, physics, chemistry)):
        return "Marks must be between 0 and 100."
    total = maths + (physics / 2.0) + (chemistry / 2.0)
    return (
        f"TNEA Cutoff: {total:g} / 200.0\n"
        f"Maths: {maths:g} + Physics ({physics:g}/2 = {physics / 2:g}) + "
        f"Chemistry ({chemistry:g}/2 = {chemistry / 2:g}) = {total:g}"
    )


def create_agent_tools(db: AsyncSession, session_key: str = "") -> list[Any]:
    """Create and bind database-connected tools for the TNEA counselor agent."""

    @tool
    async def list_available_colleges() -> str:
        """List all colleges and departments available in the Coligo TNEA system.

        Call this when a student asks what colleges are available, asks for a list,
        or in Tanglish like 'unga kita endha college iruku'.
        """
        logger.info("tool_invoked_list_available_colleges")
        return await _list_colleges_impl(db)

    @tool
    async def query_college_cutoffs(
        college: str,
        branch: Optional[str] = None,
        community: Optional[str] = None,
    ) -> str:
        """Query official verified TNEA closing cutoffs (out of 200) for a college.

        Args:
            college: College name (e.g. SKCET, CIT, PSG, Bannari, Kongu).
            branch: Optional department (CSE, ECE, IT, AIDS, MECH).
            community: Optional reservation community (OC, BC, BCM, MBC, SC, ST).
        """
        logger.info(
            "tool_invoked_query_college_cutoffs",
            college=college,
            branch=branch,
            community=community,
        )
        return await _query_cutoffs_impl(db, college, branch, community)

    @tool
    async def compare_colleges_cutoffs(
        colleges: List[str],
        branch: Optional[str] = None,
        community: Optional[str] = None,
    ) -> str:
        """Compare official TNEA cutoffs between two or more colleges
        (e.g. ['PSG', 'SKCET']).

        Args:
            colleges: List of college names or aliases (e.g. ['PSG', 'SKCET', 'CIT']).
            branch: Optional department to compare (e.g. 'CSE', 'ECE').
            community: Optional reservation community (e.g. 'BC', 'OC').
        """
        logger.info(
            "tool_invoked_compare_colleges_cutoffs",
            colleges=colleges,
            branch=branch,
            community=community,
        )
        return await _compare_colleges_impl(db, colleges, branch, community)

    @tool
    async def get_choice_filling_recommendations_tool(
        cutoff: float,
        community: str = "OC",
        preferred_branches: Optional[List[str]] = None,
    ) -> str:
        """Generate a 3-tier TNEA Choice Filling List based on student cutoff.

        Args:
            cutoff: Student's TNEA cutoff score out of 200.0.
            community: Student's community: 'OC', 'BC', 'BCM', 'MBC', 'SC', 'ST'.
            preferred_branches: Optional desired branches (e.g. ['CSE', 'ECE']).
        """
        logger.info(
            "tool_invoked_choice_recommendations",
            cutoff=cutoff,
            community=community,
            branches=preferred_branches,
        )
        return await _choice_recs_impl(db, cutoff, community, preferred_branches)

    @tool
    async def search_admission_brochures(
        query: str, college: Optional[str] = None
    ) -> str:
        """Search official brochures for fees, hostel, placements, and campus rules.

        Args:
            query: Question regarding fees, hostel, placements, or facilities.
            college: Optional college name to filter by (e.g. 'SKCET').
        """
        logger.info("tool_invoked_search_brochures", query=query, college=college)
        return await _search_brochures_impl(db, query, college)

    @tool
    def calculate_cutoff_from_marks(
        maths: float, physics: float, chemistry: float
    ) -> str:
        """Calculate official TNEA cutoff mark from Maths, Physics, Chemistry.

        Args:
            maths: Maths mark (0 to 100).
            physics: Physics mark (0 to 100).
            chemistry: Chemistry mark (0 to 100).
        """
        cutoff = round(maths + (physics / 2.0) + (chemistry / 2.0), 2)
        if session_key:
            from api.services.student_profile_service import (
                update_student_profile,
            )

            update_student_profile(
                session_key=session_key,
                cutoff=cutoff,
                maths=maths,
                physics=physics,
                chemistry=chemistry,
            )
        return _calc_cutoff_impl(maths, physics, chemistry)

    return [
        list_available_colleges,
        query_college_cutoffs,
        compare_colleges_cutoffs,
        get_choice_filling_recommendations_tool,
        search_admission_brochures,
        calculate_cutoff_from_marks,
    ]
