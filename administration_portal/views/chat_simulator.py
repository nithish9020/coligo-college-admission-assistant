import uuid

import streamlit as st
from utils.api_client import APIError, send_chat_message
from utils.styling import (
    page_header,
    render_footer,
)


def render_chat_simulator() -> None:
    page_header(
        "💬",
        "AI Admission Assistant Playground",
        "Interactive test simulator for the multi-college TNEA RAG counseling chatbot",
    )

    if (
        "chat_session_id" not in st.session_state
        or not st.session_state.chat_session_id
    ):
        st.session_state.chat_session_id = f"test_{uuid.uuid4().hex[:8]}"

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {
                "role": "assistant",
                "content": "Vanakkam! I am Coligo, your TNEA counseling assistant. Ask me about cutoff marks, college comparisons, courses, or type your marks to calculate eligibility!",
                "sources": [],
            }
        ]

    # Controls bar
    col_sess, col_clear = st.columns([3, 1])
    with col_sess:
        st.caption(
            f"Session ID: `{st.session_state.chat_session_id}` (24h memory active)"
        )
    with col_clear:
        if st.button("🔄 New Conversation", use_container_width=True):
            st.session_state.chat_session_id = f"test_{uuid.uuid4().hex[:8]}"
            st.session_state.chat_messages = [
                {
                    "role": "assistant",
                    "content": "Started a new conversation! How can I help you with your college admissions today?",
                    "sources": [],
                }
            ]
            st.rerun()

    # Quick test prompts
    st.markdown("**Quick test prompts:**")
    qp1, qp2, qp3 = st.columns(3)
    prompt_to_send = None
    if qp1.button("🎯 Cutoff: 95, 80, 85 (BC)", use_container_width=True):
        prompt_to_send = "My marks are Maths: 95, Physics: 80, Chemistry: 85. My community is BC. Which colleges can I get for CSE?"
    if qp2.button("🏫 Compare SKCET & CIT", use_container_width=True):
        prompt_to_send = "Compare SKCET and CIT for Computer Science and placements."
    if qp3.button("📘 PSG ECE Cutoff", use_container_width=True):
        prompt_to_send = (
            "What is the closing cutoff for ECE at PSG College of Technology?"
        )

    # Render previous conversation history
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander("📌 Cited Sources"):
                    for src in msg["sources"]:
                        st.markdown(f"- `{src}`")

    # Handle input from chat_input or quick prompt
    user_input = st.chat_input(
        "Ask a question about colleges, cutoffs, or admissions..."
    )
    query = prompt_to_send or user_input

    if query:
        # Append user message
        st.session_state.chat_messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        # Query backend /chat endpoint
        with st.chat_message("assistant"):
            with st.spinner("Searching documents & generating answer..."):
                try:
                    res = send_chat_message(
                        message=query,
                        session_id=st.session_state.chat_session_id,
                    )
                    reply_text = res.get("response", "I could not retrieve an answer.")
                    sources = res.get("sources", [])

                    st.markdown(reply_text)
                    if sources:
                        with st.expander("📌 Cited Sources"):
                            for src in sources:
                                st.markdown(f"- `{src}`")

                    st.session_state.chat_messages.append(
                        {
                            "role": "assistant",
                            "content": reply_text,
                            "sources": sources,
                        }
                    )
                except APIError as e:
                    err_msg = f"⚠️ Error communicating with assistant: {e.message}"
                    st.error(err_msg)
                    st.session_state.chat_messages.append(
                        {"role": "assistant", "content": err_msg, "sources": []}
                    )

    render_footer()
