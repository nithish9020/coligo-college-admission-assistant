from typing import Any, List

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.logging import get_logger
from api.services.cutoff_service import (
    generate_choice_filling_recommendations,
    get_cutoff_records,
    seed_cutoffs_from_file,
)

router = APIRouter(prefix="/cutoffs", tags=["TNEA Cutoffs & Choice Filling"])
logger = get_logger(__name__)


class CutoffItemResponse(BaseModel):
    college_code: str = Field(..., examples=["2006"])
    college_name: str = Field(..., examples=["PSG College of Technology"])
    branch_name: str = Field(..., examples=["COMPUTER SCIENCE AND ENGINEERING"])
    community: str = Field(..., examples=["BC"])
    cutoff_mark: float = Field(..., examples=[198.5])
    difference: float | None = Field(default=None, examples=[1.5])


class ChoiceFillingResponse(BaseModel):
    cutoff: float
    community: str
    ambitious: List[CutoffItemResponse]
    target: List[CutoffItemResponse]
    safe: List[CutoffItemResponse]


@router.get(
    "/recommendations",
    response_model=ChoiceFillingResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate 3-Tier TNEA Choice Filling List",
)
async def get_choice_filling_recommendations(
    cutoff: float = Query(
        ..., ge=70.0, le=200.0, description="Student TNEA Cutoff (out of 200)"
    ),
    community: str = Query(
        ..., description="Community category (OC, BC, BCM, MBC, SC, SCA, ST)"
    ),
    branches: str | None = Query(
        default=None, description="Comma-separated branches (e.g. CSE,IT,ECE)"
    ),
    colleges: str | None = Query(
        default=None, description="Comma-separated college keywords"
    ),
    db: AsyncSession = Depends(get_db),
) -> ChoiceFillingResponse:
    """Generate 3-tier preference list (Dream, Target, Safe) for TNEA counselling."""
    branch_list = (
        [b.strip() for b in branches.split(",") if b.strip()] if branches else None
    )
    college_list = (
        [c.strip() for c in colleges.split(",") if c.strip()] if colleges else None
    )

    recs = await generate_choice_filling_recommendations(
        db,
        cutoff=cutoff,
        community=community,
        branches=branch_list,
        colleges=college_list,
    )

    return ChoiceFillingResponse(
        cutoff=cutoff,
        community=community.upper(),
        ambitious=[CutoffItemResponse(**r) for r in recs["ambitious"]],
        target=[CutoffItemResponse(**r) for r in recs["target"]],
        safe=[CutoffItemResponse(**r) for r in recs["safe"]],
    )


@router.get(
    "/search",
    response_model=List[CutoffItemResponse],
    status_code=status.HTTP_200_OK,
    summary="Search Official TNEA Cutoff Records",
)
async def search_cutoffs(
    college: str | None = Query(default=None, description="College name or keyword"),
    branch: str | None = Query(
        default=None, description="Branch keyword (e.g. Computer Science)"
    ),
    community: str | None = Query(
        default=None, description="Community (OC, BC, BCM, MBC, SC, ST)"
    ),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> List[CutoffItemResponse]:
    """Retrieve cutoff marks filtered by college, branch, and community."""
    records = await get_cutoff_records(
        db, college=college, branch=branch, community=community, limit=limit
    )
    return [
        CutoffItemResponse(
            college_code=r.college_code,
            college_name=r.college_name,
            branch_name=r.branch_name,
            community=r.community,
            cutoff_mark=r.cutoff_mark,
        )
        for r in records
    ]


@router.post(
    "/seed",
    status_code=status.HTTP_200_OK,
    summary="Seed Official TNEA Cutoffs from Knowledge Base",
)
async def seed_cutoffs(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Seed the database with official closing cutoffs."""
    inserted = await seed_cutoffs_from_file(db)
    return {"status": "success", "records_seeded": inserted}
