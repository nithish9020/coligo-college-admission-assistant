import os
from typing import Any, List, Optional

from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.logging import get_logger
from api.models.cutoff import TNEACutoff
from api.models.document import Document
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
    college: Optional[str] = None,
    branch: Optional[str] = None,
    community: Optional[str] = None,
    district: Optional[str] = None,
) -> str:
    """Fetch verified TNEA cutoffs from the database."""
    try:
        from api.services.rag_service import detect_college_keyword

        search_col = detect_college_keyword(college) if college else None
        records = await get_cutoff_records(
            db,
            college=search_col or college,
            branch=branch,
            community=community,
            district=district,
            limit=20,
        )
        if not records:
            target_str = f"'{college}' " if college else ""
            dist_str = f"in {district} " if district else ""
            return (
                f"No exact cutoff record found for {target_str}{dist_str}"
                f"(Branch: {branch or 'All'}, Community: {community or 'All'})."
            )

        target_label = (
            college.upper()
            if college
            else (f"{district.title()} District" if district else "Top Colleges")
        )
        comm_label = f"[{community.upper()}]" if community else "[All Communities]"
        lines = [f"Official TNEA Cutoffs for {target_label} {comm_label}:"]
        for r in records:
            lines.append(
                f"• {r.college_name} | {r.branch_name} | "
                f"{r.community}: {r.cutoff_mark:g}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error("tool_query_cutoffs_failed", error=str(e))
        return f"Error retrieving cutoffs: {str(e)}"


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
            lines.append(f"\n*{col_name}*")
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
    district: Optional[str] = None,
) -> str:
    """Generate 3-tier choice filling list."""
    try:
        recs = await generate_choice_filling_recommendations(
            db,
            cutoff=cutoff,
            community=community,
            branches=preferred_branches,
            district=district,
        )
        dist_label = f" in {district.title()}" if district else ""
        lines = [
            f"TNEA 3-Tier Choice Filling List{dist_label} ({cutoff:g} / 200.0 | "
            f"{community.upper()}):",
            "\nAMBITIOUS (Reach Options):",
        ]
        for it in recs["ambitious"][:5]:
            d = it["difference"]
            diff = f"+{d:g}" if d > 0 else f"{d:g}"
            lines.append(
                f"• {it['college_name']} | {it['branch_name']} | "
                f"Cutoff: {it['cutoff_mark']:g} ({diff})"
            )

        lines.append("\nTARGET (Realistic Options):")
        for it in recs["target"][:6]:
            lines.append(
                f"• {it['college_name']} | {it['branch_name']} | "
                f"Cutoff: {it['cutoff_mark']:g} ({it['difference']:g})"
            )

        lines.append("\nSAFE (Backup Options):")
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
    """Hybrid search brochure documents for fees, hostels, and rules with FlashRank."""
    try:
        from api.services.hybrid_search import hybrid_search_chunks

        query_embeddings = await get_embeddings([query])
        query_vector = query_embeddings[0]

        chunks = await hybrid_search_chunks(
            db=db,
            query=query,
            query_vector=query_vector,
            college=college,
            top_k=4,
        )
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


