"""AI Chatbot View with Streaming and Contextual Visual Charts."""

import streamlit as st

from app.services.agent_streamer import stream_agent_response
from app.services.chart_builder import (
    build_cutoff_comparison_chart,
    build_placement_comparison_chart,
    build_quota_pie_chart,
)


def render_chat_view() -> None:
    """Render interactive AI chat interface with live streaming & contextual charts."""
    st.markdown("## 💬 Coligo TNEA Admission Assistant")
    st.caption(
        "Ask questions about engineering college cutoffs, courses, hostel fees, "
        "placements, and choice filling."
    )

    session_key = st.session_state.get("session_key", "whatsapp:anonymous")

    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {
                "role": "assistant",
                "content": (
                    "👋 Hello! I am Coligo, your official TNEA Counselling Assistant. "
                    "I can help you check cutoff marks, compare colleges, and generate "
                    "your personalized 3-tier choice filling order. How can I help?"
                ),
                "sources": [],
            }
        ]

    # Quick action prompt chips
    st.markdown("**💡 Quick Questions:**")
    q_col1, q_col2, q_col3, q_col4 = st.columns(4)
    quick_query = None

    with q_col1:
        if st.button("📊 SKCET vs PSG Cutoffs", use_container_width=True):
            quick_query = "Compare SKCET vs PSG Tech cutoffs for CSE, IT, and ECE."
    with q_col2:
        if st.button("💼 Highest CTC Placements", use_container_width=True):
            quick_query = (
                "What is the highest package and average CTC for SKCET and PSG Tech?"
            )
    with q_col3:
        if st.button("📋 My 3-Tier Choice List", use_container_width=True):
            cutoff = st.session_state.get("cutoff", 186.5)
            comm = st.session_state.get("community", "BC")
            quick_query = (
                f"Suggest my 3-tier choice filling order for cutoff {cutoff} "
                f"and {comm} community in Coimbatore."
            )
    with q_col4:
        if st.button("📈 Predict My State Rank", use_container_width=True):
            cutoff = st.session_state.get("cutoff", 186.5)
            comm = st.session_state.get("community", "BC")
            quick_query = (
                f"Predict my TNEA State Overall Rank and counselling round "
                f"for cutoff {cutoff} in {comm}."
            )

    # Render chat history
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander("📚 Verified Official Sources"):
                    for s in msg["sources"]:
                        st.markdown(f"- `{s}`")

    # Handle incoming user input
    user_input = st.chat_input("Type your admission query here...") or quick_query

    if user_input:
        st.session_state["messages"].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing cutoff databases & guidelines..."):
                stream_gen, sources, full_text = stream_agent_response(
                    query=user_input, session_key=session_key
                )

            # Stream response in real time
            response_text = st.write_stream(stream_gen)

            if sources:
                with st.expander("📚 Verified Official Sources"):
                    for s in sources:
                        st.markdown(f"- `{s}`")

            # Contextual inline charts based on query context
            u_low = user_input.lower()
            if any(
                k in u_low
                for k in ("cutoff", "compare", "psg", "skcet", "mark", "branch")
            ):
                st.markdown("---")
                st.markdown("#### 📊 Comparative Cutoff Visualization")
                chart = build_cutoff_comparison_chart(
                    selected_colleges=["SKCET", "PSG Tech", "CIT", "KCT"],
                    community=st.session_state.get("community", "BC"),
                )
                st.altair_chart(chart, use_container_width=True)

            elif any(
                k in u_low
                for k in ("placement", "package", "ctc", "recruiter", "salary", "lpa")
            ):
                st.markdown("---")
                st.markdown("#### 💼 Institution Placement Analytics")
                p_chart = build_placement_comparison_chart()
                st.altair_chart(p_chart, use_container_width=True)

            elif any(
                k in u_low
                for k in ("reservation", "quota", "community", "seats", "matrix")
            ):
                st.markdown("---")
                st.markdown("#### 🥧 Tamil Nadu Government Quota Breakdown")
                q_chart = build_quota_pie_chart()
                st.altair_chart(q_chart, use_container_width=True)

        st.session_state["messages"].append(
            {"role": "assistant", "content": response_text, "sources": sources}
        )
