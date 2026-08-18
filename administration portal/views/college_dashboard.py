import streamlit as st
from utils.api_client import APIError, get_my_profile, list_brochures, list_courses
from utils.styling import (
    action_row,
    empty_state,
    page_header,
    render_footer,
    render_stat_row,
)


def render_college_dashboard() -> None:
    token = st.session_state.token

    try:
        profile = get_my_profile(token)
        courses = list_courses(token)
        brochures = list_brochures(token)
    except APIError as e:
        st.error(e.message)
        return

    page_header(
        "\U0001f3e0",
        "Dashboard",
        f"Welcome back, {profile['college_name']} \U0001f44b",
    )

    published = sum(1 for c in courses if c["status"] == "published")
    render_stat_row(
        [
            ("Total Courses", len(courses), "\U0001f4d8", "All courses added"),
            (
                "Published Courses",
                published,
                "\U0001f393",
                "Courses published",
            ),
            (
                "Total Brochures",
                len(brochures),
                "\U0001f4c4",
                "Brochures uploaded",
            ),
            (
                "Profile Status",
                "Active" if profile["is_active"] else "Inactive",
                "\U0001f464",
                "Your profile is active"
                if profile["is_active"]
                else "Complete your profile",
            ),
        ]
    )

    st.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)
    left, right = st.columns([1.3, 1])

    with left:
        st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
        st.markdown(
            '<div class="coligo-card-header">ℹ️ About your college</div>',
            unsafe_allow_html=True,
        )
        if profile.get("about"):
            st.write(profile["about"])
        else:
            empty_state(
                "\U0001f3db️",
                "No description added yet.",
                "Add a description to showcase your college.",
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
        st.markdown(
            '<div class="coligo-card-header">⚡ Quick Actions</div>',
            unsafe_allow_html=True,
        )
        if action_row(
            "addcourse", "➕", "Add New Course", "Create a new course", "purple"
        ):
            st.session_state.nav = "Courses"
            st.rerun()
        if action_row(
            "uploadbrochure",
            "\U0001f4e4",
            "Upload Brochure",
            "Upload college brochure",
            "blue",
        ):
            st.session_state.nav = "Brochures"
            st.rerun()
        if action_row(
            "editprofile",
            "✏️",
            "Edit College Profile",
            "Update your college information",
            "orange",
        ):
            st.session_state.nav = "College Profile"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    render_footer()
