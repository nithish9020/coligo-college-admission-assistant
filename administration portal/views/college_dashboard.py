import streamlit as st

from utils.api_client import APIError, get_my_profile, list_brochures, list_courses
from utils.styling import render_stat_row


def render_college_dashboard() -> None:
    token = st.session_state.token

    try:
        profile = get_my_profile(token)
        courses = list_courses(token)
        brochures = list_brochures(token)
    except APIError as e:
        st.error(e.message)
        return

    st.title("Dashboard")
    st.caption(f"Welcome back, {profile['college_name']} \U0001F44B")

    published = sum(1 for c in courses if c["status"] == "published")
    render_stat_row(
        [
            ("Total Courses", len(courses)),
            ("Published Courses", published),
            ("Total Brochures", len(brochures)),
            ("Profile Status", "Active" if profile["is_active"] else "Inactive"),
        ]
    )

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    left, right = st.columns([1.3, 1])

    with left:
        st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
        st.markdown("#### About your college")
        st.write(profile.get("about") or "No description added yet.")
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
        st.markdown("#### Quick Actions")
        if st.button("➕ Add New Course", use_container_width=True):
            st.session_state.nav = "Courses"
            st.rerun()
        if st.button("\U0001F4C4 Upload Brochure", use_container_width=True):
            st.session_state.nav = "Brochures"
            st.rerun()
        if st.button("\U0001F4DD Edit College Profile", use_container_width=True):
            st.session_state.nav = "College Profile"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
