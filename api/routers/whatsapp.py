from fastapi import APIRouter, Header, HTTPException, Query, Request, Response

from api.core.config import settings
from api.core.logging import get_logger
from api.schemas.whatsapp import WhatsAppWebhookPayload
from api.services.whatsapp_service import (
    extract_message,
    is_admin_number,
    match_admin_command,
    verify_signature,
)

router = APIRouter(prefix="/webhook", tags=["WhatsApp Webhook"])
logger = get_logger(__name__)


@router.get("", summary="Meta webhook verification handshake")
async def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
) -> Response:
    """Meta calls this once when you register the webhook URL."""
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("webhook_verified")
        return Response(content=hub_challenge, media_type="text/plain")

    logger.warning("webhook_verification_failed")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("", summary="Receive WhatsApp Cloud API events")
async def receive_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
) -> dict[str, str]:
    """Trigger entry point: verify, parse, and route an incoming event.

    No reply is sent yet — there's no chat/LLM service to generate one.
    This logs the routing decision and acks Meta with 200 (Meta retries on
    non-2xx). Phase 2 will call chat_service.handle_query() /
    ingest_service / analytics_service here and reply via
    whatsapp_service.send_text().
    """
    raw_body = await request.body()

    if settings.WHATSAPP_APP_SECRET:
        if not verify_signature(
            raw_body, x_hub_signature_256, settings.WHATSAPP_APP_SECRET
        ):
            logger.warning("webhook_signature_invalid")
            raise HTTPException(status_code=401, detail="Invalid signature")
    else:
        logger.warning("webhook_signature_check_skipped_no_app_secret_configured")

    payload = WhatsAppWebhookPayload.model_validate_json(raw_body)
    message = extract_message(payload)

    if message is None:
        logger.debug("webhook_event_ignored", reason="no_message_in_payload")
        return {"status": "ignored"}

    if is_admin_number(message.sender):
        command = match_admin_command(message.text)
        logger.info(
            "admin_message_received",
            sender=message.sender,
            command=command,
            message_type=message.message_type,
        )
    else:
        logger.info(
            "student_message_received",
            sender=message.sender,
            message_type=message.message_type,
        )

    return {"status": "received"}