def create_agent_tools(  # noqa: C901
    db: AsyncSession, session_key: str = ""
) -> list[Any]:
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
        college: Optional[str] = None,
        branch: Optional[str] = None,
        community: Optional[str] = None,
        district: Optional[str] = None,
    ) -> str:
        """Query official verified TNEA closing cutoffs (out of 200).

        Args:
            college: Optional college name (e.g. SKCET, CIT, PSG, Bannari, Kongu).
            branch: Optional department (CSE, ECE, IT, AIDS, MECH).
            community: Optional reservation community (OC, BC, BCM, MBC, SC, ST).
            district: Optional district filter (e.g. Coimbatore, Chennai, Erode).
        """
        logger.info(
            "tool_invoked_query_college_cutoffs",
            college=college,
            branch=branch,
            community=community,
            district=district,
        )
        return await _query_cutoffs_impl(db, college, branch, community, district)

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
        district: Optional[str] = None,
    ) -> str:
        """Generate a 3-tier TNEA Choice Filling List based on student cutoff.

        Args:
            cutoff: Student's TNEA cutoff score out of 200.0.
            community: Student's community: 'OC', 'BC', 'BCM', 'MBC', 'SC', 'ST'.
            preferred_branches: Optional desired branches (e.g. ['CSE', 'ECE']).
            district: Optional regional filter (e.g. 'Coimbatore', 'Erode').
        """
        logger.info(
            "tool_invoked_choice_recommendations",
            cutoff=cutoff,
            community=community,
            branches=preferred_branches,
            district=district,
        )
        return await _choice_recs_impl(
            db, cutoff, community, preferred_branches, district
        )

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

    @tool
    def query_college_placements(college: str, branch: Optional[str] = None) -> str:
        """Query placement stats, highest CTC, average CTC, and top recruiters.

        Args:
            college: College name or alias (e.g. SKCET, PSG, CIT, KCT, Bannari).
            branch: Optional department to focus on (e.g. CSE, ECE, Mech).
        """
        logger.info("tool_invoked_query_placements", college=college, branch=branch)
        from api.services.placement_service import format_placement_card

        return format_placement_card(college, branch)

    @tool
    def predict_tnea_rank_tool(cutoff: float, community: str = "BC") -> str:
        """Predict expected TNEA State Overall Rank and Counselling Round.

        Args:
            cutoff: Student's TNEA cutoff score out of 200.0.
            community: Student's community (OC, BC, BCM, MBC, SC, ST).
        """
        logger.info("tool_invoked_predict_rank", cutoff=cutoff, community=community)
        from api.services.rank_predictor import format_rank_prediction_message

        return format_rank_prediction_message(cutoff, community)

    @tool
    async def download_choice_sheet_pdf_tool(
        cutoff: float,
        community: str = "BC",
        preferred_branches: Optional[List[str]] = None,
        district: Optional[str] = None,
    ) -> str:
        """Generate and deliver an official TNEA Choice Filling Sheet PDF.

        Args:
            cutoff: Student's TNEA cutoff score out of 200.0.
            community: Student's community (OC, BC, BCM, MBC, SC, ST).
            preferred_branches: Optional desired branches (e.g. ['CSE', 'ECE']).
            district: Optional district filter (e.g. 'Coimbatore', 'Chennai').
        """
        logger.info(
            "tool_invoked_generate_pdf",
            cutoff=cutoff,
            community=community,
            branches=preferred_branches,
            district=district,
        )
        from api.services.choice_list_service import generate_choice_sheet_file

        try:
            _, pdf_url = await generate_choice_sheet_file(
                db=db,
                cutoff=cutoff,
                community=community,
                preferred_branches=preferred_branches,
                district=district,
                session_key=session_key,
            )
            return (
                f"Your official TNEA Choice Sheet PDF has been generated!\n"
                f"Download link: {pdf_url}\n"
                f"Cutoff: {cutoff:g} | Community: {community.upper()}\n"
                f"Please review the choices and lock them on tneaonline.org."
            )
        except Exception as e:
            logger.error("tool_generate_pdf_failed", error=str(e))
            return f"Error generating PDF choice sheet: {str(e)}"

    @tool
    async def simulate_upward_movement_tool(
        allotted_college: str,
        allotted_branch: str,
        cutoff: float,
        community: str = "BC",
        target_branches: Optional[List[str]] = None,
    ) -> str:
        """Simulate TNEA Upward Movement outcomes, probabilities, and best option.

        Call this when a student asks about upward movement, tentative allotment,
        or whether to Accept & Join vs Accept & Upward.

        Args:
            allotted_college: Tentatively allotted college (e.g. 'SKCET', 'PSG').
            allotted_branch: Tentatively allotted department (e.g. 'MECH', 'ECE').
            cutoff: Candidate's cutoff mark (out of 200).
            community: Candidate's reservation category (OC, BC, BCM, MBC, SC, ST).
            target_branches: Optional higher preference branches (e.g. ['CSE', 'IT']).
        """
        logger.info(
            "tool_invoked_upward_simulation",
            college=allotted_college,
            branch=allotted_branch,
            cutoff=cutoff,
            community=community,
        )
        from api.services.upward_movement_simulator import (
            format_upward_movement_text,
            simulate_upward_movement,
        )

        try:
            sim_data = await simulate_upward_movement(
                db=db,
                allotted_college=allotted_college,
                allotted_branch=allotted_branch,
                student_cutoff=cutoff,
                community=community,
                target_branches=target_branches,
            )
            return format_upward_movement_text(sim_data)
        except Exception as e:
            logger.error("tool_upward_simulation_failed", error=str(e))
            return f"Error simulating upward movement: {str(e)}"

    return [
        list_available_colleges,
        query_college_cutoffs,
        compare_colleges_cutoffs,
        get_choice_filling_recommendations_tool,
        search_admission_brochures,
        calculate_cutoff_from_marks,
        query_college_placements,
        predict_tnea_rank_tool,
        download_choice_sheet_pdf_tool,
        simulate_upward_movement_tool,
    ]
