import time

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
    get_college_list_menu_sections,
    get_course_list_menu_sections,
    get_welcome_message,
    is_brochure_query,
    is_greeting,
)
from api.services.rag_service import handle_rag_query
from api.services.whatsapp_service import (
    execute_admin_command,
    extract_message,
    is_admin_number,
    mark_message_as_read,
    match_admin_command,
    send_contact,
    send_document,
    send_interactive_buttons,
    send_interactive_list,
    send_location,
    send_text,
    send_typing_indicator,
    verify_signature,
)

FALLBACK_REPLY = (
    "Hey! I ran into a tiny hiccup fetching that info. "
    "Could you try asking again in a moment?"
)

# Keywords that indicate the student wants to know which colleges are in the system
_COLLEGES_LIST_KEYWORDS = (
    "which college",
    "what college",
    "colleges do you have",
    "colleges you have",
    "what colleges",
    "colleges available",
    "list of colleges",
    "colleges in the database",
    "data about which",
    "which colleges",
    "know about which",
    "info about which",
    "contacts about",
    "have information",
)


def _is_colleges_list_query(text: str) -> bool:
    """Return True if the student is asking which colleges are available."""
    cleaned = text.strip().lower()
    return any(kw in cleaned for kw in _COLLEGES_LIST_KEYWORDS)


router = APIRouter(prefix="/webhook", tags=["WhatsApp Webhook"])
logger = get_logger(__name__)

# ── Duplicate-message guard ────────────────────────────────────────────
# Meta retries webhook POSTs when the initial request is slow.  We track
# recently-processed message IDs so the bot never answers twice.
_PROCESSED_IDS: dict[str, float] = {}
_DEDUP_TTL = 60  # seconds


def _is_duplicate(message_id: str) -> bool:
    """Return True if this message_id was already processed within TTL."""
    now = time.time()
    # Evict stale entries
    stale = [k for k, v in _PROCESSED_IDS.items() if now - v > _DEDUP_TTL]
    for k in stale:
        del _PROCESSED_IDS[k]
    if message_id in _PROCESSED_IDS:
        return True
    _PROCESSED_IDS[message_id] = now
    return False


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


async def _handle_location_query(sender: str, query: str) -> bool:
    """Send native location pin and transit instructions for campus."""
    q_lower = query.lower()
    location_triggers = (
        "btn_location",
        "where is the college",
        "where is skcet",
        "campus location",
        "college location",
        "how to reach skcet",
        "how to reach the college",
        "college address",
        "route map",
        "google map",
        "location pin",
    )
    if not any(kw in q_lower for kw in location_triggers):
        return False

    await send_location(
        to=sender,
        latitude=10.9388,
        longitude=76.9554,
        name="Sri Krishna College of Engineering & Technology (SKCET)",
        address="Kuniamuthur, Coimbatore, Tamil Nadu 641008",
    )
    guide = (
        "📍 *Campus Location & Travel Guide*\n\n"
        "🏫 *Sri Krishna College of Engineering and Technology (Autonomous)*\n"
        "Kuniamuthur, Palakkad Main Road, Coimbatore - 641008\n\n"
        "🚌 *Transit Connectivity:*\n"
        "• *Coimbatore Railway Junction*: 8 km (Bus Route 3, 3A, 4)\n"
        "• *Ukkadam Bus Stand*: 6 km (Direct buses every 5 mins)\n"
        "• *Gandhipuram Central Bus Stand*: 12 km\n"
        "• *Coimbatore Airport (CJB)*: 18 km\n\n"
        "💡 _You can tap the location pin above to navigate with Google Maps!_"
    )
    await send_text(sender, guide)
    return True


async def _handle_contact_query(sender: str, query: str) -> bool:
    """Send native vCard contact card for admission desk."""
    q_lower = query.lower()
    contact_triggers = (
        "btn_contact",
        "admission helpline",
        "contact number",
        "call college",
        "phone number",
        "admission office",
        "counselor phone",
        "help desk phone",
    )
    if not any(kw in q_lower for kw in contact_triggers):
        return False

    await send_contact(
        to=sender,
        name="SKCET Admissions Helpline",
        phone="+914222678001",
        org="Sri Krishna College of Engg & Tech",
        email="admissions@skcet.ac.in",
    )
    await send_text(
        sender,
        "📞 *Official Admissions Contact Card sent above!*\n\n"
        "Tap *'Add to Contacts'* or call the admission desk directly for:\n"
        "• Management / Lateral Entry Quota\n"
        "• Sports Quota & 7.5% Govt School Quota\n"
        "• Campus Hostel & Transport Booking",
    )
    return True


