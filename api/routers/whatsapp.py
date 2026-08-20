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


async def _answer_student(message: ParsedMessage) -> None:
    """Run the RAG pipeline for a student message and send back the answer.

    Runs as a background task, scheduled only after the webhook has already
    acked Meta with 200 -- Meta expects a reply within a few seconds and
    retries (re-delivering the same event and stacking up duplicate work)
    if the handler blocks on the full RAG pipeline before responding. That
    retry storm, not the RAG pipeline itself, is what turns a ~5-10s answer
    into a multi-minute delay for the student.

    Opens its own DB session since the request that scheduled this task has
    already finished and its session may be closed by the time this runs.

    Never raises: any failure is logged and the user gets a friendly
    fallback.
    """
    try:
        async with async_session_factory() as db:
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
    """Trigger entry point: verify, parse, route, and ack an event.

    Student text messages are handed off to a background task that runs the
    RAG pipeline and sends the answer back over WhatsApp -- this handler
    returns immediately rather than waiting for that to finish. Meta expects
    an ack within a few seconds and otherwise retries delivery, which would
    stack up duplicate RAG runs and turn a single reply into a multi-minute
    wait. Admin commands are still detected/logged only (they need
    ingest/analytics services that don't exist yet). Always acks Meta with
    200 unless the signature is invalid — Meta retries non-2xx.
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
        background_tasks.add_task(_answer_student, message)
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
