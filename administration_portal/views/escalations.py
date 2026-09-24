import streamlit as st
from utils.api_client import (
    APIError,
    list_escalations,
    reply_escalation,
    resolve_escalation,
    update_escalation_status,
)
from utils.styling import (
    badge,
    page_header,
    render_footer,
    row_icon_html,
)

TEMPLATES = {
    "campus_visit": (
        "Hello! We would love to invite you and your family for an in-person campus "
        "visit and personalized admission counselling this week. Would you like us "
        "to schedule a convenient time slot for you?"
    ),
    "cutoff_guidance": (
        "Hello! Based on your TNEA marks and community category, you have strong chances "
        "for top circuital branches (CSE, IT, ECE). We can assist you with the official "
        "choice-filling sequence during counselling rounds. What specific branches are you interested in?"
    ),
    "fees_scholarship": (
        "Hello! For our institution, government-approved tuition fee and hostel charges "
        "apply. Merit scholarships and fee concessions are also available for students with "
        "high TNEA cutoffs. Would you like our detailed fee breakdown document?"
    ),
    "direct_call": (
        "Hello! To discuss your specific admission options and document verification directly, "
        "please call our Senior Admission Officer on our desk hotline at +91 422 2678001, "
        "or let us know a good time to call you back."
    ),
}


