from typing import Any

from api.core.logging import get_logger
from api.services.agent.math_evaluator import calculate_tnea_cutoff
from api.services.agent.state import AgentState
from api.services.llm_service import generate_response_from_llm
from api.services.rag_service import (
    HISTORY_BLOCK_TEMPLATE,
    SYSTEM_PROMPT_TEMPLATE,
    validate_numeric_facts,
)

logger = get_logger(__name__)


def _build_header_prefix(marks: dict[str, float] | None, cutoff: float | None) -> str:
    """Build deterministic calculation summary header."""
    if marks:
        try:
            _, explanation = calculate_tnea_cutoff(
                marks["maths"], marks["physics"], marks["chemistry"]
            )
            return f"{explanation}\n\n"
        except Exception:
            pass
    if cutoff is not None:
        return f"🎯 **TNEA Cutoff**: **{cutoff:g} / 200.0**\n\n"
    return ""


def _build_ungrounded_msg(
    header_prefix: str,
    colleges: list[str],
    community: str | None,
    cutoff: float | None,
) -> str:
    """Build honest boundary response when data is not grounded."""
    colleges_str = (
        ", ".join(c.title() for c in colleges) if colleges else "the requested colleges"
    )
    comm_str = f" for the {community} community" if community else ""
    cutoff_str = f" with your cutoff of {cutoff:g}" if cutoff is not None else ""

    return (
        f"{header_prefix}"
        f"I could not locate verified official cutoff records for "
        f"{colleges_str}{comm_str}{cutoff_str} in our documents.\n\n"
        f"• Verify latest closing ranks at tneaonline.org.\n"
        f"• You can also contact the college admission desk directly."
    )


def _compile_grounding_context(
    chunks: list[dict[str, Any]], max_chars: int = 7500
) -> str:
    """Concatenate retrieved document chunks with character boundary limit."""
    parts = []
    total_chars = 0
    for c in chunks[:4]:
        doc_ref = c.get("document_ref", "document")
        idx = c.get("chunk_index", 0)
        text = (c.get("text_content", "") or "").strip()
        if total_chars + len(text) > max_chars:
            remaining = max(0, max_chars - total_chars)
            if remaining > 200:
                text = text[:remaining] + "..."
                parts.append(f"--- Source: {doc_ref} (Chunk Index: {idx}) ---\n{text}")
            break
        parts.append(f"--- Source: {doc_ref} (Chunk Index: {idx}) ---\n{text}")
        total_chars += len(text)
    return "\n\n".join(parts)


def _build_conversational_guidelines(lang_pref: str, is_distress: bool) -> str:
    """Build empathetic tone directives for Tanglish and student anxiety."""
    guidelines = []
    if lang_pref == "tanglish":
        guidelines.append(
            "[Tone Directive: The student communicated in Tanglish. Respond "
            "warmly and conversationally, mixing friendly Tamil phrases "
            "naturally (e.g. 'Unga cutoff-ku...', '...chance irukku 🟢'), "
            "while keeping numbers and college codes exact.]"
        )
    elif lang_pref == "tamil":
        guidelines.append(
            "[Tone Directive: The student communicated in Tamil. Respond with "
            "a supportive, clear Tamil/English bilingual explanation.]"
        )

    if is_distress:
        guidelines.append(
            "[Empathy Directive: The student is concerned about their score. "
            "Offer encouraging guidance highlighting that Round 3/4 offer "
            "viable engineering paths across colleges, along with 7.5% quota.]"
        )

    return ("\n" + "\n".join(guidelines) + "\n") if guidelines else ""


async def synthesizer_node(state: AgentState) -> dict[str, Any]:
    """Synthesize admission counselling answer with citations and cutoffs."""
    raw_message = state.get("raw_message", "")
    history_str = state.get("history_text", "")
    chunks = state.get("retrieved_chunks") or []
    sources = state.get("sources") or []
    is_grounded = state.get("is_grounded", True)
    community = state.get("community")
    marks = state.get("marks")
    cutoff = state.get("calculated_cutoff")
    colleges = state.get("colleges") or []

    # 1. Deterministic Calculation Header
    header_prefix = _build_header_prefix(marks, cutoff)

    # 2. Honest boundary fallback if not grounded
    if not is_grounded or not chunks:
        msg = _build_ungrounded_msg(header_prefix, colleges, community, cutoff)
        return {"response_text": msg, "sources": sources}

    # 3. Assemble Grounding Context & Conversational Directives
    compiled_context = _compile_grounding_context(chunks)
    guideline_str = _build_conversational_guidelines(
        state.get("language_preference", "english"),
        state.get("is_distress", False),
    )

    llm_question = raw_message
    if cutoff is not None:
        llm_question = f"[System Calculated Cutoff: {cutoff:g} / 200] {raw_message}"
    if guideline_str:
        llm_question = f"{guideline_str}\n{llm_question}"

    prompt = SYSTEM_PROMPT_TEMPLATE.format(
        context=compiled_context,
        question=llm_question,
        history=(
            HISTORY_BLOCK_TEMPLATE.format(history=history_str) if history_str else ""
        ),
    )

    # 4. Generate with Groq / configured LLM
    try:
        raw_response = await generate_response_from_llm(prompt)
    except Exception as e:
        logger.error("synthesizer_llm_failed", error=str(e))
        raw_response = (
            "We are currently experiencing high inquiry volume. "
            "Please check back shortly or refer to the official TNEA portal."
        )

    is_valid = validate_numeric_facts(
        raw_response, compiled_context, cutoff, query_text=raw_message
    )
    if not is_valid:
        logger.warning("numeric_validation_failed_in_agent_synthesis")
        raw_response += (
            "\n\n⚠️ _Some numbers may not match official records. "
            "Please verify with the college website or TNEA portal._"
        )

    # Append Sources
    if sources:
        raw_response += f"\n\n📌 Source: {', '.join(sources)}"

    final_output = f"{header_prefix}{raw_response}".strip()

    return {
        "response_text": final_output,
        "sources": sources,
    }
