import streamlit as st
from utils.api_client import (
    APIError,
    delete_document,
    list_documents,
    scrape_college,
)
from utils.styling import (
    badge,
    page_header,
    render_footer,
    row_icon_html,
)


def render_knowledge_base() -> None:
    token = st.session_state.token

    page_header(
        "📚",
        "Knowledge Base & Documents",
        "Manage RAG vector embeddings, documents, and web crawler ingestion",
    )

    # 1. Ingestion Section with Tabs
    st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
    st.markdown("#### 📥 Ingest College Data to Vector Store")

    tab_scrape, tab_pdf = st.tabs(["🌐 Web Scraper", "📄 Upload PDF / Document URL"])

    with tab_scrape:
        st.caption(
            "Enter college name and official admission URLs. The scraper extracts pages, "
            "chunks text, computes vector embeddings, and indexes them into pgvector."
        )
        with st.form("web_scraper_form", clear_on_submit=False):
            c1, c2 = st.columns([1, 2])
            with c1:
                college_name = st.text_input(
                    "College Name *",
                    placeholder="e.g. Coimbatore Institute of Technology",
                )
            with c2:
                urls_raw = st.text_area(
                    "URLs to Scrape (one per line) *",
                    placeholder="https://www.cit.edu.in/admission\nhttps://www.cit.edu.in/courses",
                    height=90,
                )

            submit_scraper = st.form_submit_button("🚀 Scrape & Ingest", type="primary")

        if submit_scraper:
            urls = [
                u.strip() for u in urls_raw.split("\n") if u.strip().startswith("http")
            ]
            if not college_name.strip() or not urls:
                st.error(
                    "Please provide both a valid college name and at least one valid HTTP URL."
                )
            else:
                with st.spinner(f"Scraping {len(urls)} pages for {college_name}..."):
                    try:
                        res = scrape_college(token, college_name.strip(), urls)
                        st.success(
                            f"✅ Successfully ingested! Total chunks: {res.get('total_chunks', 0)}, "
                            f"Inserted: {res.get('inserted_chunks', 0)}"
                        )
                        st.rerun()
                    except APIError as e:
                        st.error(f"Scraping failed: {e.message}")

    with tab_pdf:
        st.caption(
            "Upload an official PDF document or provide an online PDF URL. The backend will parse, "
            "chunk, and index all text into pgvector for the RAG assistant."
        )
        import os

        from utils.api_client import process_document

        pdf_method = st.radio(
            "Source Type",
            options=["File Upload (.pdf / .txt)", "Remote URL or Local Path"],
            horizontal=True,
        )

        if pdf_method == "File Upload (.pdf / .txt)":
            uploaded_file = st.file_uploader(
                "Select Document",
                type=["pdf", "txt"],
                help="PDF handbook, prospectus, or raw text cutoff file",
            )
            if uploaded_file and st.button("📥 Process & Ingest File", type="primary"):
                os.makedirs("data", exist_ok=True)
                target_path = os.path.join("data", uploaded_file.name)
                with open(target_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                with st.spinner(f"Processing and embedding {uploaded_file.name}..."):
                    try:
                        res = process_document(target_path, token=token)
                        st.success(
                            f"✅ Ingested {uploaded_file.name}! "
                            f"Total chunks: {res.get('total_chunks', 0)}, "
                            f"Inserted: {res.get('inserted_chunks', 0)}"
                        )
                        st.rerun()
                    except APIError as e:
                        st.error(f"Ingestion failed: {e.message}")
        else:
            with st.form("doc_url_form"):
                doc_ref = st.text_input(
                    "Document URL or Local Path *",
                    placeholder="https://example.com/admission_brochure.pdf or data/my_college.pdf",
                )
                submit_doc = st.form_submit_button("📥 Ingest Document", type="primary")

            if submit_doc:
                if not doc_ref.strip():
                    st.error("Please enter a valid document URL or file path.")
                else:
                    with st.spinner(f"Processing {doc_ref}..."):
                        try:
                            res = process_document(doc_ref.strip(), token=token)
                            st.success(
                                f"✅ Ingested successfully! "
                                f"Total chunks: {res.get('total_chunks', 0)}, "
                                f"Inserted: {res.get('inserted_chunks', 0)}"
                            )
                            st.rerun()
                        except APIError as e:
                            st.error(f"Ingestion failed: {e.message}")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # 2. Ingested Documents List
    try:
        data = list_documents(token)
        documents = data.get("documents", [])
    except APIError as e:
        st.error(f"Failed to fetch documents: {e.message}")
        render_footer()
        return

    st.markdown('<div class="coligo-card">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="coligo-card-header">📄 Ingested Documents ({len(documents)})</div>',
        unsafe_allow_html=True,
    )

    if not documents:
        st.info("No documents have been ingested into the vector store yet.")
    else:
        header = st.columns([3.5, 1.2, 1.8, 1])
        for col, label in zip(
            header,
            ["DOCUMENT REFERENCE", "CHUNKS", "INGESTED DATE", "ACTION"],
            strict=False,
        ):
            col.markdown(f"**{label}**")

        for doc in documents:
            row = st.columns([3.5, 1.2, 1.8, 1])
            with row[0]:
                doc_icon = row_icon_html("📄", "purple")
                st.markdown(
                    f'<div class="coligo-item-row">'
                    f"{doc_icon}"
                    f'<span class="coligo-item-title">{doc["document_ref"]}</span></div>',
                    unsafe_allow_html=True,
                )
            with row[1]:
                st.markdown(
                    badge(f"{doc['chunk_count']} chunks"), unsafe_allow_html=True
                )
            with row[2]:
                st.caption(doc["created_at"][:19].replace("T", " "))
            with row[3]:
                if st.button("🗑️ Delete", key=f"del_doc_{doc['id']}"):
                    try:
                        delete_document(token, doc["id"])
                        st.success("Document deleted.")
                        st.rerun()
                    except APIError as e:
                        st.error(e.message)

    st.markdown("</div>", unsafe_allow_html=True)
    render_footer()