def render_escalations() -> None:
    token = st.session_state.token

    page_header(
        "🎧",
        "Counselor Live WhatsApp Takeover",
        "Two-way WhatsApp intervention desk for out-of-scope inquiries, sensitive queries, and personalized student counselling",
        "orange",
    )

    try:
        data = list_escalations(token)
        escalations = data.get("escalations", [])
    except APIError as e:
        st.error(f"Failed to fetch escalations: {e.message}")
        render_footer()
        return

    pending_count = sum(1 for e in escalations if e.get("status") == "pending")
    takeover_count = sum(1 for e in escalations if e.get("status") == "in_progress")
    resolved_count = sum(1 for e in escalations if e.get("status") == "resolved")

    # Metrics row
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("🔴 Pending Review", pending_count)
    with m2:
        st.metric("🟡 In Live Takeover (AI Paused)", takeover_count)
    with m3:
        st.metric("🟢 Resolved Inquiries", resolved_count)

    st.markdown("<br>", unsafe_allow_html=True)

    # Filter tabs
    status_filter = st.radio(
        "Filter by Queue Status",
        options=[
            "All",
            f"Pending ({pending_count})",
            f"In Takeover ({takeover_count})",
            f"Resolved ({resolved_count})",
        ],
        horizontal=True,
    )

    if "Pending" in status_filter:
        filtered = [e for e in escalations if e.get("status") == "pending"]
    elif "Takeover" in status_filter:
        filtered = [e for e in escalations if e.get("status") == "in_progress"]
    elif "Resolved" in status_filter:
        filtered = [e for e in escalations if e.get("status") == "resolved"]
    else:
        filtered = escalations

    st.markdown(f"#### 📥 Active Inquiries & Live Chat Queue ({len(filtered)})")

    if not filtered:
        st.info("No escalations found in this queue category.")
    else:
        for item in filtered:
            esc_id = item["id"]
            status = item.get("status", "pending")
            sender = item.get("sender", "unknown")
            is_whatsapp = sender.startswith("whatsapp:")
            created_at = item.get("created_at", "")[:19].replace("T", " ")

            badge_label = "Pending"
            if status == "in_progress":
                badge_label = "In Takeover"
            elif status == "resolved":
                badge_label = "Resolved"

            with st.expander(
                f"#{esc_id} | {sender} | {badge_label} | {created_at}",
                expanded=(status in ("pending", "in_progress")),
            ):
                col_info, col_status = st.columns([3, 1])
                with col_info:
                    sender_icon = row_icon_html("📱" if is_whatsapp else "💻", "purple")
                    st.markdown(
                        f'<div class="coligo-item-row">{sender_icon}'
                        f'<span class="coligo-item-title"><strong>Student Channel:</strong> {sender}</span></div>',
                        unsafe_allow_html=True,
                    )
                    st.caption(f"Received at: {created_at}")
                with col_status:
                    st.markdown(
                        badge(badge_label),
                        unsafe_allow_html=True,
                    )

                st.markdown("**Student Inquiries / Conversation:**")
                st.info(f"🗣️ {item.get('query_text')}")

                if item.get("counselor_reply"):
                    st.markdown("**Previous Counselor Reply:**")
                    st.success(f"👨‍🏫 {item.get('counselor_reply')}")
                    if item.get("resolved_at"):
                        st.caption(
                            f"Resolved at: {item['resolved_at'][:19].replace('T', ' ')}"
                        )

                if status == "in_progress":
                    st.warning(
                        "⏸️ **AI Bot Paused:** Automated bot replies are currently paused for this student "
                        "so you can chat freely without AI interference. When you resolve the ticket or the "
                        "student types */resume*, automated AI will resume."
                    )

                if status in ("pending", "in_progress"):
                    st.markdown("---")
                    st.markdown("##### 💬 Send Live WhatsApp Reply to Student")

                    # Quick response template buttons
                    st.caption("Quick Reply Templates:")
                    t1, t2, t3, t4 = st.columns(4)
                    template_key = f"tpl_val_{esc_id}"
                    if template_key not in st.session_state:
                        st.session_state[template_key] = ""

                    if t1.button("🏫 Campus Visit", key=f"btn_tpl_cv_{esc_id}"):
                        st.session_state[template_key] = TEMPLATES["campus_visit"]
                        st.rerun()
                    if t2.button("📊 Cutoff Guidance", key=f"btn_tpl_cg_{esc_id}"):
                        st.session_state[template_key] = TEMPLATES["cutoff_guidance"]
                        st.rerun()
                    if t3.button("💰 Fee & Scholarship", key=f"btn_tpl_fs_{esc_id}"):
                        st.session_state[template_key] = TEMPLATES["fees_scholarship"]
                        st.rerun()
                    if t4.button("📞 Direct Call", key=f"btn_tpl_dc_{esc_id}"):
                        st.session_state[template_key] = TEMPLATES["direct_call"]
                        st.rerun()

                    reply_text = st.text_area(
                        "Counselor Reply Message:",
                        value=st.session_state[template_key],
                        key=f"input_reply_{esc_id}",
                        placeholder="Type your personalized guidance here... (will be sent directly to student's WhatsApp)",
                        height=100,
                    )

                    btn_col1, btn_col2, btn_col3 = st.columns([1.5, 1.5, 1.2])

                    with btn_col1:
                        if st.button(
                            "📤 Send WhatsApp & Resolve",
                            key=f"send_resolve_{esc_id}",
                            type="primary",
                            disabled=not reply_text.strip(),
                        ):
                            try:
                                res = reply_escalation(
                                    token,
                                    esc_id,
                                    reply_text.strip(),
                                    resolve=True,
                                    send_whatsapp=is_whatsapp,
                                )
                                if res.get("delivered_to_whatsapp"):
                                    st.success(
                                        "✅ Message delivered to student's WhatsApp! Ticket resolved."
                                    )
                                else:
                                    st.success("✅ Reply saved and ticket resolved.")
                                st.session_state[template_key] = ""
                                st.rerun()
                            except APIError as e:
                                st.error(f"Error: {e.message}")

                    with btn_col2:
                        if st.button(
                            "💬 Send & Keep in Takeover",
                            key=f"send_takeover_{esc_id}",
                            disabled=not reply_text.strip(),
                        ):
                            try:
                                res = reply_escalation(
                                    token,
                                    esc_id,
                                    reply_text.strip(),
                                    resolve=False,
                                    send_whatsapp=is_whatsapp,
                                )
                                if res.get("delivered_to_whatsapp"):
                                    st.success(
                                        "✅ Message delivered! Session kept in live takeover."
                                    )
                                else:
                                    st.success(
                                        "✅ Reply saved! Session kept in live takeover."
                                    )
                                st.session_state[template_key] = ""
                                st.rerun()
                            except APIError as e:
                                st.error(f"Error: {e.message}")

                    with btn_col3:
                        if st.button("Mark Resolved", key=f"btn_res_only_{esc_id}"):
                            try:
                                resolve_escalation(token, esc_id)
                                st.success("Marked resolved.")
                                st.rerun()
                            except APIError as e:
                                st.error(e.message)

                elif status == "resolved":
                    st.markdown("---")
                    r_col1, _ = st.columns([1.5, 3])
                    with r_col1:
                        if st.button(
                            "🔄 Reopen / Takeover Chat", key=f"reopen_{esc_id}"
                        ):
                            try:
                                update_escalation_status(token, esc_id, "in_progress")
                                st.success("Reopened chat in Live Takeover mode.")
                                st.rerun()
                            except APIError as e:
                                st.error(e.message)

    render_footer()
