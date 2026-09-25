import re
from typing import Optional, Tuple

from api.core.logging import get_logger

logger = get_logger(__name__)

COLLEGE_CODES: dict[str, dict[str, str]] = {
    "skcet": {
        "name": "Sri Krishna College of Engineering and Technology (Autonomous)",
        "code": "2722",
        "location": "Kuniamuthur, Coimbatore",
    },
    "psg": {
        "name": "PSG College of Technology (Autonomous)",
        "code": "2006",
        "location": "Peelamedu, Coimbatore",
    },
    "psg tech": {
        "name": "PSG College of Technology (Autonomous)",
        "code": "2006",
        "location": "Peelamedu, Coimbatore",
    },
    "cit": {
        "name": "Coimbatore Institute of Technology (Autonomous)",
        "code": "2007",
        "location": "Civil Aerodrome Post, Coimbatore",
    },
    "gct": {
        "name": "Government College of Technology (Autonomous)",
        "code": "2005",
        "location": "Thadagam Road, Coimbatore",
    },
    "kct": {
        "name": "Kumaraguru College of Technology (Autonomous)",
        "code": "2712",
        "location": "Saravanampatti, Coimbatore",
    },
    "kumaraguru": {
        "name": "Kumaraguru College of Technology (Autonomous)",
        "code": "2712",
        "location": "Saravanampatti, Coimbatore",
    },
    "bannari": {
        "name": "Bannari Amman Institute of Technology (Autonomous)",
        "code": "2702",
        "location": "Sathyamangalam, Erode",
    },
    "kongu": {
        "name": "Kongu Engineering College (Autonomous)",
        "code": "2711",
        "location": "Perundurai, Erode",
    },
    "psg itech": {
        "name": "PSG Institute of Technology and Applied Research",
        "code": "2377",
        "location": "Neelambur, Coimbatore",
    },
    "tce": {
        "name": "Thiagarajar College of Engineering (Autonomous)",
        "code": "5008",
        "location": "Thiruparankundram, Madurai",
    },
}

TNEA_FORMULA_REPLY = (
    "📊 *Official TNEA Cutoff Calculation (Out of 200 Marks):*\n\n"
    "Cutoff = *Mathematics* + (*Physics* ÷ 2) + (*Chemistry* ÷ 2)\n\n"
    "• Mathematics: Max 100 marks (weightage: 100%)\n"
    "• Physics: Max 50 marks (Score out of 100 ÷ 2)\n"
    "• Chemistry: Max 50 marks (Score out of 100 ÷ 2)\n\n"
    "💡 *Example:*\n"
    "If you scored Maths 96, Physics 90, Chemistry 88:\n"
    "👉 96 + (90 ÷ 2) + (88 ÷ 2) = 96 + 45 + 44 = *185.0 / 200.0*\n\n"
    "Simply reply with your subject marks (e.g. *Maths 95, Physics 90, Chemistry 88*) "
    "and I will calculate it and check your college chances!"
)

TNEA_DOCS_REPLY = (
    "📋 *Official TNEA Certificate Verification Checklist:*\n\n"
    "1. *10th Standard Mark Sheet* (Proof of Date of Birth)\n"
    "2. *11th & 12th (+2) Mark Sheets / Internet Copy*\n"
    "3. *Transfer Certificate (TC)* from last studied school\n"
    "4. *Permanent Community Certificate* (Card or e-Certificate) for "
    "BC, BCM, MBC & DNC, SC, SCA, ST\n"
    "5. *Nativity Certificate* (Electronic form / Digitally signed), "
    "if applicable\n"
    "6. *First Graduate Certificate & Joint Declaration*, if claiming "
    "FG tuition fee waiver\n"
    "7. *Special Reservation Certificate* (Sports, Ex-Servicemen, "
    "Differently Abled, or 7.5% Govt School Quota), if applicable."
)

TNEA_PROCESS_REPLY = (
    "🎓 *TNEA Engineering Admissions Step-by-Step Procedure:*\n\n"
    "1. *Online Registration & Document Upload:* Register on tneaonline.org\n"
    "2. *Random Number & Rank List Publication:* State overall & community rank list\n"
    "3. *Online Choice Filling (3 Days):* Add preferred colleges and "
    "branches in order\n"
    "4. *Tentative Allotment & Decision Confirmation:* Accept / "
    "Accept with Upward / Decline\n"
    "5. *Final Allotment Order:* Download allotment letter and report to "
    "college within deadline."
)

