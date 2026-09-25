import re
import time
from typing import Any

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
        buttons = [
            ("btn_matchmaker", "Find My College"),
            ("btn_cutoff", "Check Cutoff"),
            ("btn_placements", "Placement Stats"),
        ]
        sent_p = await send_interactive_buttons(sender, prompt_msg, buttons)
        if not sent_p:
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

        try:
            from api.services.choice_list_service import generate_choice_sheet_file

            _, pdf_url = await generate_choice_sheet_file(
                db=db,
                cutoff=profile.calculated_cutoff,
                community=profile.community or "BC",
                preferred_branches=profile.preferred_branches or None,
                preferred_colleges=profile.preferred_colleges or None,
                session_key=session_key,
            )
            await send_document(
                to=sender,
                document_url=pdf_url,
                caption=(
                    "📄 *Your Official TNEA Choice Filling Sheet (PDF)*\n"
                    "Save or print this to fill choices on tneaonline.org!"
                ),
                filename="TNEA_Choice_Filling_Sheet.pdf",
            )
        except Exception as pdf_err:
            logger.error("choice_sheet_pdf_delivery_failed", error=str(pdf_err))

        cta_buttons = [
            ("btn_download_pdf", "Download PDF"),
            ("btn_change_dist", "Change District"),
            ("btn_contact", "Talk to Counselor"),
        ]
        await send_interactive_buttons(
            sender, "💡 *Next Steps for Choice Filling:*", cta_buttons
        )
    return True


async def _handle_download_pdf_query(sender: str, query: str, session_key: str) -> bool:
    """Send or re-send downloadable TNEA choice sheet PDF."""
    q_lower = query.lower()
    if q_lower not in ("btn_download_pdf", "download pdf", "download pdf sheet"):
        return False

    from api.services.choice_list_service import generate_choice_sheet_file
    from api.services.student_profile_service import get_student_profile

    profile = get_student_profile(session_key)
    cutoff = profile.calculated_cutoff or 185.0
    community = profile.community or "BC"

    async with async_session_factory() as db:
        try:
            _, pdf_url = await generate_choice_sheet_file(
                db=db,
                cutoff=cutoff,
                community=community,
                preferred_branches=profile.preferred_branches or None,
                preferred_colleges=profile.preferred_colleges or None,
                session_key=session_key,
            )
            await send_document(
                to=sender,
                document_url=pdf_url,
                caption=(
                    f"📄 *Official TNEA Choice Sheet ({community} - {cutoff:g})*\n"
                    "Ready for choice locking on tneaonline.org!"
                ),
                filename="TNEA_Choice_Filling_Sheet.pdf",
            )
        except Exception as e:
            logger.error("download_pdf_failed", error=str(e))
            await send_text(
                sender,
                "⚠️ Could not generate PDF right now. Please send your cutoff score first!",
            )
    return True


async def _handle_change_district_query(
    sender: str, query: str, session_key: str
) -> bool:
    """Prompt for changing preferred region / district."""
    q_lower = query.lower()
    if q_lower not in ("btn_change_dist", "change district"):
        return False

    from api.services.student_profile_service import get_student_profile

    profile = get_student_profile(session_key)
    profile.matchmaker_step = 3
    step3_msg = (
        "📍 *Select your preferred location / district:*\n"
        "Tap below to regenerate your choice sheet for that region:"
    )
    buttons = [
        ("btn_dist_cbe", "Coimbatore"),
        ("btn_dist_chn", "Chennai"),
        ("btn_dist_all", "Anywhere (TN)"),
    ]
    await send_interactive_buttons(sender, step3_msg, buttons)
    return True