async def _handle_college_menu_query(sender: str, query: str) -> bool:
    """Send interactive list menu for college directory."""
    q_lower = query.lower()
    if q_lower not in (
        "btn_colleges",
        "explore colleges",
        "choose college",
        "compare colleges",
        "college list",
    ):
        return False

    sections = get_college_list_menu_sections()
    sent = await send_interactive_list(
        to=sender,
        body_text=(
            "🏫 *Select an Engineering College below to view campus highlights, "
            "closing cutoff ranks, and available courses:*"
        ),
        button_label="Explore Colleges",
        sections=sections,
    )
    if not sent:
        await send_text(
            sender,
            "🏫 *Featured TNEA Institutions:*\n"
            "• SKCET Coimbatore (2722)\n"
            "• PSG Tech Coimbatore (2006)\n"
            "• CIT Coimbatore (2007)\n"
            "• Kumaraguru KCT (2712)\n"
            "• GCT Coimbatore (2005)\n"
            "• CEG Anna Univ (0001)\n\n"
            "💡 Reply with any college name to see cutoff marks!",
        )
    return True


async def _handle_choice_list_query(sender: str, query: str, session_key: str) -> bool:
    """Generate personalized TNEA 10-choice order draft."""
    q_lower = query.lower()
    triggers = (
        "btn_choice_list",
        "choice list",
        "generate choice list",
        "suggest choices",
        "choice filling order",
        "choice order",
    )
    if not any(kw in q_lower for kw in triggers):
        return False

    from api.services.choice_list_service import generate_tnea_choice_list
    from api.services.student_profile_service import get_student_profile

    profile = get_student_profile(session_key)
    if profile.calculated_cutoff is None:
        prompt_msg = (
            "📋 *Personalized TNEA Choice Filling Generator*\n\n"
            "To generate your customized 10-choice order draft, I need your cutoff!\n\n"
            "• Send your cutoff mark (e.g. *185*)\n"
            "• Or type marks: *Maths 90, Physics 85, Chemistry 80*\n"
            "• And your community quota (e.g. *BC*, *MBC*, *OC*, *SC*)"
        )
        await send_text(sender, prompt_msg)
        return True

    async with async_session_factory() as db:
        choice_draft = await generate_tnea_choice_list(
            db=db,
            cutoff=profile.calculated_cutoff,
            community=profile.community or "BC",
            preferred_branches=profile.preferred_branches or None,
            preferred_colleges=profile.preferred_colleges or None,
        )
    await send_text(sender, choice_draft)
    return True


