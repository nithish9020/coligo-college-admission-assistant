from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.logging import get_logger
from api.models.escalation import Escalation

router = APIRouter(prefix="/escalations", tags=["Admin Escalations"])
logger = get_logger(__name__)


class EscalationItemResponse(BaseModel):
    id: int = Field(..., examples=[1])
    sender: str = Field(..., examples=["whatsapp:+919876543210"])
    query_text: str = Field(..., examples=["What is the management quota fee?"])
    status: str = Field(..., examples=["pending"])
    created_at: str = Field(..., examples=["2026-08-19T00:00:00Z"])


class EscalationListResponse(BaseModel):
    total: int
    escalations: List[EscalationItemResponse]


@router.get(
    "",
    response_model=EscalationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Out-of-Scope Student Escalations",
)
async def list_escalations(
    db: AsyncSession = Depends(get_db),
) -> EscalationListResponse:
    """List all out-of-scope student queries that need human admission counselor follow-up."""
    stmt = select(Escalation).order_by(Escalation.created_at.desc())
    escalations = (await db.execute(stmt)).scalars().all()

    items = [
        EscalationItemResponse(
            id=esc.id,
            sender=esc.sender,
            query_text=esc.query_text,
            status=esc.status,
            created_at=esc.created_at.isoformat(),
        )
        for esc in escalations
    ]
    return EscalationListResponse(total=len(items), escalations=items)


@router.patch(
    "/{escalation_id}/resolve",
    status_code=status.HTTP_200_OK,
    summary="Mark Escalation as Resolved",
)
async def resolve_escalation(
    escalation_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark a student escalation query as resolved by an admission officer."""
    esc = await db.get(Escalation, escalation_id)
    if not esc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Escalation not found"
        )

    esc.status = "resolved"
    await db.commit()
    logger.info("escalation_resolved", escalation_id=escalation_id)
    return {"status": "resolved", "id": escalation_id}