async def _handle_rank_predictor_query(
    sender: str, query: str, session_key: str
) -> bool:
    """Predict TNEA State Overall Rank and Counselling Round."""
    q_lower = query.lower()
    if q_lower not in (
        "btn_rank_predictor",
        "rank predictor",
        "predict rank",
        "predict my rank",
    ):
        return False

    from api.services.rank_predictor import format_rank_prediction_message
    from api.services.student_profile_service import get_student_profile

    profile = get_student_profile(session_key)
    if profile.calculated_cutoff is not None:
        msg = format_rank_prediction_message(
            profile.calculated_cutoff, profile.community or "BC"
        )
        await send_text(sender, msg)
        buttons = [
            ("btn_choice_list", "3-Tier Choice List"),
            ("btn_placements", "Placement Stats"),
            ("btn_colleges", "Compare College"),
        ]
        await send_interactive_buttons(
            sender, "💡 *What would you like to explore next?*", buttons
        )
    else:
        prompt_msg = (
            "📈 *TNEA Rank & Counselling Round Predictor*\n\n"
            "To predict your State Overall Rank & Counselling Round:\n"
            "• Send your cutoff mark (e.g. *188*)\n"
            "• Or send your marks: *Maths 90, Physics 85, Chemistry 88*\n"
            "• And your community (e.g. *BC*, *MBC*, *OC*, *SC*)"
        )
        await send_text(sender, prompt_msg)
    return True


async def _handle_placement_query(sender: str, query: str) -> bool:
    """Send structured placement analytics card."""
    q_lower = query.lower()
    if q_lower not in ("btn_placements", "placement stats"):
        return False

    from api.services.placement_service import format_placement_card

    card = format_placement_card("skcet")
    await send_text(sender, card)
    buttons = [
        ("btn_cutoff", "Check Cutoff"),
        ("btn_choice_list", "3-Tier Choice List"),
        ("btn_fees", "Fee Details"),
    ]
    await send_interactive_buttons(
        sender, "💡 *What would you like to explore next?*", buttons
    )
    return True


