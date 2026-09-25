"""Personalized TNEA Choice-List Recommendation Generator."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.logging import get_logger
from api.models.cutoff import TNEACutoff

logger = get_logger(__name__)


def _matches_preferences(
    row: TNEACutoff,
    branches: Optional[List[str]],
    colleges: Optional[List[str]],
) -> int:
    """Score cutoff row based on student preferences (higher = better match)."""
    score = 0
    if branches:
        for b in branches:
            if (
                b.lower() in row.branch_name.lower()
                or b.lower() == row.branch_code.lower()
            ):
                score += 2
    if colleges:
        for c in colleges:
            if c.lower() in row.college_name.lower() or c == row.college_code:
                score += 2
    return score


def _bucket_choices(
    rows: List[TNEACutoff],
    cutoff: float,
    branches: Optional[List[str]],
    colleges: Optional[List[str]],
) -> tuple[List[TNEACutoff], List[TNEACutoff], List[TNEACutoff]]:
    """Partition cutoffs into Reach, Target, and Safe buckets."""
    reach: List[TNEACutoff] = []
    target: List[TNEACutoff] = []
    safe: List[TNEACutoff] = []

    # Sort rows by preference match descending, then by cutoff closeness
    sorted_rows = sorted(
        rows,
        key=lambda r: (
            _matches_preferences(r, branches, colleges),
            -abs(r.cutoff_mark - cutoff),
        ),
        reverse=True,
    )

    seen_pairs: set[tuple[str, str]] = set()

    for r in sorted_rows:
        pair = (r.college_code, r.branch_code or r.branch_name)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)

        diff = r.cutoff_mark - cutoff
        if 0.0 < diff <= 3.0 and len(reach) < 3:
            reach.append(r)
        elif -3.5 <= diff <= 0.0 and len(target) < 5:
            target.append(r)
        elif -12.0 <= diff < -3.5 and len(safe) < 4:
            safe.append(r)

    return reach, target, safe


def _render_choice_items(
    items: List[TNEACutoff], start_no: int, badge: str
) -> tuple[List[str], int]:
    lines: List[str] = []
    curr = start_no
    for item in items:
        b_code = f" [{item.branch_code}]" if item.branch_code else ""
        lines.append(
            f"{curr}. {badge} *[{item.college_code}] {item.college_name}*\n"
            f"   • *Branch*: {item.branch_name}{b_code}\n"
            f"   • *Closing Cutoff*: *{item.cutoff_mark:g}*"
        )
        curr += 1
    return lines, curr


async def generate_tnea_choice_list(
    db: AsyncSession,
    cutoff: float,
    community: str = "BC",
    preferred_branches: Optional[List[str]] = None,
    preferred_colleges: Optional[List[str]] = None,
) -> str:
    """Generate a personalized 10-choice TNEA draft order table."""
    comm = community.upper() if community else "BC"

    stmt = (
        select(TNEACutoff)
        .where(
            TNEACutoff.community == comm,
            TNEACutoff.cutoff_mark >= max(cutoff - 15.0, 77.5),
            TNEACutoff.cutoff_mark <= cutoff + 3.0,
        )
        .order_by(TNEACutoff.cutoff_mark.desc())
    )
    res = await db.execute(stmt)
    records = list(res.scalars().all())

    if not records:
        # Fallback query without community restriction
        stmt_fallback = (
            select(TNEACutoff)
            .where(
                TNEACutoff.cutoff_mark >= max(cutoff - 15.0, 77.5),
                TNEACutoff.cutoff_mark <= cutoff + 3.0,
            )
            .order_by(TNEACutoff.cutoff_mark.desc())
            .limit(30)
        )
        res_fb = await db.execute(stmt_fallback)
        records = list(res_fb.scalars().all())

    reach, target, safe = _bucket_choices(
        records, cutoff, preferred_branches, preferred_colleges
    )

    header = (
        "📋 *Personalized TNEA Choice Filling Order Draft*\n\n"
        f"• *Candidate Cutoff*: *{cutoff:g} / 200.0*\n"
        f"• *Community Quota*: *{comm}*\n"
        "• *Strategy*: 3-Tier Draft (Dream -> Target -> Safe)\n"
        "────────────────────────"
    )

    choice_no = 1
    body_parts: List[str] = [header]

    if reach:
        body_parts.append("\n🚀 *Aspirational / Dream Choices (Upward Movement):*")
        reach_lines, choice_no = _render_choice_items(reach, choice_no, "🔴")
        body_parts.extend(reach_lines)

    if target:
        body_parts.append("\n🎯 *Target Choices (High Probability Match):*")
        target_lines, choice_no = _render_choice_items(target, choice_no, "🟡")
        body_parts.extend(target_lines)

    if safe:
        body_parts.append("\n🟢 *Safe Backup Choices (Guaranteed Seat):*")
        safe_lines, choice_no = _render_choice_items(safe, choice_no, "🟢")
        body_parts.extend(safe_lines)

    footer = (
        "\n────────────────────────\n"
        "💡 *Key TNEA Choice Filling Rule (tneaonline.org):*\n"
        "Always keep Dream/Aspirational choices on top. If allotted a Target "
        "choice, choose *'Accept with Upward Movement'* so you can upgrade!"
    )
    body_parts.append(footer)

    logger.info(
        "choice_list_generated",
        cutoff=cutoff,
        community=comm,
        reach_count=len(reach),
        target_count=len(target),
        safe_count=len(safe),
    )
    return "\n".join(body_parts)


async def generate_choice_sheet_file(
    db: AsyncSession,
    cutoff: float,
    community: str = "BC",
    preferred_branches: Optional[List[str]] = None,
    preferred_colleges: Optional[List[str]] = None,
    district: Optional[str] = None,
    session_key: str = "",
) -> tuple[str, str]:
    """Build structured choices and export a downloadable PDF choice sheet.

    Returns:
        tuple[str, str]: (filepath, public_url)
    """
    from api.services.pdf_generator import generate_tnea_choice_sheet_pdf

    comm = community.upper() if community else "BC"
    stmt = select(TNEACutoff).where(
        TNEACutoff.community == comm,
        TNEACutoff.cutoff_mark >= max(cutoff - 15.0, 77.5),
        TNEACutoff.cutoff_mark <= cutoff + 3.0,
    )
    if district:
        from sqlalchemy import or_

        from api.services.cutoff_service import DISTRICT_KEYWORD_PATTERNS

        d_lower = district.strip().lower()
        d_patterns = DISTRICT_KEYWORD_PATTERNS.get(d_lower, [district])
        stmt = stmt.where(
            or_(*(TNEACutoff.college_name.ilike(f"%{p}%") for p in d_patterns))
        )

    stmt = stmt.order_by(TNEACutoff.cutoff_mark.desc())
    res = await db.execute(stmt)
    records = list(res.scalars().all())

    if not records:
        stmt_fallback = (
            select(TNEACutoff)
            .where(
                TNEACutoff.cutoff_mark >= max(cutoff - 15.0, 77.5),
                TNEACutoff.cutoff_mark <= cutoff + 3.0,
            )
            .order_by(TNEACutoff.cutoff_mark.desc())
            .limit(30)
        )
        res_fb = await db.execute(stmt_fallback)
        records = list(res_fb.scalars().all())

    reach, target, safe = _bucket_choices(
        records, cutoff, preferred_branches, preferred_colleges
    )

    choices_data = []
    for r in reach:
        choices_data.append(
            {
                "college_code": r.college_code,
                "college_name": r.college_name,
                "branch_name": r.branch_name,
                "cutoff_mark": r.cutoff_mark,
                "tier": "Ambitious",
            }
        )
    for r in target:
        choices_data.append(
            {
                "college_code": r.college_code,
                "college_name": r.college_name,
                "branch_name": r.branch_name,
                "cutoff_mark": r.cutoff_mark,
                "tier": "Target",
            }
        )
    for r in safe:
        choices_data.append(
            {
                "college_code": r.college_code,
                "college_name": r.college_name,
                "branch_name": r.branch_name,
                "cutoff_mark": r.cutoff_mark,
                "tier": "Safe",
            }
        )

    return generate_tnea_choice_sheet_pdf(
        cutoff=cutoff,
        community=comm,
        choices=choices_data,
        session_key=session_key,
    )
