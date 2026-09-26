import streamlit as st
from utils.api_client import APIError, list_colleges
from utils.styling import (
    badge,
    page_header,
    render_footer,
    render_stat_row,
    row_icon_html,
)


def render_admin_dashboard() -> None:
    try:
        colleges = list_colleges(st.session_state.token)
    except APIError as e:
        st.error(e.message)
        return

    page_header(
        "\U0001f3e0", "Admin Dashboard", "Overview across all registered colleges"
    )

    total_courses = sum(c["course_count"] for c in colleges)
    total_brochures = sum(c["brochure_count"] for c in colleges)
    active_colleges = sum(1 for c in colleges if c["is_active"])

    render_stat_row(
        [
            ("Total Colleges", len(colleges), "", "Registered on platform"),
            ("Active Colleges", active_colleges, "", "Currently active"),
            ("Total Courses", total_courses, "", "Across all colleges"),
            ("Total Brochures", total_brochures, "", "Uploaded in total"),
        ]
    )

    # Bot & RAG Ingestion Metrics
    try:
        from utils.api_client import get_analytics_summary

        analytics = get_analytics_summary(st.session_state.token)
        conv = analytics.get("conversations", {})
        esc = analytics.get("escalations", {})
        doc = analytics.get("documents", {})

        st.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)
        render_stat_row(
            [
                (
                    "Chat Threads",
                    conv.get("total_threads", 0),
                    "",
                    "Student sessions",
                ),
                (
                    "Total Messages",
                    conv.get("total_messages", 0),
                    "",
                    f"{conv.get('avg_turns_per_thread', 0):.1f} avg turns/user",
                ),
                (
                    "Pending Escalations",
                    esc.get("pending", 0),
                    "",
                    f"{esc.get('resolved', 0)} resolved",
                ),
                (
                    "RAG Chunks",
                    doc.get("total_chunks", 0),
                    "",
                    f"Across {doc.get('total_documents', 0)} documents",
                ),
            ]
        )
    except Exception:
        pass

    st.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="coligo-card-header">\U0001f3eb Recent Colleges</div>',
        unsafe_allow_html=True,
    )

    recent = sorted(colleges, key=lambda c: c["created_at"], reverse=True)[:5]
    if not recent:
        st.info("No colleges have registered yet.")
    else:
        header = st.columns([2.5, 2, 1, 1, 1, 1])
        for col, label in zip(
            header,
            [
                "COLLEGE NAME",
                "CONTACT PERSON",
                "COURSES",
                "BROCHURES",
                "STATUS",
                "ACTION",
            ],
            strict=False,
        ):
            col.markdown(f"**{label}**")
        for c in recent:
            row = st.columns([2.5, 2, 1, 1, 1, 1])
            with row[0]:
                college_icon = row_icon_html("\U0001f3eb", "purple")
                st.markdown(
                    f'<div class="coligo-item-row">'
                    f"{college_icon}"
                    f'<span class="coligo-item-title">{c["college_name"]}</span></div>',
                    unsafe_allow_html=True,
                )
            row[1].write(c.get("contact_person") or "-")
            row[2].write(c["course_count"])
            row[3].write(c["brochure_count"])
            row[4].markdown(
                badge("Active" if c["is_active"] else "Inactive"),
                unsafe_allow_html=True,
            )
            if row[5].button("View", key=f"dash_view_{c['id']}"):
                st.session_state.nav = "Colleges"
                st.session_state.viewing_college_id = c["id"]
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    # 2.5 Live Student Inquiries (WhatsApp & Web Conversations)
    st.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="coligo-card-header">Live Student Inquiries (WhatsApp & Web)</div>',
        unsafe_allow_html=True,
    )
    try:
        from utils.api_client import get_conversation, list_conversations

        threads = list_conversations(st.session_state.token, limit=10)
        if not threads:
            st.info("No student conversations recorded yet.")
        else:
            for t in threads:
                sess = t.get("session_key", "")
                is_wa = sess.startswith("whatsapp:")
                channel_label = (
                    f"WhatsApp: {sess.replace('whatsapp:', '')}"
                    if is_wa
                    else f"Web Session: {sess}"
                )
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.markdown(
                        f"**{channel_label}** — `{t.get('message_count', 0)} messages`"
                    )
                    if t.get("last_message"):
                        st.caption(f"Latest: {t['last_message']}")
                with col_b:
                    st.caption(
                        f"Active: {str(t.get('last_message_at', ''))[:16].replace('T', ' ')}"
                    )

                with st.expander(f"View Dialogue ({channel_label})"):
                    conv_detail = get_conversation(st.session_state.token, t["id"])
                    msgs = conv_detail.get("messages", [])
                    if msgs:
                        for m in msgs:
                            with st.chat_message(m["role"]):
                                st.write(m["content"])
                                st.caption(
                                    f"{str(m.get('created_at', ''))[:19].replace('T', ' ')}"
                                )
                    else:
                        st.write("No messages found.")
                st.markdown("<hr style='margin: 0.4rem 0;'>", unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"Could not load student conversations: {e}")
    st.markdown("</div>", unsafe_allow_html=True)

    # 3. Live System Health & Backend Service Status
    st.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="coligo-card-header">System Health & Connectivity</div>',
        unsafe_allow_html=True,
    )
    try:
        from utils.api_client import get_detailed_health

        health_data = get_detailed_health()
        h_col1, h_col2, h_col3 = st.columns(3)
        with h_col1:
            st.metric("API Gateway", health_data.get("status", "unknown").upper())
            st.caption(f"Environment: `{health_data.get('environment', 'unknown')}`")
        with h_col2:
            db_status = health_data.get("services", {}).get("database", "unknown")
            st.metric("Database (pgvector)", db_status.upper())
            st.caption("Engine: PostgreSQL 16 (Supabase / Vector)")
        with h_col3:
            st.metric("API Version", health_data.get("version", "0.1.0"))
            st.caption("Docs: `/docs` | OpenAPI: `/openapi.json`")
    except Exception as e:
        st.warning(f"Could not reach health check: {e}")

    st.markdown("</div>", unsafe_allow_html=True)
    render_footer()