async def _handle_matchmaker_flow(sender: str, query: str, session_key: str) -> bool:
    """Run interactive 3-step college matchmaker diagnostic flow.

    Step 1: Cutoff score (or subject marks)
    Step 2: Community category (OC, BC, BCM, MBC, SC, ST)
    Step 3: Preferred district (Coimbatore, Chennai, Erode, or Anywhere)
    Delivers instant personalized admission roadmap + choice-sheet PDF in < 2 seconds.
    """
    from api.services.choice_list_service import (
        generate_choice_sheet_file,
        generate_tnea_choice_list,
    )
    from api.services.message_formatter import calculate_tnea_cutoff
    from api.services.rank_predictor import predict_tnea_rank
    from api.services.student_profile_service import (
        get_student_profile,
        update_student_profile,
    )

    profile = get_student_profile(session_key)
    q_lower = query.strip().lower()

    matchmaker_triggers = (
        "btn_matchmaker",
        "btn_find_college",
        "matchmaker",
        "find my college",
        "college matchmaker",
        "find college",
        "start matchmaker",
        "diagnostic",
    )
    is_trigger = any(t in q_lower for t in matchmaker_triggers)
    is_active_step = profile.matchmaker_step in (1, 2, 3)

    if not is_trigger and not is_active_step:
        return False

    if is_trigger and not is_active_step:
        inline_cutoff = calculate_tnea_cutoff(query)
        if inline_cutoff is None:
            c_match = re.search(
                r"\b(1\d{2}(?:\.\d+)?|200(?:\.0+)?|\d{2}(?:\.\d+)?)\b", query
            )
            if c_match:
                val = float(c_match.group(1))
                if 77.5 <= val <= 200.0:
                    inline_cutoff = val

        if inline_cutoff is not None:
            update_student_profile(session_key, cutoff=inline_cutoff)
            profile.matchmaker_step = 2
        elif profile.calculated_cutoff is not None:
            profile.matchmaker_step = 2 if not profile.community else 3
        else:
            profile.matchmaker_step = 1

    # ── Step 1: Cutoff score or subject marks ──
    if profile.matchmaker_step == 1:
        extracted_cutoff = calculate_tnea_cutoff(query)
        if extracted_cutoff is None:
            c_match = re.search(
                r"\b(1\d{2}(?:\.\d+)?|200(?:\.0+)?|\d{2}(?:\.\d+)?)\b", query
            )
            if c_match:
                val = float(c_match.group(1))
                if 77.5 <= val <= 200.0:
                    extracted_cutoff = val

        if extracted_cutoff is not None:
            update_student_profile(session_key, cutoff=extracted_cutoff)
            if profile.community:
                profile.matchmaker_step = 3
                step3_msg = (
                    f"🎯 *TNEA College Matchmaker (Step 3 of 3)*\n\n"
                    f"• Cutoff: *{extracted_cutoff:g}* | Quota: *{profile.community}* ✅\n\n"
                    f"👉 *Step 3: What is your preferred study location / district?*\n"
                    f"Tap below or type your preferred city:"
                )
                buttons = [
                    ("btn_dist_cbe", "Coimbatore"),
                    ("btn_dist_chn", "Chennai"),
                    ("btn_dist_all", "Anywhere (TN)"),
                ]
                await send_interactive_buttons(sender, step3_msg, buttons)
                return True
            else:
                profile.matchmaker_step = 2
                step2_msg = (
                    f"🎯 *TNEA College Matchmaker (Step 2 of 3)*\n\n"
                    f"• Cutoff registered: *{extracted_cutoff:g} / 200.0* ✅\n\n"
                    f"👉 *Step 2: What is your Community Quota category?*\n"
                    f"Tap a button below or type your category (OC, BC, BCM, MBC, SC, ST):"
                )
                buttons = [
                    ("btn_comm_bc", "BC Community"),
                    ("btn_comm_mbc", "MBC Community"),
                    ("btn_comm_oc", "OC Community"),
                ]
                await send_interactive_buttons(sender, step2_msg, buttons)
                return True
        else:
            step1_msg = (
                "🎯 *TNEA College Matchmaker (Step 1 of 3)*\n\n"
                "Welcome to the 3-Step Guided College Matchmaker! 🎓 Let's discover "
                "your ideal engineering colleges & branches in seconds.\n\n"
                "👉 *Step 1: What is your 12th Cutoff score?*\n"
                "• Send your cutoff mark (e.g. *186.5*)\n"
                "• Or type marks: *Maths 95, Physics 90, Chemistry 88*"
            )
            await send_text(sender, step1_msg)
            return True

    # ── Step 2: Community Category (OC, BC, BCM, MBC, SC, ST) ──
    if profile.matchmaker_step == 2:
        comm_match = re.search(r"\b(OC|BC|BCM|MBC|SC|SCA|ST)\b", query, re.IGNORECASE)
        if comm_match or "btn_comm_" in q_lower:
            if "btn_comm_bc" in q_lower:
                comm = "BC"
            elif "btn_comm_mbc" in q_lower:
                comm = "MBC"
            elif "btn_comm_oc" in q_lower:
                comm = "OC"
            elif "btn_comm_sc" in q_lower:
                comm = "SC"
            elif comm_match:
                comm = comm_match.group(1).upper()
            else:
                comm = "BC"

            update_student_profile(session_key, community=comm)
            profile.matchmaker_step = 3
            c_score = profile.calculated_cutoff or 185.0
            step3_msg = (
                f"🎯 *TNEA College Matchmaker (Step 3 of 3)*\n\n"
                f"• Cutoff: *{c_score:g}* | Quota: *{comm}* ✅\n\n"
                f"👉 *Step 3: What is your preferred study location / district?*\n"
                f"Tap below or type your preferred city:"
            )
            buttons = [
                ("btn_dist_cbe", "Coimbatore"),
                ("btn_dist_chn", "Chennai"),
                ("btn_dist_all", "Anywhere (TN)"),
            ]
            await send_interactive_buttons(sender, step3_msg, buttons)
            return True
        else:
            c_score = profile.calculated_cutoff or 185.0
            step2_msg = (
                f"🎯 *TNEA College Matchmaker (Step 2 of 3)*\n\n"
                f"• Cutoff registered: *{c_score:g} / 200.0* ✅\n\n"
                f"👉 *Step 2: What is your Community Quota category?*\n"
                f"Tap a button below or type your category (OC, BC, BCM, MBC, SC, ST):"
            )
            buttons = [
                ("btn_comm_bc", "BC Community"),
                ("btn_comm_mbc", "MBC Community"),
                ("btn_comm_oc", "OC Community"),
            ]
            await send_interactive_buttons(sender, step2_msg, buttons)
            return True

    # ── Step 3: Preferred District / Region ──
    if profile.matchmaker_step == 3:
        dist = "Anywhere"
        if any(k in q_lower for k in ("coimbatore", "cbe", "kovai", "btn_dist_cbe")):
            dist = "Coimbatore"
        elif any(k in q_lower for k in ("chennai", "chn", "btn_dist_chn")):
            dist = "Chennai"
        elif any(k in q_lower for k in ("erode", "sathy", "perundurai")):
            dist = "Erode"
        elif any(
            k in q_lower
            for k in ("anywhere", "all", "tn", "tamil nadu", "btn_dist_all")
        ):
            dist = "Anywhere"
        elif (
            query.strip()
            and not is_trigger
            and not any(k in q_lower for k in ("step", "matchmaker", "find my college"))
        ):
            dist = query.strip().title()
        else:
            c_score = profile.calculated_cutoff or 185.0
            comm_val = profile.community or "BC"
            step3_msg = (
                f"🎯 *TNEA College Matchmaker (Step 3 of 3)*\n\n"
                f"• Cutoff: *{c_score:g}* | Quota: *{comm_val}* ✅\n\n"
                f"👉 *Step 3: What is your preferred study location / district?*\n"
                f"Tap below or type your preferred city:"
            )
            buttons = [
                ("btn_dist_cbe", "Coimbatore"),
                ("btn_dist_chn", "Chennai"),
                ("btn_dist_all", "Anywhere (TN)"),
            ]
            await send_interactive_buttons(sender, step3_msg, buttons)
            return True

        update_student_profile(session_key, district=dist, clear_matchmaker=True)

        cutoff_val = profile.calculated_cutoff or 185.0
        comm_val = profile.community or "BC"
        rank_data = predict_tnea_rank(cutoff_val, comm_val)

        async with async_session_factory() as db:
            pref_colls = None
            if dist.lower() == "coimbatore":
                pref_colls = ["SKCET", "PSG", "CIT", "KCT", "GCT", "Sri Eshwar"]
            elif dist.lower() == "chennai":
                pref_colls = ["CEG", "MIT", "SSN", "REC", "SVCE"]

            choice_draft = await generate_tnea_choice_list(
                db=db,
                cutoff=cutoff_val,
                community=comm_val,
                preferred_branches=profile.preferred_branches or None,
                preferred_colleges=pref_colls,
            )

            roadmap_msg = (
                f"🎉 *Your TNEA Personalized Admission Roadmap!* 🎓\n\n"
                f"• *Cutoff Score:* *{cutoff_val:g} / 200.0*\n"
                f"• *Community Quota:* *{comm_val}*\n"
                f"• *Preferred Region:* *{dist}*\n\n"
                f"🎯 *Predicted State Overall Rank:* *~{rank_data['overall_rank_min']:,} to {rank_data['overall_rank_max']:,}*\n"
                f"🏷️ *Predicted Community Rank ({comm_val}):* *~{rank_data['community_rank_min']:,} to {rank_data['community_rank_max']:,}*\n"
                f"🏁 *Eligible Counselling:* *ROUND {rank_data['round_number']}* — _{rank_data['round_name']}_\n\n"
                f"💡 *Expert Round Strategy:*\n{rank_data['strategy']}\n\n"
                f"{choice_draft}\n\n"
                f"📄 _Delivering your official PDF Choice Sheet below..._"
            )
            await send_text(sender, roadmap_msg)

            try:
                _, pdf_url = await generate_choice_sheet_file(
                    db=db,
                    cutoff=cutoff_val,
                    community=comm_val,
                    preferred_branches=profile.preferred_branches or None,
                    preferred_colleges=pref_colls,
                    session_key=session_key,
                )
                await send_document(
                    to=sender,
                    document_url=pdf_url,
                    caption=(
                        f"📄 *Official TNEA Choice Sheet ({comm_val} - {cutoff_val:g})*\n"
                        f"Personalized for {dist} region. Ready for choice locking!"
                    ),
                    filename=f"TNEA_Choice_Sheet_{int(cutoff_val)}.pdf",
                )
            except Exception as pdf_e:
                logger.error("matchmaker_pdf_delivery_failed", error=str(pdf_e))

            cta_buttons = [
                ("btn_download_pdf", "Download PDF"),
                ("btn_change_dist", "Change District"),
                ("btn_contact", "Talk to Counselor"),
            ]
            await send_interactive_buttons(
                sender, "💡 *Next Steps for Choice Filling:*", cta_buttons
            )
            return True

    return True


