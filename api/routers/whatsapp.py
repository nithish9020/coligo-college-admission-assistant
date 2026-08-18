from fastapi import (
    APIRouter,
    BackgroundTasks,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
)

from api.core.config import settings
from api.core.database import async_session_factory
from api.core.logging import get_logger
from api.schemas.whatsapp import ParsedMessage, WhatsAppWebhookPayload
from api.services.rag_service import handle_rag_query
from api.services.whatsapp_service import (
    extract_message,
    is_admin_number,
    match_admin_command,
    send_text,
    verify_signature,
)

FALLBACK_REPLY = (
    "Sorry, I ran into a problem answering that. Please try again in a moment."
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


async def _answer_student_task(message: ParsedMessage) -> None:
    """Run the RAG pipeline in background with its own DB session."""
    async with async_session_factory() as db:
        try:
            answer, sources = await handle_rag_query(
                db, message.text or "", session_key=f"whatsapp:{message.sender}"
            )
            logger.info(
                "rag_answer_generated", sender=message.sender, source_count=len(sources)
            )
        except Exception as e:
            logger.error("rag_query_failed", sender=message.sender, error=str(e))
            answer = FALLBACK_REPLY
        await send_text(message.sender, answer)


@router.post("", summary="Receive WhatsApp Cloud API events")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str | None = Header(default=None),
) -> dict[str, str]:
    """Trigger entry point: verify, parse, route, and reply asynchronously.

    Acknowledges Meta immediately with HTTP 200 to prevent webhook timeouts
    and duplicate message retries. The RAG pipeline runs in a background task.
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
        return {"status": "received"}

    logger.info(
        "student_message_received",
        sender=message.sender,
        message_type=message.message_type,
    )

    if message.message_type == "text" and message.text:
        background_tasks.add_task(_answer_student_task, message)
    else:
        logger.debug(
            "reply_skipped_unsupported_message_type",
            message_type=message.message_type,
        )
        background_tasks.add_task(
            send_text,
            message.sender,
            "I can only answer text questions right now. Please type your query.",
        )

    return {"status": "received"}
