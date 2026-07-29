import streamlit as st

from utils.api_client import (
    APIError,
    delete_brochure,
    download_brochure,
    list_brochures,
    update_brochure,
    upload_brochure,
)

CATEGORIES = ["Prospectus", "Course Guide", "Placement Brochure", "Facilities", "Other"]


def render_brochures() -> None:
    token = st.session_state.token

    st.title("Brochures")
    st.caption("Upload and manage your college brochures (PDF only)")

    st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
    with st.form("upload_brochure_form", clear_on_submit=True):
        col1, col2 = st.columns([2, 1])
        with col1:
            title = st.text_input("Brochure Title *", placeholder="e.g. College Prospectus 2026")
        with col2:
            category = st.selectbox("Category", CATEGORIES)
        pdf_file = st.file_uploader("PDF File *", type=["pdf"])

        if st.form_submit_button("\U0001F4E4 Upload Brochure", type="primary"):
            if not title or pdf_file is None:
                st.error("Title and a PDF file are both required.")
            else:
                try:
                    upload_brochure(
                        token, title, category, pdf_file.name, pdf_file.getvalue()
                    )
                    st.success("Brochure uploaded.")
                    st.rerun()
                except APIError as e:
                    st.error(e.message)
    st.markdown("</div>", unsafe_allow_html=True)

    try:
        brochures = list_brochures(token)
    except APIError as e:
        st.error(e.message)
        return

    if not brochures:
        st.info("No brochures uploaded yet.")
        return

    st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
    header = st.columns([3, 1.5, 1, 1.5, 2])
    for col, label in zip(
        header, ["Brochure Title", "Category", "Size", "Uploaded On", "Action"], strict=False
    ):
        col.markdown(f"**{label}**")

    for b in brochures:
        edit_key = f"editing_brochure_{b['id']}"
        row = st.columns([3, 1.5, 1, 1.5, 2])
        if st.session_state.get(edit_key):
            new_title = row[0].text_input(
                "Title", value=b["title"], key=f"bro_title_{b['id']}", label_visibility="collapsed"
            )
            new_cat = row[1].selectbox(
                "Category",
                CATEGORIES,
                index=CATEGORIES.index(b["category"])
                if b.get("category") in CATEGORIES
                else 0,
                key=f"bro_cat_{b['id']}",
                label_visibility="collapsed",
            )
            row[2].write(f"{round(b['file_size_bytes'] / (1024 * 1024), 2)} MB")
            row[3].write(b["uploaded_at"][:10])
            with row[4]:
                s_col, c_col = st.columns(2)
                if s_col.button("Save", key=f"save_bro_{b['id']}"):
                    try:
                        update_brochure(
                            token, b["id"], {"title": new_title, "category": new_cat}
                        )
                        st.session_state[edit_key] = False
                        st.rerun()
                    except APIError as e:
                        st.error(e.message)
                if c_col.button("Cancel", key=f"cancel_bro_{b['id']}"):
                    st.session_state[edit_key] = False
                    st.rerun()
        else:
            row[0].write(b["title"])
            row[1].write(b.get("category") or "-")
            row[2].write(f"{round(b['file_size_bytes'] / (1024 * 1024), 2)} MB")
            row[3].write(b["uploaded_at"][:10])
            with row[4]:
                dl_col, e_col, d_col = st.columns(3)
                with dl_col:
                    try:
                        pdf_bytes = download_brochure(token, b["id"])
                        st.download_button(
                            "\U0001F441️",
                            data=pdf_bytes,
                            file_name=f"{b['title']}.pdf",
                            mime="application/pdf",
                            key=f"dl_bro_{b['id']}",
                        )
                    except APIError:
                        st.caption("N/A")
                if e_col.button("✏️", key=f"edit_bro_{b['id']}"):
                    st.session_state[edit_key] = True
                    st.rerun()
                if d_col.button("\U0001F5D1️", key=f"del_bro_{b['id']}"):
                    try:
                        delete_brochure(token, b["id"])
                        st.rerun()
                    except APIError as e:
                        st.error(e.message)
    st.markdown("</div>", unsafe_allow_html=True)