def _build_dynamic_reply_buttons(
    query: str, answer: str, profile: Any
) -> list[tuple[str, str]]:
    """Build exactly 3 contextual WhatsApp quick-reply buttons based on response.

    Rules:
    - Maximum 3 buttons per WhatsApp interactive message.
    - Each button title must be <= 20 characters.
    - After cutoff inquiry: [3-Tier Choice List], [Fee Details], [Compare College]
    - After college comparison: [Download PDF Sheet], [Hostel & Campus], [Other Branches]
    - After choice list: [Download PDF], [Change District], [Talk to Counselor]
    - Default turns: [Find My College], [Check Cutoff], [Placement Stats]
    """
    q_low = query.lower()
    ans_low = answer.lower()

    # 1. After choice list inquiry / recommendation
    if (
        any(
            k in q_low
            for k in (
                "choice",
                "recommend",
                "ambitious",
                "order draft",
                "choice list",
            )
        )
        or "3-tier" in ans_low
        or "choice filling" in ans_low
    ):
        return [
            ("btn_download_pdf", "Download PDF"),
            ("btn_change_dist", "Change District"),
            ("btn_contact", "Talk to Counselor"),
        ]

    # 2. After college comparison
    if (
        any(
            k in q_low
            for k in (
                "compare",
                " vs ",
                "versus",
                "difference between",
                "better than",
            )
        )
        or "comparison" in ans_low
        or (
            " vs " in ans_low
            and ("college" in ans_low or "skcet" in ans_low or "psg" in ans_low)
        )
    ):
        return [
            ("btn_download_pdf", "Download PDF Sheet"),
            ("btn_campus", "Hostel & Campus"),
            ("btn_courses", "Other Branches"),
        ]

    # 3. After cutoff inquiry
    if (
        any(
            k in q_low
            for k in (
                "cutoff",
                "cut-off",
                "cut off",
                "mark",
                "marks",
                "maths",
                "physics",
                "chemistry",
            )
        )
        or "cutoff marks" in ans_low
        or "closing cutoff" in ans_low
    ):
        return [
            ("btn_choice_list", "3-Tier Choice List"),
            ("btn_fees", "Fee Details"),
            ("btn_colleges", "Compare College"),
        ]

    # 4. After placement inquiry
    if (
        any(
            k in q_low
            for k in (
                "placement",
                "package",
                "ctc",
                "recruiter",
                "salary",
                "lpa",
            )
        )
        or "highest ctc" in ans_low
        or "average ctc" in ans_low
    ):
        return [
            ("btn_cutoff", "Check Cutoff"),
            ("btn_choice_list", "3-Tier Choice List"),
            ("btn_fees", "Fee Details"),
        ]

    # 5. After rank prediction inquiry
    if (
        any(
            k in q_low
            for k in (
                "rank",
                "round",
                "predictor",
                "overall rank",
                "community rank",
            )
        )
        or "predicted state overall rank" in ans_low
    ):
        return [
            ("btn_choice_list", "3-Tier Choice List"),
            ("btn_placements", "Placement Stats"),
            ("btn_colleges", "Compare College"),
        ]

    # 6. Default / General turns
    if getattr(profile, "calculated_cutoff", None) is not None:
        return [
            ("btn_rank_predictor", "Rank Predictor"),
            ("btn_choice_list", "3-Tier Choice List"),
            ("btn_placements", "Placement Stats"),
        ]

    return [
        ("btn_matchmaker", "Find My College"),
        ("btn_cutoff", "Check Cutoff"),
        ("btn_placements", "Placement Stats"),
    ]