TNEA_SCHEDULE_REPLY = (
    "📅 *Official TNEA Counselling Schedule & Round Architecture:*\n\n"
    "• *Round 1:* Typically ranks 1 to 25,000 (Cutoff ~200.0 to 179.0)\n"
    "• *Round 2:* Typically ranks 25,001 to 65,000 (Cutoff ~178.9 to 145.0)\n"
    "• *Round 3:* Typically ranks 65,001 to 1,30,000 (Cutoff ~144.9 to 77.5)\n\n"
    "🕒 *Each Round 5-Day Lifecycle:*\n"
    "• *Days 1–3 (Choice Filling):* 3 full days to add & order college choices\n"
    "• *Day 4 (Tentative Allotment):* Result published by 10:00 AM\n"
    "• *Days 4–5 (Confirmation):* Confirm with Accept / Accept & Upward\n"
    "• *Day 6:* Final allotment release & college reporting date\n\n"
    "💡 Reply with *Upward Movement* to understand how to upgrade your seat!"
)

TNEA_UPWARD_MOVEMENT_REPLY = (
    "🚀 *How TNEA Upward Movement Works (The Golden Rule):*\n\n"
    "When you receive your tentative allotment, you get 5 confirmation options:\n\n"
    "1. ✅ *Accept and Join:* You are 100% happy with this seat and confirm "
    "admission.\n"
    "2. 🌟 *Accept and Upward (RECOMMENDED):* You KEEP your currently allotted "
    "seat as a guaranteed backup, BUT if a higher-priority choice from your list "
    "becomes vacant, TNEA upgrades you automatically! You NEVER lose your "
    "current seat.\n"
    "3. ❌ *Decline and Upward:* You reject the current seat and only wait for "
    "higher choices.\n"
    "4. ⏭️ *Decline and Next Round:* You skip to the next counselling round.\n"
    "5. 🚪 *Quit:* You exit TNEA counselling.\n\n"
    "💡 *Always select 'Accept and Upward' if you want a better college without "
    "risking your seat!*"
)


def match_instant_faq(query: str) -> Optional[Tuple[str, list[str]]]:
    """Check if query matches a deterministic institutional FAQ for sub-50ms reply."""
    q = query.strip().lower()

    # 1. College Code queries
    code_match = re.search(r"\b(?:code|counselling code|tnea code)\b", q)
    if code_match:
        for key, data in COLLEGE_CODES.items():
            if key in q:
                ans = (
                    f"🏫 *{data['name']}*\n\n"
                    f"• *TNEA College Code:* *{data['code']}*\n"
                    f"• *Location:* {data['location']}\n\n"
                    f"💡 Reply with *{key.upper()} cutoffs* or *fees* "
                    "to view detailed records!"
                )
                logger.info("instant_faq_hit", topic="college_code", college=key)
                return ans, [f"TNEA Official College Code Directory ({data['code']})"]

    # 2. Cutoff calculation formula
    if any(
        phrase in q
        for phrase in (
            "how to calculate cutoff",
            "calculate cutoff",
            "cutoff formula",
            "formula for cutoff",
            "how is cutoff calculated",
            "how cutoff is calculated",
            "cutoff calculation",
        )
    ):
        logger.info("instant_faq_hit", topic="cutoff_formula")
        return TNEA_FORMULA_REPLY, [
            "Directorate of Technical Education (DTE) Guidelines"
        ]

    # 3. Documents required
    if any(
        phrase in q
        for phrase in (
            "documents required",
            "certificates required",
            "documents needed",
            "certificates needed",
            "document verification",
            "what documents",
            "certificate list",
        )
    ):
        logger.info("instant_faq_hit", topic="documents_required")
        return TNEA_DOCS_REPLY, ["TNEA Official Verification Information Brochure"]

    # 4. Counselling stages
    if any(
        phrase in q
        for phrase in (
            "counselling process",
            "counseling process",
            "how counselling works",
            "counselling steps",
            "counselling stages",
            "tnea procedure",
        )
    ):
        logger.info("instant_faq_hit", topic="counselling_procedure")
        return TNEA_PROCESS_REPLY, ["TNEA Online Portal Handbook"]

    # 5. Counselling Round Schedule & Timeline
    if any(
        phrase in q
        for phrase in (
            "schedule",
            "timeline",
            "dates",
            "round 1",
            "round 2",
            "round 3",
            "counselling dates",
            "counselling schedule",
            "when is round",
        )
    ):
        logger.info("instant_faq_hit", topic="counselling_schedule")
        return TNEA_SCHEDULE_REPLY, ["TNEA Official Annual Schedule"]

    # 6. Upward Movement Explanation
    if any(
        phrase in q
        for phrase in (
            "upward movement",
            "upward",
            "what is upward",
            "accept and upward",
            "how upward works",
            "upward option",
        )
    ):
        logger.info("instant_faq_hit", topic="upward_movement")
        return TNEA_UPWARD_MOVEMENT_REPLY, ["TNEA Candidate Choice-Filling Guidance"]

    return None
