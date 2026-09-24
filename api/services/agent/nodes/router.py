import re
from typing import Any

from api.services.agent.math_evaluator import (
    calculate_tnea_cutoff,
    extract_marks_from_text,
)
from api.services.agent.state import AgentState
from api.services.rag_service import detect_college_keywords

COMMUNITIES = ["BCM", "MBC", "SCA", "OC", "BC", "SC", "ST"]

ESCALATION_KEYWORDS = [
    "management quota",
    "donation",
    "bribe",
    "buy seat",
    "direct admission fee",
    "agent commission",
    "seat booking",
    "capitation",
]

CHOICE_KEYWORDS = [
    "choice filling",
    "choice list",
    "choices for",
    "recommend college",
    "recommend colleges",
    "colleges can i get",
    "college can i get",
    "colleges for my cutoff",
    "where can i get",
    "which college can i get",
    "eligible colleges",
    "suggest colleges",
    "option list",
]

BRANCH_KEYS = ["cse", "ece", "it", "aids", "aiml", "eee", "mech", "civil", "csbs"]


def _detect_community(raw_text: str) -> str | None:
    for comm in COMMUNITIES:
        if re.search(rf"\b{comm}\b", raw_text, re.IGNORECASE):
            return comm.upper()
    return None


def _detect_branches(lower_text: str) -> list[str]:
    branches = []
    for bk in BRANCH_KEYS:
        if re.search(rf"\b{bk}\b", lower_text):
            branches.append(bk.upper())
    return branches


async def router_node(state: AgentState) -> dict[str, Any]:
    """Parse student query for marks, community, colleges, and intent."""
    raw_text = state.get("raw_message", "")
    lower = raw_text.lower()

    # 1. Check for sensitive out-of-scope / escalation intent
    for kw in ESCALATION_KEYWORDS:
        if kw in lower:
            reason = f"Inquiry regarding '{kw}' requires counselor review."
            return {
                "intent": "escalation",
                "is_escalated": True,
                "escalation_reason": reason,
            }

    # 2. Extract community
    community = state.get("community") or _detect_community(raw_text)

    # 3. Deterministic mark & cutoff evaluation
    marks, direct_cutoff = extract_marks_from_text(raw_text)
    calculated_cutoff = state.get("calculated_cutoff")

    if marks:
        try:
            calc_val, _ = calculate_tnea_cutoff(
                marks["maths"], marks["physics"], marks["chemistry"]
            )
            calculated_cutoff = calc_val
        except ValueError:
            pass
    elif direct_cutoff is not None:
        calculated_cutoff = direct_cutoff

    # 4. Extract college names
    colleges = detect_college_keywords(raw_text)

    # 5. Determine intent
    is_choice_filling = any(kw in lower for kw in CHOICE_KEYWORDS)
    if is_choice_filling and calculated_cutoff is not None:
        intent = "choice_filling"
    elif calculated_cutoff is not None or "cutoff" in lower or colleges:
        intent = "cutoff_query"
    else:
        intent = "general_faq"

    # 6. Extract branch preferences
    detected_branches = _detect_branches(lower)

    return {
        "intent": intent,
        "marks": marks or state.get("marks"),
        "calculated_cutoff": calculated_cutoff,
        "community": community,
        "colleges": colleges,
        "branches": detected_branches or state.get("branches"),
        "is_escalated": False,
    }