async def _answer_student_task(message: ParsedMessage) -> None:
    """Run the RAG pipeline in background with its own DB session."""
    if message.message_id:
        await mark_message_as_read(message.message_id)

    query = (message.text or "").strip()

    # ── 0. Handle WhatsApp Audio / Voice Note Transcriptions ──
    if message.message_type in ("audio", "voice") and message.media_id:
        from api.services.audio_service import transcribe_audio_message

        logger.info(
            "transcribing_incoming_voice_note",
            media_id=message.media_id,
            mime_type=message.mime_type,
            sender=message.sender,
        )
        transcript = await transcribe_audio_message(message.media_id)
        if transcript:
            query = transcript
            logger.info("voice_note_transcribed_successfully", transcript=transcript)
            # Reassure student by echoing back their transcribed question first
            await send_text(message.sender, f'🎙️ _Voice note:_ "{transcript}"')
        else:
            await send_text(
                message.sender,
                "🎙️ *I received your voice note*, but couldn't quite hear the audio clearly.\n\n"
                "Could you please try speaking again in a quiet place, or type your query? "
                "I'm happy to help with cutoffs, courses, and admissions! 🎓",
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

    try:
        async with async_session_factory() as db:
            stmt = (
                select(Escalation)
                .where(
                    Escalation.sender == session_key,
                    Escalation.status == "in_progress",
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
                )
                try:
                    conv = await get_or_create_conversation(db, session_key)
                    await append_turn(db, conv, "user", query)
                    active_esc.query_text += f"\n[Student Follow-up]: {query}"
                    await db.commit()
                except Exception as e:
                    logger.error("failed_to_log_paused_message", error=str(e))

                pause_notice = (
                    "⏳ *Your conversation is currently in active consultation with "
                    "an admission counselor.*\n\n"
                    "A human officer is reviewing your queries and will reply here "
                    "on WhatsApp.\n\n"
                    "💡 _To switch back to automated AI mode at any time, "
                    "reply with */resume*._"
                )
                await send_text(message.sender, pause_notice)
                return
    except Exception as esc_check_err:
        logger.warning("escalation_check_skipped", error=str(esc_check_err))

    if await _handle_location_query(message.sender, query):
        return

    if await _handle_contact_query(message.sender, query):
        return

    if await _handle_download_pdf_query(message.sender, query, session_key):
        return

    if await _handle_change_district_query(message.sender, query, session_key):
        return

    if await _handle_matchmaker_flow(message.sender, query, session_key):
        return

    if await _handle_rank_predictor_query(message.sender, query, session_key):
        return

    if await _handle_placement_query(message.sender, query):
        return

    if await _handle_college_menu_query(message.sender, query):
        return

    if await _handle_choice_list_query(message.sender, query, session_key):
        return

    if is_greeting(query):
        welcome_txt = get_welcome_message()
        buttons = [
            ("btn_matchmaker", "Find My College"),
            ("btn_cutoff", "Check Cutoff"),
            ("btn_placements", "Placement Stats"),
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
            ("btn_matchmaker", "Find My College"),
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
        "btn_matchmaker": "Help me find colleges with the 3-step college matchmaker diagnostic",
        "btn_find_college": "Help me find colleges with the 3-step college matchmaker diagnostic",
        "btn_campus": "Tell me about the hostel rooms, mess food, sports facilities, and campus amenities.",
        "btn_placements": "What is the highest package, average CTC, and top recruiters for engineering colleges?",
        "btn_rank_predictor": "Predict my TNEA State Overall Rank and counselling round based on my cutoff marks.",
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
            formatted_answer = format_whatsapp_response(query, answer, sources)
            await send_text(message.sender, formatted_answer)

            # ── Contextual interactive quick-reply buttons on EVERY turn ──
            buttons = _build_dynamic_reply_buttons(query, formatted_answer, profile)
            await send_interactive_buttons(
                message.sender,
                "💡 *Quick Actions:*",
                buttons,
            )
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
