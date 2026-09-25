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


def _resolve_cutoff(
    raw_text: str,
    state_cutoff: float | None,
    profile_cutoff: float | None,
) -> tuple[dict[str, float] | None, float | None]:
    """Extract marks or direct cutoff with fallback to state and profile."""
    marks, direct_cutoff = extract_marks_from_text(raw_text)
    calculated_cutoff = state_cutoff

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
    elif profile_cutoff is not None:
        calculated_cutoff = profile_cutoff

    return marks, calculated_cutoff


def _determine_intent(
    lower_text: str, calculated_cutoff: float | None, colleges: list[str]
) -> str:
    """Classify user intent into choice_filling, cutoff_query, or general_faq."""
    is_choice_filling = any(kw in lower_text for kw in CHOICE_KEYWORDS)
    if is_choice_filling and calculated_cutoff is not None:
        return "choice_filling"
    if calculated_cutoff is not None or "cutoff" in lower_text or colleges:
        return "cutoff_query"
    return "general_faq"


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

    # 2. Retrieve persistent student profile memory
    session_key = state.get("session_key", "")
    from api.services.student_profile_service import (
        get_student_profile,
        update_student_profile,
    )

    profile = get_student_profile(session_key) if session_key else None

    # 3. Extract community (fallback to profile)
    community = (
        state.get("community")
        or _detect_community(raw_text)
        or (profile.community if profile else None)
    )

    # 4. Deterministic mark & cutoff evaluation (fallback to profile)
    prof_cutoff = profile.calculated_cutoff if profile else None
    marks, calculated_cutoff = _resolve_cutoff(
        raw_text, state.get("calculated_cutoff"), prof_cutoff
    )

    # 5. Extract college names
    colleges = detect_college_keywords(raw_text)

    # 6. Extract branch preferences (fallback to profile)
    detected_branches = _detect_branches(lower)
    if not detected_branches and profile and profile.preferred_branches:
        detected_branches = list(profile.preferred_branches)

    # 7. Update persistent profile memory with newly detected facts
    if session_key:
        update_student_profile(
            session_key=session_key,
            cutoff=calculated_cutoff,
            community=community,
            maths=marks.get("maths") if marks else None,
            physics=marks.get("physics") if marks else None,
            chemistry=marks.get("chemistry") if marks else None,
            colleges=colleges or None,
            branches=detected_branches or None,
        )

    # 8. Determine intent
    intent = _determine_intent(lower, calculated_cutoff, colleges)

    return {
        "intent": intent,
        "marks": marks or state.get("marks"),
        "calculated_cutoff": calculated_cutoff,
        "community": community,
        "colleges": colleges,
        "branches": detected_branches or state.get("branches"),
        "is_escalated": False,
    }
