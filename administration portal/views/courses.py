import streamlit as st

from utils.api_client import (
    APIError,
    create_course,
    delete_course,
    list_courses,
    update_course,
)
from utils.styling import badge

PROGRAM_LEVELS = ["UG", "PG", "Diploma", "PhD"]


def _course_form(existing: dict | None) -> None:
    token = st.session_state.token
    is_edit = existing is not None
    st.subheader("Edit Course" if is_edit else "Add New Course")

    with st.form("course_form"):
        col1, col2 = st.columns(2)
        with col1:
            program_level = st.selectbox(
                "Program Level *",
                PROGRAM_LEVELS,
                index=PROGRAM_LEVELS.index(existing["program_level"])
                if is_edit
                else 0,
            )
            course_name = st.text_input(
                "Course Name *", value=existing["course_name"] if is_edit else ""
            )
            course_code = st.text_input(
                "Course Code (Optional)",
                value=(existing.get("course_code") or "") if is_edit else "",
            )
            duration = st.text_input(
                "Duration *", value=(existing.get("duration") or "") if is_edit else ""
            )
        with col2:
            intake_capacity = st.number_input(
                "Intake Capacity",
                min_value=0,
                value=existing.get("intake_capacity") or 0 if is_edit else 0,
                step=1,
            )
            department = st.text_input(
                "Department", value=(existing.get("department") or "") if is_edit else ""
            )
            status_options = ["published", "draft"]
            current_status = existing["status"] if is_edit else "draft"
            status = st.radio(
                "Course Status *",
                status_options,
                index=status_options.index(current_status),
                horizontal=True,
                format_func=lambda s: s.capitalize(),
            )

        eligibility = st.text_area(
            "Eligibility", value=(existing.get("eligibility") or "") if is_edit else ""
        )
        fees = st.text_input(
            "Fees", value=(existing.get("fees") or "") if is_edit else ""
        )
        course_details = st.text_area(
            "Course Details",
            value=(existing.get("course_details") or "") if is_edit else "",
        )
        career_opportunities = st.text_area(
            "Career Opportunities",
            value=(existing.get("career_opportunities") or "") if is_edit else "",
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
                update_course(token, existing["id"], payload)
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
                existing = next(
                    c for c in list_courses(token) if c["id"] == editing_id
                )
            except (APIError, StopIteration) as e:
                st.error(getattr(e, "message", "Course not found."))
                st.session_state.course_editing_id = None
                return
        if st.button("← Back to Courses"):
            st.session_state.course_editing_id = None
            st.rerun()
        _course_form(existing)
        return

    st.title("Courses")
    st.caption("Manage all courses offered by your college")

    top_left, top_right = st.columns([4, 1])
    with top_right:
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

    st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
    header = st.columns([3, 1, 1.2, 1, 1.3, 1])
    for col, label in zip(
        header, ["Course Name", "Program", "Duration", "Intake", "Status", "Action"], strict=False
    ):
        col.markdown(f"**{label}**")

    for course in courses:
        row = st.columns([3, 1, 1.2, 1, 1.3, 1])
        row[0].write(course["course_name"])
        row[1].write(course["program_level"])
        row[2].write(course.get("duration") or "-")
        row[3].write(course.get("intake_capacity") or "-")
        row[4].markdown(badge(course["status"].capitalize()), unsafe_allow_html=True)
        with row[5]:
            e_col, d_col = st.columns(2)
            if e_col.button("✏️", key=f"edit_course_{course['id']}"):
                st.session_state.course_editing_id = course["id"]
                st.rerun()
            if d_col.button("\U0001F5D1️", key=f"delete_course_{course['id']}"):
                try:
                    delete_course(token, course["id"])
                    st.rerun()
                except APIError as e:
                    st.error(e.message)
    st.markdown("</div>", unsafe_allow_html=True)
