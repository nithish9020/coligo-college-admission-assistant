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
- If the student writes in colloquial Tanglish or Tamil (e.g. 'yenaku 185 cutoff \
cse kedaikuma', 'hostel fees evalo varum'), translate the intent into a clear \
English question (e.g. 'Can I get CSE with 185 cutoff in TNEA counselling?').
- If the user asks a general question like "which college" or "top colleges", DO \
NOT restrict it to a specific college from the history. Keep it general.
- If the follow-up is already a standalone question in English, return it unchanged.
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

_TANGLISH_KEYWORDS = (
    "yenaku",
    "enakku",
    "evalo",
    "evlo",
    "kedaikuma",
    "epdi",
    "iruku",
    "iruka",
    "panna",
    "solunga",
    "solungo",
)


def is_tanglish(text: str) -> bool:
    """Return True if message contains colloquial Tamil/Tanglish phrasing."""
    cleaned = text.lower()
    return any(w in cleaned for w in _TANGLISH_KEYWORDS)


async def condense_question(history: str, question: str) -> str:
    """Rewrite a follow-up or Tanglish query into a standalone question for retrieval.

    Returns the original question unchanged when there is no history and no
    Tanglish, or on any failure.
    """
    if not history.strip() and not is_tanglish(question):
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
