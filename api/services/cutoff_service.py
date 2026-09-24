import os
import re
from typing import Any, List

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.logging import get_logger
from api.models.cutoff import TNEACutoff

logger = get_logger(__name__)

# Branch search mapping for user query terms to full department names
BRANCH_KEYWORD_PATTERNS = {
    "cse": ["computer science", "cse"],
    "ece": ["electronics and communication", "ece"],
    "it": ["information technology", " it"],
    "aids": ["artificial intelligence", "data science", "aids", "ai & ds"],
    "aiml": ["machine learning", "aiml", "ai & ml"],
    "eee": ["electrical and electronics", "eee"],
    "mech": ["mechanical", "mech"],
    "civil": ["civil"],
    "csbs": ["business systems", "csbs"],
    "biotech": ["biotechnology", "biotech"],
    "bme": ["biomedical", "bme"],
}


async def seed_cutoffs_from_file(
    db: AsyncSession, filepath: str = "data/tnea_top_colleges_cutoffs.txt"
) -> int:
    """Populate tnea_cutoffs table from structured text data if not already present."""
    count_stmt = select(func.count(TNEACutoff.id))
    existing_count = (await db.execute(count_stmt)).scalar() or 0
    if existing_count > 0:
        logger.info("cutoffs_already_seeded", count=existing_count)
        return existing_count

    if not os.path.exists(filepath):
        logger.warning("cutoff_seed_file_not_found", path=filepath)
        return 0

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = content.split("---")
    inserted = 0

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        college_match = re.search(
            r"College:\s*(.*?)(?:\s*\(TNEA Code:\s*(\w+)\))?$", block, re.MULTILINE
        )
        branch_match = re.search(r"Branch:\s*(.*)", block)
        cutoffs_match = re.search(r"TNEA Closing Cutoffs:\s*(.*)", block)

        if not college_match or not branch_match or not cutoffs_match:
            continue

        college_name = college_match.group(1).strip()
        college_code = college_match.group(2).strip() if college_match.group(2) else ""
        branch_name = branch_match.group(1).strip()
        cutoffs_str = cutoffs_match.group(1).strip()

        # Parse community cutoffs (OC: 199.5 | BC: 198.5 ...)
        pairs = cutoffs_str.split("|")
        for pair in pairs:
            if ":" not in pair:
                continue
            comm, val_str = pair.split(":", 1)
            comm = comm.strip().upper()
            val_str = val_str.strip()

            try:
                val = float(val_str)
            except ValueError:
                continue

            record = TNEACutoff(
                college_code=college_code,
                college_name=college_name,
                branch_code="",
                branch_name=branch_name,
                community=comm,
                cutoff_mark=val,
                round_no=1,
                academic_year="2024",
            )
            db.add(record)
            inserted += 1

    await db.commit()
    logger.info("cutoffs_seeded_successfully", inserted_count=inserted)
    return inserted


async def get_cutoff_records(
    db: AsyncSession,
    college: str | None = None,
    branch: str | None = None,
    community: str | None = None,
    limit: int = 50,
) -> List[TNEACutoff]:
    """Query cutoff records with college, branch, and community filters."""
    stmt = select(TNEACutoff)

    if college:
        stmt = stmt.where(TNEACutoff.college_name.ilike(f"%{college}%"))
    if branch:
        stmt = stmt.where(TNEACutoff.branch_name.ilike(f"%{branch}%"))
    if community and community != "ALL":
        stmt = stmt.where(TNEACutoff.community == community.upper())

    stmt = stmt.order_by(TNEACutoff.cutoff_mark.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def generate_choice_filling_recommendations(
    db: AsyncSession,
    cutoff: float,
    community: str,
    branches: list[str] | None = None,
    colleges: list[str] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Generate 3-tier TNEA choice filling preference list.

    - Ambitious (Dream): cutoff <= mark <= cutoff + 3.0 (higher competition)
    - Realistic (Target): cutoff - 2.5 <= mark < cutoff (strong chance)
    - Safe (Backup): cutoff - 6.0 <= mark < cutoff - 2.5 (guaranteed admission)
    """
    comm = community.upper()
    base_stmt = select(TNEACutoff).where(TNEACutoff.community == comm)

    # Filter by branches if specified
    if branches:
        branch_conds = []
        for b in branches:
            clean_b = b.lower().strip()
            patterns = BRANCH_KEYWORD_PATTERNS.get(clean_b, [clean_b])
            for pat in patterns:
                branch_conds.append(TNEACutoff.branch_name.ilike(f"%{pat}%"))
        if branch_conds:
            base_stmt = base_stmt.where(or_(*branch_conds))

    # Filter by colleges if specified
    if colleges:
        col_conds = [TNEACutoff.college_name.ilike(f"%{c}%") for c in colleges]
        base_stmt = base_stmt.where(or_(*col_conds))

    # 1. Ambitious / Dream choices (Cutoff to Cutoff + 3.0)
    dream_stmt = (
        base_stmt.where(
            TNEACutoff.cutoff_mark >= cutoff,
            TNEACutoff.cutoff_mark <= cutoff + 3.0,
        )
        .order_by(TNEACutoff.cutoff_mark.asc())
        .limit(8)
    )
    dream_rows = (await db.execute(dream_stmt)).scalars().all()

    # 2. Realistic / Target choices (Cutoff - 2.5 to Cutoff)
    target_stmt = (
        base_stmt.where(
            TNEACutoff.cutoff_mark >= cutoff - 2.5,
            TNEACutoff.cutoff_mark < cutoff,
        )
        .order_by(TNEACutoff.cutoff_mark.desc())
        .limit(10)
    )
    target_rows = (await db.execute(target_stmt)).scalars().all()

    # 3. Safe / Backup choices (Cutoff - 6.0 to Cutoff - 2.5)
    safe_stmt = (
        base_stmt.where(
            TNEACutoff.cutoff_mark >= cutoff - 6.0,
            TNEACutoff.cutoff_mark < cutoff - 2.5,
        )
        .order_by(TNEACutoff.cutoff_mark.desc())
        .limit(8)
    )
    safe_rows = (await db.execute(safe_stmt)).scalars().all()

    def format_row(r: TNEACutoff) -> dict[str, Any]:
        return {
            "college_code": r.college_code,
            "college_name": r.college_name,
            "branch_name": r.branch_name,
            "community": r.community,
            "cutoff_mark": r.cutoff_mark,
            "difference": round(r.cutoff_mark - cutoff, 2),
        }

    return {
        "ambitious": [format_row(r) for r in dream_rows],
        "target": [format_row(r) for r in target_rows],
        "safe": [format_row(r) for r in safe_rows],
    }
