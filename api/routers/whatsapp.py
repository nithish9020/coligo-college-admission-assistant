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
from api.models import Escalation
from api.schemas.whatsapp import ParsedMessage, WhatsAppWebhookPayload
from api.services.message_formatter import (
    format_whatsapp_response,
    get_course_list_menu_sections,
    get_welcome_message,
    is_greeting,
)
from api.services.rag_service import handle_rag_query
from api.services.whatsapp_service import (
    execute_admin_command,
    extract_message,
    is_admin_number,
    mark_message_as_read,
    match_admin_command,
    send_interactive_buttons,
    send_interactive_list,
    send_text,
    verify_signature,
)

FALLBACK_REPLY = (
    "Hey! I ran into a tiny hiccup fetching that info. "
    "Could you try asking again in a moment?"
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
    if message.message_id:
        await mark_message_as_read(message.message_id)

    query = (message.text or "").strip()
    if is_greeting(query):
        welcome_txt = get_welcome_message()
        buttons = [
            ("btn_courses", "View Courses"),
            ("btn_cutoff", "Check Cutoff"),
            ("btn_fees", "Fee Details"),
        ]
        sent_buttons = await send_interactive_buttons(
            message.sender, welcome_txt, buttons
        )
        if not sent_buttons:
            await send_text(message.sender, welcome_txt)
        return

    if query.lower() in (
        "btn_courses",
        "view courses",
        "explore courses",
        "courses offered",
    ):
        sections = get_course_list_menu_sections()
        sent_list = await send_interactive_list(
            message.sender,
            "🎓 *Select an Engineering Branch below to view intake, cutoffs, and career opportunities:*",
            "Browse Branches",
            sections,
        )
        if sent_list:
            return

    if query.lower() in ("btn_cutoff", "check cutoff"):
        cutoff_msg = (
            "📊 *TNEA Cutoff Information & Calculator*\n\n"
            "• Type your marks like: *Maths 95, Physics 90, Chemistry 88* to calculate your TNEA cutoff mark.\n"
            "• Or choose a branch below to view community cutoffs (OC, BC, MBC, SC, ST):"
        )
        buttons = [
            ("btn_cutoff_cse", "CSE Cutoffs"),
            ("btn_cutoff_ece", "ECE Cutoffs"),
            ("btn_fees", "Fee Details"),
        ]
        sent_cutoff_btns = await send_interactive_buttons(
            message.sender, cutoff_msg, buttons
        )
        if not sent_cutoff_btns:
            await send_text(message.sender, cutoff_msg)
        return

    # Map menu selection IDs to structured query prompts
    menu_query_map = {
        "btn_fees": "What is the complete tuition fee, hostel fee, and transport fee structure?",
        "btn_cutoff_cse": "What are the TNEA cutoff marks for Computer Science Engineering (CSE)?",
        "btn_cutoff_ece": "What are the TNEA cutoff marks for Electronics and Communication Engineering (ECE)?",
        "cse_info": "What is the intake, TNEA cutoff, and placement record for Computer Science Engineering (CSE)?",
        "ece_info": "What is the intake, TNEA cutoff, and placement record for Electronics and Communication Engineering (ECE)?",
        "it_info": "What is the intake, TNEA cutoff, and placement record for Information Technology (IT)?",
        "aids_info": "What is the intake, TNEA cutoff, and placement record for AI & Data Science (AI & DS)?",
        "mech_info": "What is the intake, TNEA cutoff, and placement record for Mechanical Engineering?",
        "eee_info": "What is the intake, TNEA cutoff, and placement record for Electrical and Electronics Engineering (EEE)?",
        "civil_info": "What is the intake, TNEA cutoff, and placement record for Civil Engineering?",
    }

    if query.lower() in menu_query_map:
        query = menu_query_map[query.lower()]

    if query.lower() in ("btn_helpful", "👍 helpful"):
        await send_text(
            message.sender,
            "😊 *Thanks for your feedback!* Good luck with your TNEA college admissions! 🎓",
        )
        return

    if query.lower() in ("btn_unhelpful", "👎 need help"):
        async with async_session_factory() as db:
            try:
                db.add(
                    Escalation(
                        sender=f"whatsapp:{message.sender}",
                        query_text="User marked answer as unhelpful / requested human counselor",
                    )
                )
                await db.commit()
            except Exception as e:
                logger.error("feedback_escalation_failed", error=str(e))
        await send_text(
            message.sender,
            "📞 *Got it!* I've notified our admission team. A counselor will follow up with you soon!",
        )
        return

    async with async_session_factory() as db:
        try:
            answer, sources = await handle_rag_query(
                db, query, session_key=f"whatsapp:{message.sender}"
            )
            formatted_answer = format_whatsapp_response(query, answer, sources)
            await send_text(message.sender, formatted_answer)
        except Exception as e:
            logger.error("rag_query_failed", sender=message.sender, error=str(e))
            await send_text(message.sender, FALLBACK_REPLY)


async def _execute_admin_task(command: str, full_text: str, sender: str) -> None:
    """Run admin command in background with its own DB session."""
    async with async_session_factory() as db:
        try:
            await execute_admin_command(db, command, full_text, sender)
        except Exception as e:
            logger.error("admin_command_failed", command=command, error=str(e))


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
        if command:
            background_tasks.add_task(
                _execute_admin_task, command, message.text or "", message.sender
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
