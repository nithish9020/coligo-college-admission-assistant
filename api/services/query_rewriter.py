from api.core.logging import get_logger
from api.services.llm_service import generate_response_from_llm

logger = get_logger(__name__)

CONDENSE_PROMPT_TEMPLATE = """Given the conversation below and a follow-up \
message, rewrite the follow-up as a standalone question that can be understood \
without the conversation.

Rules:
- Resolve pronouns and ellipsis ("it", "that branch", "what about ECE?") using \
the conversation.
- Keep the user's original intent and any details they gave (community, marks, \
rank, branch, college, year).
- If the follow-up is already a standalone question, return it unchanged.
- Output ONLY the rewritten question. No preamble, no quotes, no explanation.

Conversation:
{history}

Follow-up message:
{question}

Standalone question:"""

# A condensed question should be one sentence. Anything much longer means the
# model ignored the "output only the question" instruction and started
# explaining itself, so the raw text is safer to embed than its rambling.
MAX_CONDENSED_CHARS = 500


async def condense_question(history: str, question: str) -> str:
    """Rewrite a follow-up into a standalone question for retrieval.

    Returns the original question unchanged when there is no history, when
    rewriting is not useful, or on any failure — a bad rewrite must never be
    worse than today's stateless behaviour.
    """
    if not history.strip():
        return question

    prompt = CONDENSE_PROMPT_TEMPLATE.format(history=history, question=question)

    try:
        condensed = (await generate_response_from_llm(prompt)).strip()
    except Exception as e:
        logger.warning("question_condense_failed", error=str(e))
        return question

    if not condensed or len(condensed) > MAX_CONDENSED_CHARS:
        logger.warning(
            "question_condense_rejected",
            reason="empty" if not condensed else "too_long",
            length=len(condensed),
        )
        return question

    logger.info("question_condensed", original=question, condensed=condensed)
    return condensed
