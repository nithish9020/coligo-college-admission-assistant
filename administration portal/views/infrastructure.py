import streamlit as st
from utils.api_client import (
    APIError,
    create_facility,
    delete_facility,
    list_facilities,
    update_facility,
)


def render_infrastructure() -> None:
    token = st.session_state.token

    st.title("Infrastructure & Facilities")
    st.caption("List the facilities available at your campus")

    st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
    with st.form("add_facility_form", clear_on_submit=True):
        col1, col2 = st.columns([1, 2])
        with col1:
            name = st.text_input("Facility Name *", placeholder="e.g. Central Library")
        with col2:
            description = st.text_input(
                "Description", placeholder="Short description (optional)"
            )
        if st.form_submit_button("+ Add Facility", type="primary"):
            if not name:
                st.error("Facility name is required.")
            else:
                try:
                    create_facility(
                        token, {"name": name, "description": description or None}
                    )
                    st.success("Facility added.")
                    st.rerun()
                except APIError as e:
                    st.error(e.message)
    st.markdown("</div>", unsafe_allow_html=True)

    try:
        facilities = list_facilities(token)
    except APIError as e:
        st.error(e.message)
        return

    if not facilities:
        st.info("No facilities added yet.")
        return

    for facility in facilities:
        st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
        cols = st.columns([3, 1])
        with cols[0]:
            st.markdown(f"**{facility['name']}**")
            if facility.get("description"):
                st.caption(facility["description"])
        with cols[1]:
            edit_key = f"editing_facility_{facility['id']}"
            if st.session_state.get(edit_key):
                new_name = st.text_input(
                    "Name", value=facility["name"], key=f"fac_name_{facility['id']}"
                )
                new_desc = st.text_input(
                    "Description",
                    value=facility.get("description") or "",
                    key=f"fac_desc_{facility['id']}",
                )
                save_col, cancel_col = st.columns(2)
                if save_col.button("Save", key=f"save_facility_{facility['id']}"):
                    try:
                        update_facility(
                            token,
                            facility["id"],
                            {"name": new_name, "description": new_desc or None},
                        )
                        st.session_state[edit_key] = False
                        st.rerun()
                    except APIError as e:
                        st.error(e.message)
                if cancel_col.button("Cancel", key=f"cancel_facility_{facility['id']}"):
                    st.session_state[edit_key] = False
                    st.rerun()
            else:
                e_col, d_col = st.columns(2)
                if e_col.button("✏️ Edit", key=f"edit_btn_facility_{facility['id']}"):
                    st.session_state[edit_key] = True
                    st.rerun()
                if d_col.button(
                    "\U0001f5d1️ Delete", key=f"del_facility_{facility['id']}"
                ):
                    try:
                        delete_facility(token, facility["id"])
                        st.rerun()
                    except APIError as e:
                        st.error(e.message)
        st.markdown("</div>", unsafe_allow_html=True)
