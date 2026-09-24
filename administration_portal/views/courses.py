from collections import Counter
from typing import Any

import streamlit as st
from utils.api_client import (
    APIError,
    create_course,
    delete_course,
    list_courses,
    update_course,
)
from utils.styling import (
    badge,
    page_header,
    pill,
    render_footer,
    render_stat_row,
    row_icon_html,
)

PROGRAM_LEVELS: list[str] = ["UG", "PG", "Diploma", "PhD"]


def _course_form(existing: dict | None) -> None:
    token = st.session_state.token
    is_edit = existing is not None
    existing_dict: dict[str, Any] = existing or {}
    st.subheader("Edit Course" if is_edit else "Add New Course")

    with st.form("course_form"):
        col1, col2 = st.columns(2)
        with col1:
            program_level = st.selectbox(
                "Program Level *",
                PROGRAM_LEVELS,
                index=PROGRAM_LEVELS.index(existing_dict["program_level"])
                if is_edit
                else 0,
            )
            course_name = st.text_input(
                "Course Name *", value=existing_dict["course_name"] if is_edit else ""
            )
            course_code = st.text_input(
                "Course Code (Optional)",
                value=(existing_dict.get("course_code") or "") if is_edit else "",
            )
            duration = st.text_input(
                "Duration *",
                value=(existing_dict.get("duration") or "") if is_edit else "",
            )
        with col2:
            intake_capacity = st.number_input(
                "Intake Capacity",
                min_value=0,
                value=existing_dict.get("intake_capacity") or 0 if is_edit else 0,
                step=1,
            )
            department = st.text_input(
                "Department",
                value=(existing_dict.get("department") or "") if is_edit else "",
            )
            status_options = ["published", "draft"]
            current_status = existing_dict["status"] if is_edit else "draft"
            status = st.radio(
                "Course Status *",
                status_options,
                index=status_options.index(current_status),
                horizontal=True,
                format_func=lambda s: s.capitalize(),
            )

        eligibility = st.text_area(
            "Eligibility",
            value=(existing_dict.get("eligibility") or "") if is_edit else "",
        )
        fees = st.text_input(
            "Fees", value=(existing_dict.get("fees") or "") if is_edit else ""
        )
        course_details = st.text_area(
            "Course Details",
            value=(existing_dict.get("course_details") or "") if is_edit else "",
        )
        career_opportunities = st.text_area(
            "Career Opportunities",
            value=(existing_dict.get("career_opportunities") or "") if is_edit else "",
        )

        save_col, cancel_col = st.columns([1, 1])
        with save_col:
            submitted = st.form_submit_button(
                "Save & Next", type="primary", use_container_width=True
            )
        with cancel_col:
            cancelled = st.form_submit_button("Cancel", use_container_width=True)

    if cancelled:
        st.session_state.course_editing_id = None
        st.rerun()

    if submitted:
        if not course_name or not duration:
            st.error("Course name and duration are required.")
            return
        payload = {
            "program_level": program_level,
            "course_name": course_name,
            "course_code": course_code or None,
            "duration": duration,
            "intake_capacity": int(intake_capacity) or None,
            "department": department or None,
            "status": status,
            "eligibility": eligibility or None,
            "fees": fees or None,
            "course_details": course_details or None,
            "career_opportunities": career_opportunities or None,
        }
        try:
            if is_edit:
                update_course(token, existing_dict["id"], payload)
                st.success("Course updated.")
            else:
                create_course(token, payload)
                st.success("Course added.")
            st.session_state.course_editing_id = None
            st.rerun()
        except APIError as e:
            st.error(e.message)


def render_courses() -> None:
    token = st.session_state.token
    editing_id = st.session_state.get("course_editing_id")

    if editing_id is not None:
        existing = None
        if editing_id != "new":
            try:
                existing = next(c for c in list_courses(token) if c["id"] == editing_id)
            except (APIError, StopIteration) as e:
                st.error(getattr(e, "message", "Course not found."))
                st.session_state.course_editing_id = None
                return
        if st.button("← Back to Courses"):
            st.session_state.course_editing_id = None
            st.rerun()
        _course_form(existing)
        return

    header_left, header_right = st.columns([4, 1.2])
    with header_left:
        page_header(
            "\U0001f4d8", "Courses", "Manage all courses offered by your college"
        )
    with header_right:
        st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
        if st.button("+ Add New Course", type="primary", use_container_width=True):
            st.session_state.course_editing_id = "new"
            st.rerun()

    try:
        courses = list_courses(token)
    except APIError as e:
        st.error(e.message)
        return

    if not courses:
        st.info("No courses added yet. Click 'Add New Course' to get started.")
        return

    total_intake = sum(c.get("intake_capacity") or 0 for c in courses)
    durations = [c["duration"] for c in courses if c.get("duration")]
    common_duration = Counter(durations).most_common(1)[0][0] if durations else "-"
    draft_count = sum(1 for c in courses if c["status"] == "draft")
    render_stat_row(
        [
            ("Total Courses", len(courses), "\U0001f4d8", "Active courses"),
            ("Total Intake", total_intake, "\U0001f393", "Total seats"),
            (
                "Average Duration",
                common_duration,
                "⌛",
                "Across all courses",
            ),
            ("Draft Courses", draft_count, "\U0001f4c4", "Courses in draft"),
        ]
    )

    search = st.text_input(
        "Search courses",
        placeholder="\U0001f50d  Search courses...",
        label_visibility="collapsed",
    )
    if search:
        courses = [c for c in courses if search.lower() in c["course_name"].lower()]

    st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
    header = st.columns([3, 1, 1.2, 1, 1.3, 1])
    for col, label in zip(
        header,
        ["COURSE NAME", "PROGRAM", "DURATION", "INTAKE", "STATUS", "ACTION"],
        strict=False,
    ):
        col.markdown(f"**{label}**")

    for course in courses:
        row = st.columns([3, 1, 1.2, 1, 1.3, 1])
        with row[0]:
            course_icon = row_icon_html("\U0001f4bb", "purple")
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;">'
                f"{course_icon}"
                f'<span>{course["course_name"]}</span></div>',
                unsafe_allow_html=True,
            )
        row[1].markdown(badge(course["program_level"], "ug"), unsafe_allow_html=True)
        row[2].markdown(
            pill(course.get("duration") or "-", "blue"), unsafe_allow_html=True
        )
        row[3].markdown(
            pill(course.get("intake_capacity") or "-", "green"),
            unsafe_allow_html=True,
        )
        row[4].markdown(badge(course["status"].capitalize()), unsafe_allow_html=True)
        with row[5]:
            e_col, d_col = st.columns(2)
            if e_col.button("✏️", key=f"edit_course_{course['id']}"):
                st.session_state.course_editing_id = course["id"]
                st.rerun()
            if d_col.button("\U0001f5d1️", key=f"delete_course_{course['id']}"):
                try:
                    delete_course(token, course["id"])
                    st.rerun()
                except APIError as e:
                    st.error(e.message)
    st.markdown("</div>", unsafe_allow_html=True)
    render_footer()
