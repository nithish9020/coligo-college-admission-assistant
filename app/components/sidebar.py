"""Sidebar Navigation and Student Profile Badge for Coligo Streamlit Portal."""

import streamlit as st

from api.services.student_profile_service import (
    get_student_profile,
    update_student_profile,
)


def render_sidebar() -> str:
    """Render sidebar profile badge, TNEA quick-stats, and tab selector.

    Returns:
        str: Currently selected navigation view title.
    """
    with st.sidebar:
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">🎓</span>
                <div>
                    <h2 style="margin: 0; font-size: 1.35rem; color: #1E293B;">Coligo Portal</h2>
                    <span style="font-size: 0.8rem; color: #4F46E5; font-weight: 600;">TNEA 2026 ASSISTANT</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        session_key = st.session_state.get("session_key", "whatsapp:anonymous")
        phone = st.session_state.get("phone", "Guest")
        profile = get_student_profile(session_key)

        with st.container(border=True):
            st.markdown(f"**👤 Student:** `{phone}`")
            cutoff_val = profile.calculated_cutoff or st.session_state.get(
                "cutoff", 185.0
            )
            comm_val = profile.community or st.session_state.get("community", "BC")
            dist_val = profile.preferred_district or st.session_state.get(
                "district", "Coimbatore"
            )

            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Cutoff", f"{cutoff_val:g}")
            with col_b:
                st.metric("Quota", comm_val)

            st.caption(f"📍 Target Region: **{dist_val}**")

            with st.expander("✏️ Update Cutoff / Quota"):
                new_c = st.number_input(
                    "Cutoff Mark",
                    min_value=77.5,
                    max_value=200.0,
                    value=float(cutoff_val),
                    step=0.25,
                    key="sidebar_cutoff_input",
                )
                new_comm = st.selectbox(
                    "Community Quota",
                    options=["OC", "BC", "BCM", "MBC", "SC", "SCA", "ST"],
                    index=["OC", "BC", "BCM", "MBC", "SC", "SCA", "ST"].index(comm_val)
                    if comm_val in ["OC", "BC", "BCM", "MBC", "SC", "SCA", "ST"]
                    else 1,
                    key="sidebar_comm_select",
                )
                if st.button("Save Profile", use_container_width=True):
                    update_student_profile(
                        session_key=session_key,
                        cutoff=new_c,
                        community=new_comm,
                    )
                    st.session_state["cutoff"] = new_c
                    st.session_state["community"] = new_comm
                    st.success("Profile updated!")
                    st.rerun()

        st.markdown("### 📌 Navigation")
        nav_options = [
            "💬 AI Admissions Chatbot",
            "📊 Cutoff Visualizer & Graphs",
            "🥧 Seat Matrix & Quota Pie Charts",
            "💼 Placement & Recruiter Analytics",
            "📋 3-Tier Choice Sheet Builder",
            "📈 TNEA Rank & Round Predictor",
        ]
        selected_view = st.radio(
            "Go to View",
            options=nav_options,
            label_visibility="collapsed",
            key="portal_navigation_radio",
        )

        st.divider()

        st.markdown(
            """
            <div style="background: #F8FAFC; padding: 10px; border-radius: 8px; border: 1px solid #E2E8F0; font-size: 0.85rem;">
                <strong>📞 Official Admissions Desk</strong><br>
                <span>Sri Krishna College of Engg & Tech</span><br>
                <a href="tel:+914222678001" style="color: #4F46E5; text-decoration: none;">+91 422 2678001</a>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")
        if st.button("🚪 Log Out", use_container_width=True):
            st.session_state.clear()
            st.rerun()

        return selected_view
