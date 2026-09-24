import re
from typing import List, Optional

GREETINGS = {
    "hi",
    "hello",
    "hey",
    "namaste",
    "vanakkam",
    "good morning",
    "good evening",
    "start",
    "help",
}


def is_greeting(text: str) -> bool:
    """Check if the student's message is a simple greeting."""
    cleaned = text.strip().lower()
    return cleaned in GREETINGS or any(cleaned.startswith(g + " ") for g in GREETINGS)


def get_welcome_message() -> str:
    """Return a warm, customizable WhatsApp welcome menu."""
    return (
        "👋 *Hey there! Welcome to Coligo Admission Guide!*\n\n"
        "I'm your senior peer guide for Tamil Nadu Engineering Admissions (TNEA).\n"
        "I can help you explore courses, check cutoff marks, fees, and campus facilities!\n\n"
        "💡 *What would you like to check today?*\n"
        "• Type *Cutoff for ECE* (or your branch)\n"
        "• Type *Maths 90, Physics 85, Chemistry 80* to calculate your TNEA cutoff\n"
        "• Type *Fee Structure* to view college fees\n"
        "• Type *Courses Offered* to explore branches"
    )


def get_course_list_menu_sections() -> List[dict]:
    """Structure sections for Meta WhatsApp List Selection Menus."""
    return [
        {
            "title": "💻 Computer Science & IT",
            "rows": [
                {
                    "id": "cse_info",
                    "title": "B.E. Computer Science",
                    "description": "CSE intake, cutoffs, and placements",
                },
                {
                    "id": "it_info",
                    "title": "B.Tech Information Tech",
                    "description": "IT curriculum and career paths",
                },
                {
                    "id": "aids_info",
                    "title": "B.Tech AI & Data Science",
                    "description": "Artificial Intelligence & ML specializations",
                },
            ],
        },
        {
            "title": "⚡ Electrical & Electronics",
            "rows": [
                {
                    "id": "ece_info",
                    "title": "B.E. Electronics & Comm",
                    "description": "ECE core circuits and embedded systems",
                },
                {
                    "id": "eee_info",
                    "title": "B.E. Electrical & Electronics",
                    "description": "EEE power systems and automation",
                },
            ],
        },
        {
            "title": "⚙️ Mechanical & Civil",
            "rows": [
                {
                    "id": "mech_info",
                    "title": "B.E. Mechanical Engg",
                    "description": "Robotics, CAD, and manufacturing",
                },
                {
                    "id": "civil_info",
                    "title": "B.E. Civil Engineering",
                    "description": "Structural and environmental engineering",
                },
            ],
        },
    ]


def calculate_tnea_cutoff(text: str) -> Optional[float]:
    """Extract Maths, Physics, and Chemistry marks from text and calculate official TNEA Cutoff out of 200.

    Official TNEA Formula: Maths + (Physics / 2) + (Chemistry / 2)
    """
    cleaned = text.lower()
    maths_match = re.search(r"\b(?:maths?|mathes|m)\b\D*(\d{1,3})", cleaned)
    physics_match = re.search(r"\b(?:physics?|phy|p)\b\D*(\d{1,3})", cleaned)
    chem_match = re.search(r"\b(?:chemistry?|chem|c)\b\D*(\d{1,3})", cleaned)

    if maths_match and physics_match and chem_match:
        m = float(maths_match.group(1))
        p = float(physics_match.group(1))
        c = float(chem_match.group(1))

        if 0 <= m <= 100 and 0 <= p <= 100 and 0 <= c <= 100:
            cutoff = m + (p / 2.0) + (c / 2.0)
            return round(cutoff, 2)
    return None


def format_whatsapp_response(query: str, answer: str, sources: List[str]) -> str:
    """Dynamically enhance WhatsApp response formatting based on query intent.

    Applies WhatsApp rich text styling (bold headers, bullet styling, and source tags).
    """
    cleaned_answer = answer.strip()
    # Convert markdown double asterisks (**text**) to WhatsApp single asterisks (*text*)
    cleaned_answer = re.sub(r"\*\*(.*?)\*\*", r"*\1*", cleaned_answer)
    lower_query = query.lower()

    # 1. Automatic Cutoff Calculation if student typed marks
    calculated_cutoff = calculate_tnea_cutoff(query)
    if calculated_cutoff is not None:
        calc_header = f"🎯 *Calculated TNEA Cutoff*: *{calculated_cutoff} / 200*\n\n"
        cleaned_answer = calc_header + cleaned_answer

    # 1b. Comparative Analysis Formatting
    elif any(
        k in lower_query for k in ("compare", "versus", "vs", "difference", "better")
    ):
        if "📊 *Branch & Cutoff" not in cleaned_answer:
            cleaned_answer = (
                f"📊 *Branch & Cutoff Comparative Analysis*\n\n{cleaned_answer}"
            )

    # 2. Format Cutoff Query Responses
    elif any(k in lower_query for k in ("cutoff", "cut-off", "mark", "marks", "rank")):
        if ("tnea" in lower_query or "mark" in lower_query) and not any(
            neg in cleaned_answer.lower()
            for neg in ("don't have", "not available", "missing", "sorry")
        ):
            hint = "\n\n💡 *TNEA Cutoff Formula*: `Maths + (Physics / 2) + (Chemistry / 2)` (Max 200)"
            if "TNEA Cutoff Formula" not in cleaned_answer:
                cleaned_answer += hint

    # 3. Format Fee Query Responses (only if answer is actually about fees)
    elif any(
        k in lower_query for k in ("fee", "fees", "tuition", "hostel")
    ) and not any(c in cleaned_answer for c in ("🎯", "📊", "Cutoff", "cutoff")):
        if "💳 *Fee" not in cleaned_answer:
            cleaned_answer = f"💳 *Fee Structure & Details*\n\n{cleaned_answer}"

    # 4. Format Location / Travel Queries
    elif any(
        k in lower_query
        for k in ("location", "where", "address", "reach", "bus", "direction")
    ):
        if "📍 *Campus Location*" not in cleaned_answer:
            cleaned_answer = (
                f"📍 *Campus Location & Transportation*\n\n{cleaned_answer}"
            )

    # 5. Format Course / Branch Queries
    elif any(
        k in lower_query
        for k in ("course", "branch", "cse", "ece", "mech", "eee", "it", "aids")
    ):
        if "🎓 *Academic Program Information*" not in cleaned_answer:
            cleaned_answer = f"🎓 *Academic Branch Details*\n\n{cleaned_answer}"

    # 6. Attach Source Document References (if available)
    # The user requested to remove the source template from the final WhatsApp message.

    return cleaned_answer
