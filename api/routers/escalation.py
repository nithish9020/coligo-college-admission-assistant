from datetime import datetime, timezone
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.logging import get_logger
from api.models.escalation import Escalation
from api.services.conversation_service import append_turn, get_or_create_conversation
from api.services.whatsapp_service import send_text

router = APIRouter(prefix="/escalations", tags=["Admin Escalations"])
logger = get_logger(__name__)


class EscalationItemResponse(BaseModel):
    id: int = Field(..., examples=[1])
    sender: str = Field(..., examples=["whatsapp:+919876543210"])
    query_text: str = Field(..., examples=["What is the management quota fee?"])
    status: str = Field(..., examples=["pending"])
    created_at: str = Field(..., examples=["2026-08-19T00:00:00Z"])
    counselor_reply: str | None = Field(default=None)
    resolved_at: str | None = Field(default=None)


class EscalationListResponse(BaseModel):
    total: int
    escalations: List[EscalationItemResponse]


class CounselorReplyRequest(BaseModel):
    message: str = Field(
        ..., min_length=1, max_length=4096, description="Counselor message to student"
    )
    resolve: bool = Field(
        default=True, description="Mark ticket as resolved and resume automated bot"
    )
    send_whatsapp: bool = Field(
        default=True, description="Send outbound WhatsApp message to student"
    )


class CounselorReplyResponse(BaseModel):
    id: int
    status: str
    counselor_reply: str
    delivered_to_whatsapp: bool
    student_phone: str | None = None


class EscalationStatusUpdateRequest(BaseModel):
    status: str = Field(..., examples=["pending", "in_progress", "resolved"])


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
            counselor_reply=esc.counselor_reply,
            resolved_at=esc.resolved_at.isoformat() if esc.resolved_at else None,
        )
        for esc in escalations
    ]
    return EscalationListResponse(total=len(items), escalations=items)


@router.post(
    "/{escalation_id}/reply",
    response_model=CounselorReplyResponse,
    status_code=status.HTTP_200_OK,
    summary="Counselor Live Reply to Student via WhatsApp",
)
async def reply_escalation(
    escalation_id: int,
    payload: CounselorReplyRequest,
    db: AsyncSession = Depends(get_db),
) -> CounselorReplyResponse:
    """Counselor takes over the chat and sends a direct reply to the student's WhatsApp."""
    esc = await db.get(Escalation, escalation_id)
    if not esc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Escalation not found"
        )

    # 1. Clean recipient phone number
    whatsapp_sent = False
    clean_phone = None
    if esc.sender.startswith("whatsapp:"):
        clean_phone = esc.sender.replace("whatsapp:", "").lstrip("+").strip()
    elif esc.sender.lstrip("+").isdigit():
        clean_phone = esc.sender.lstrip("+").strip()

    # 2. Transmit message directly to student via Meta Cloud API
    if payload.send_whatsapp and clean_phone and clean_phone.isdigit():
        outbound_text = (
            f"🎓 *Message from Admission Counselor:*\n\n"
            f"{payload.message.strip()}\n\n"
            f"— *Coligo Admission Team*\n"
            f"_(You can reply directly to continue chatting with the counselor)_"
        )
        whatsapp_sent = await send_text(clean_phone, outbound_text)
        if not whatsapp_sent:
            logger.warning("counselor_reply_whatsapp_send_failed", phone=clean_phone)

    # 3. Append to conversation history so context is preserved
    try:
        conv = await get_or_create_conversation(db, esc.sender)
        await append_turn(
            db, conv, "assistant", f"[Counselor Reply]: {payload.message.strip()}"
        )
    except Exception as e:
        logger.error("failed_to_append_counselor_turn", error=str(e))

    # 4. Update escalation record
    esc.counselor_reply = payload.message.strip()
    if payload.resolve:
        esc.status = "resolved"
        esc.resolved_at = datetime.now(timezone.utc)
    else:
        esc.status = "in_progress"

    await db.commit()
    logger.info(
        "counselor_reply_processed",
        escalation_id=escalation_id,
        status=esc.status,
        delivered=whatsapp_sent,
    )

    return CounselorReplyResponse(
        id=esc.id,
        status=esc.status,
        counselor_reply=esc.counselor_reply or "",
        delivered_to_whatsapp=whatsapp_sent,
        student_phone=clean_phone,
    )


@router.patch(
    "/{escalation_id}/status",
    status_code=status.HTTP_200_OK,
    summary="Update Escalation Status / Takeover State",
)
async def update_escalation_status(
    escalation_id: int,
    payload: EscalationStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update status of escalation ticket (e.g. pending, in_progress, resolved)."""
    esc = await db.get(Escalation, escalation_id)
    if not esc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Escalation not found"
        )

    esc.status = payload.status
    if payload.status == "resolved":
        esc.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    logger.info(
        "escalation_status_updated", escalation_id=escalation_id, status=esc.status
    )
    return {"status": esc.status, "id": escalation_id}


@router.patch(
    "/{escalation_id}/resolve",
    status_code=status.HTTP_200_OK,
    summary="Mark Escalation as Resolved",
)
async def resolve_escalation(
    escalation_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Mark a student escalation query as resolved by an admission officer."""
    esc = await db.get(Escalation, escalation_id)
    if not esc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Escalation not found"
        )

    esc.status = "resolved"
    esc.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    logger.info("escalation_resolved", escalation_id=escalation_id)
    return {"status": "resolved", "id": escalation_id}
