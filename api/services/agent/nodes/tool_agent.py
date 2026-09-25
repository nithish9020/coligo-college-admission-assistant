from typing import Any, List

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.logging import get_logger
from api.services.agent.llm_factory import get_agent_chat_model
from api.services.agent.state import AgentState
from api.services.agent.tools import create_agent_tools

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are Coligo, the official AI TNEA College Admission Assistant.
You guide students on engineering college cutoffs, courses, 3-tier choice lists,
fee structures, and campus details.

CORE RULES:
1. Always ground your answers in verified database facts using tools:
   - Call `list_available_colleges` when asked what colleges are available or in
     Tanglish like 'unga kita endha college iruku'.
   - Call `query_college_cutoffs` for cutoffs of colleges like SKCET, PSG, CIT,
     Bannari Amman, Kongu, or Kumaraguru.
   - Call `get_choice_filling_recommendations_tool` when cutoff and community are
     provided to generate 3-tier Ambitious / Target / Safe recommendations.
   - Call `search_admission_brochures` for questions on fees, hostel, placements,
     and campus rules.
   - Call `calculate_cutoff_from_marks` if Maths, Physics, Chemistry marks are given.
2. Language & Empathy:
   - If the student writes in Tanglish, reply warmly in friendly Tanglish.
   - If the student writes in Tamil, reply in clear Tamil/English text.
   - If in English, reply in friendly English.
3. WhatsApp Formatting:
   - Use *bold* for key terms, college names, and numbers.
   - Use clean bullet points and emojis (🎓, 📊, 🏫, 🌟, 🎯, 🛡️).
   - Keep answers clear and mobile-friendly.
4. Multi-Turn Context:
   - When the student previously provided cutoff/marks and now gives their community,
     call `get_choice_filling_recommendations_tool` with the known facts.
"""


def _build_agent_messages(
    raw_message: str, history_text: str, state: AgentState
) -> list[Any]:
    messages: list[Any] = [SystemMessage(content=SYSTEM_PROMPT)]
    if history_text:
        messages.append(
            SystemMessage(content=f"Previous Conversation:\n{history_text}")
        )

    profile_info = []
    if state.get("calculated_cutoff"):
        profile_info.append(f"Cutoff: {state['calculated_cutoff']}")
    if state.get("community"):
        profile_info.append(f"Community: {state['community']}")
    if state.get("colleges"):
        profile_info.append(f"Target Colleges: {', '.join(state['colleges'])}")
    if state.get("branches"):
        profile_info.append(f"Preferred Branches: {', '.join(state['branches'])}")
    if profile_info:
        messages.append(
            SystemMessage(content=f"Student Profile Context: {', '.join(profile_info)}")
        )

    messages.append(HumanMessage(content=raw_message))
    return messages


async def _execute_tool_loop(
    llm: Any, tool_map: dict[str, Any], messages: list[Any]
) -> List[str]:
    sources: List[str] = []
    for _ in range(4):
        ai_msg = await llm.ainvoke(messages)
        messages.append(ai_msg)
        if not getattr(ai_msg, "tool_calls", None):
            break

        for tc in ai_msg.tool_calls:
            t_name = tc["name"]
            t_args = tc["args"]
            logger.info("agent_executing_tool", tool=t_name, args=t_args)
            sources.append(t_name)
            tool_fn = tool_map.get(t_name)
            if tool_fn:
                try:
                    tool_output = await tool_fn.ainvoke(t_args)
                except Exception as tool_err:
                    tool_output = f"Tool execution failed: {tool_err}"
            else:
                tool_output = f"Tool '{t_name}' not found."
            messages.append(
                ToolMessage(content=str(tool_output), tool_call_id=tc["id"])
            )
    return sources


async def _synthesize_final_text(
    llm: Any, messages: list[Any], sources: List[str]
) -> str:
    raw_content = messages[-1].content
    final_text = (
        "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in raw_content
        )
        if isinstance(raw_content, list)
        else str(raw_content)
    )

    if not final_text.strip() or isinstance(messages[-1], ToolMessage):
        logger.info("tool_agent_synthesizing_final_answer")
        messages.append(
            HumanMessage(
                content="Based on the verified tool output above, provide a clear, "
                "friendly, and helpful WhatsApp response for the student."
            )
        )
        try:
            synth_ai = await llm.ainvoke(messages)
            synth_content = synth_ai.content
            final_text = (
                "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in synth_content
                )
                if isinstance(synth_content, list)
                else str(synth_content)
            )
        except Exception as synth_err:
            logger.warning("agent_synthesis_failed", error=str(synth_err))

    if not final_text.strip() and sources:
        for m in reversed(messages):
            if isinstance(m, ToolMessage) and m.content:
                final_text = str(m.content)
                break

    return final_text


async def tool_agent_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    """Execute LangChain Tool-Calling loop grounded in PostgreSQL data."""
    db: AsyncSession = config["configurable"]["db"]
    raw_message = state.get("raw_message", "")
    history_text = state.get("history_text", "")
    session_key = state.get("session_key", "")

    tools = create_agent_tools(db, session_key=session_key)
    tool_map = {t.name: t for t in tools}
    llm = get_agent_chat_model().bind_tools(tools)

    messages = _build_agent_messages(raw_message, history_text, state)
    sources = await _execute_tool_loop(llm, tool_map, messages)
    final_text = await _synthesize_final_text(llm, messages, sources)

    logger.info("tool_agent_completed", tool_calls_count=len(sources))
    return {
        "response_text": final_text,
        "sources": sources,
    }