async def _answer_student_task(message: ParsedMessage) -> None:
    """Run the RAG pipeline in background with its own DB session."""
    if message.message_id:
        await mark_message_as_read(message.message_id)

    voice_prefix = ""
    query = (message.text or "").strip()

    # ── 0. Handle WhatsApp Audio / Voice Note Transcriptions ──
    if message.message_type in ("audio", "voice") and message.media_id:
        from api.services.audio_service import transcribe_audio_message

        logger.info("transcribing_incoming_voice_note", media_id=message.media_id)
        transcript = await transcribe_audio_message(message.media_id)
        if transcript:
            query = transcript
            voice_prefix = f'🎙️ _"Voice note: {transcript}"_\n\n'
            logger.info("voice_note_transcribed_successfully", transcript=transcript)
        else:
            await send_text(
                message.sender,
                "🎙️ Sorry, I had trouble listening to your audio message clearly. "
                "Could you please type your admission query as text?",
            )
            return

    if not query:
        return

    session_key = f"whatsapp:{message.sender}"

    # ── 1. Student /resume command to release escalation pause ──
    if query.lower() in ("/resume", "resume", "resume bot", "resume ai", "start ai"):
        from datetime import datetime, timezone

        from sqlalchemy import select

        async with async_session_factory() as db:
            stmt = select(Escalation).where(
                Escalation.sender == session_key,
                Escalation.status.in_(["pending", "in_progress"]),
            )
            active_escalations = (await db.execute(stmt)).scalars().all()
            for esc in active_escalations:
                esc.status = "resolved"
                esc.resolved_at = datetime.now(timezone.utc)
            await db.commit()

        resume_msg = (
            "🤖 *AI Assistant Resumed!*\n\n"
            "You are now back in automated mode with Coligo TNEA Assistant. "
            "Ask me anything about engineering college cutoffs, courses, or fee details!"
        )
        await send_text(message.sender, resume_msg)
        return

    # ── 2. Check if conversation is paused due to an active human counselor takeover ──
    from sqlalchemy import select

    from api.services.conversation_service import (
        append_turn,
        get_or_create_conversation,
    )

    async with async_session_factory() as db:
        stmt = (
            select(Escalation)
            .where(
                Escalation.sender == session_key,
                Escalation.status.in_(["pending", "in_progress"]),
            )
            .order_by(Escalation.created_at.desc())
            .limit(1)
        )
        active_esc = (await db.execute(stmt)).scalar_one_or_none()
        if active_esc is not None:
            logger.info(
                "student_message_paused_active_escalation",
                sender=message.sender,
                escalation_id=active_esc.id,
                status=active_esc.status,
            )
            try:
                conv = await get_or_create_conversation(db, session_key)
                await append_turn(db, conv, "user", query)
                active_esc.query_text += f"\n[Student Follow-up]: {query}"
                await db.commit()
            except Exception as e:
                logger.error("failed_to_log_paused_message", error=str(e))

            status_str = (
                "in active consultation with"
                if active_esc.status == "in_progress"
                else "assigned to"
            )
            pause_notice = (
                f"⏳ *Your conversation is currently {status_str} an admission counselor.*\n\n"
                "A human admission officer is reviewing your queries and will respond directly here on WhatsApp.\n\n"
                "💡 _To switch back to automated AI mode at any time, simply reply with */resume*._"
            )
            await send_text(message.sender, pause_notice)
            return

    # ── Colleges-list shortcut: answer directly from DB, not from RAG ──
    # Vector search ranks individual chunks by similarity, so a generic
    # "which colleges" query surfaces whichever college appears most often
    # in the top-K results — not all ingested colleges. We fix this by
    # querying the documents table directly and formatting the answer here.
    if _is_colleges_list_query(query):
        from sqlalchemy import select

        async with async_session_factory() as db:
            try:
                from api.models import Document

                result = await db.execute(select(Document.document_ref))
                refs = [row[0] for row in result.all()]

                # Build human-readable college names from document refs
                college_lines = []
                seen: set[str] = set()
                for ref in refs:
                    import os

                    base = os.path.basename(ref).replace("_", " ").replace("-", " ")
                    # Strip file extensions
                    for ext in (".pdf", ".txt"):
                        base = base.replace(ext, "")
                    # Group duplicates (e.g. aggregated cutoff file)
                    if "raw cutoffs" in base.lower() or "aggregated" in base.lower():
                        label = "Cutoff data: Bannari Amman, CIT, Kongu, SKCET, PSG Tech, Kumaraguru + more"
                    else:
                        label = base.title()
                    if label not in seen:
                        seen.add(label)
                        college_lines.append(f"• {label}")

                if college_lines:
                    reply = (
                        "🏫 *Colleges with TNEA data in my system:*\n\n"
                        + "\n".join(college_lines)
                        + "\n\n💡 Ask me the cutoff, fees, or courses for any of these!"
                    )
                else:
                    reply = "No college data has been ingested yet. Please ask an admin to upload documents."
            except Exception as e:
                logger.error("colleges_list_query_failed", error=str(e))
                reply = FALLBACK_REPLY

        await send_text(message.sender, reply)
        return

    if await _handle_location_query(message.sender, query):
        return

    if await _handle_contact_query(message.sender, query):
        return

    if await _handle_college_menu_query(message.sender, query):
        return

    if await _handle_choice_list_query(message.sender, query, session_key):
        return

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

    # ── Automated Brochure Delivery ──
    if is_brochure_query(query) or query.lower() == "btn_brochure":
        college_label = "Sri Krishna College of Engg & Tech (SKCET)"
        filename = "SKCET_Admission_Brochure.pdf"
        if "psg" in query.lower():
            college_label = "PSG College of Technology"
            filename = "PSG_Tech_Admission_Brochure.pdf"

        brochure_url = (
            "https://coligo-college-admission-assistant.onrender.com"
            "/static/skcet_tnea_knowledge_base.pdf"
        )
        caption = f"📄 *{college_label} - Official Admission Guide & Cutoffs*"

        sent_doc = await send_document(
            to=message.sender,
            document_url=brochure_url,
            caption=caption,
            filename=filename,
        )
        if not sent_doc:
            await send_text(
                message.sender,
                f"📄 *{college_label} Official Guide*\n\n"
                f"Download brochure here:\n{brochure_url}\n\n"
                "💡 Reply with *Cutoff* or *Fees* to explore more!",
            )
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
        "btn_comm_bc": "I belong to BC community. What are my college admission chances?",
        "btn_comm_mbc": "I belong to MBC community. What are my college admission chances?",
        "btn_comm_oc": "I belong to OC community. What are my college admission chances?",
        "btn_comm_sc": "I belong to SC community. What are my college admission chances?",
        "col_skcet": "What are the cutoff marks, top branches, and placements at Sri Krishna College of Engineering and Technology (SKCET 2722)?",
        "col_psg": "What are the cutoff marks, top branches, and placements at PSG College of Technology (PSG 2006)?",
        "col_cit": "What are the cutoff marks, top branches, and placements at Coimbatore Institute of Technology (CIT 2007)?",
        "col_kct": "What are the cutoff marks, top branches, and placements at Kumaraguru College of Technology (KCT 2712)?",
        "col_gct": "What are the cutoff marks, top branches, and placements at Government College of Technology (GCT 2005)?",
        "col_ceg": "What are the cutoff marks, top branches, and placements at College of Engineering Guindy (CEG 0001)?",
        "col_mit": "What are the cutoff marks, top branches, and placements at Madras Institute of Technology (MIT 0004)?",
        "col_ssn": "What are the cutoff marks, top branches, and placements at SSN College of Engineering (SSN 1315)?",
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
        await send_contact(
            to=message.sender,
            name="SKCET Admissions Helpline",
            phone="+914222678001",
            org="Sri Krishna College of Engg & Tech",
            email="admissions@skcet.ac.in",
        )
        await send_text(
            message.sender,
            "📞 *Got it!* I've logged your request for an admission counselor and sent "
            "their direct contact card above so you can reach an officer directly!",
        )
        return

    session_key = f"whatsapp:{message.sender}"
    async with async_session_factory() as db:
        try:
            from api.services.message_formatter import calculate_tnea_cutoff
            from api.services.student_profile_service import get_student_profile

            profile = get_student_profile(session_key)
            calculated_cutoff = calculate_tnea_cutoff(query)
            if calculated_cutoff is None and profile.calculated_cutoff is not None:
                calculated_cutoff = profile.calculated_cutoff

            if message.message_id:
                await send_typing_indicator(message.message_id)

            answer, sources = await handle_rag_query(
                db,
                query,
                session_key=session_key,
                system_calculated_cutoff=calculated_cutoff,
            )
            formatted_answer = (
                f"{voice_prefix}{format_whatsapp_response(query, answer, sources)}"
            )
            await send_text(message.sender, formatted_answer)

            # Contextual interactive quick-action CTA buttons
            q_lower = query.lower()
            if any(
                k in q_lower
                for k in (
                    "cutoff",
                    "mark",
                    "rank",
                    "maths",
                    "physics",
                    "community",
                )
            ):
                if not profile.community:
                    comm_cta = [
                        ("btn_comm_bc", "BC Community"),
                        ("btn_comm_mbc", "MBC Community"),
                        ("btn_comm_oc", "OC Community"),
                    ]
                    await send_interactive_buttons(
                        message.sender,
                        "💡 *Select your community to check exact closing ranks:*",
                        comm_cta,
                    )
                else:
                    cta = [
                        ("btn_choice_list", "Choice List Draft"),
                        ("btn_colleges", "Explore Colleges"),
                        ("btn_brochure", "Get Brochure"),
                    ]
                    await send_interactive_buttons(
                        message.sender,
                        "💡 *What would you like to explore next?*",
                        cta,
                    )
            elif any(
                k in q_lower
                for k in ("location", "campus", "address", "reach", "hostel")
            ):
                cta = [
                    ("btn_location", "Campus Location"),
                    ("btn_contact", "Admission Desk"),
                    ("btn_fees", "Fee Details"),
                ]
                await send_interactive_buttons(
                    message.sender, "💡 *Campus & Visit Information:*", cta
                )
            elif any(
                k in q_lower for k in ("fee", "fees", "cost", "hostel", "tuition")
            ):
                cta = [
                    ("btn_cutoff", "Check Cutoff"),
                    ("btn_courses", "View Courses"),
                    ("btn_brochure", "Get Brochure"),
                ]
                await send_interactive_buttons(
                    message.sender, "💡 *Explore more options:*", cta
                )
            elif any(
                k in q_lower for k in ("course", "branch", "cse", "ece", "mech", "it")
            ):
                cta = [
                    ("btn_cutoff", "Check Cutoff"),
                    ("btn_fees", "Fee Details"),
                    ("btn_brochure", "Get Brochure"),
                ]
                await send_interactive_buttons(message.sender, "💡 *Next Steps:*", cta)
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

    # ── Deduplicate retried webhook deliveries ──
    if _is_duplicate(message.message_id):
        logger.info("duplicate_message_skipped", message_id=message.message_id)
        return {"status": "duplicate_skipped"}

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
        # Admin sent a non-command message — fall through to student pipeline
        # so admins can also test the bot by chatting normally.

    logger.info(
        "student_message_received",
        sender=message.sender,
        message_type=message.message_type,
    )

    if message.text or message.message_type in ("audio", "voice"):
        # Covers text messages, interactive buttons, and voice notes
        background_tasks.add_task(_answer_student_task, message)
    else:
        logger.debug(
            "reply_skipped_unsupported_message_type",
            message_type=message.message_type,
        )
        background_tasks.add_task(
            send_text,
            message.sender,
            "I can only answer text questions or voice notes right now. Please type or speak your query!",
        )

    return {"status": "received"}
