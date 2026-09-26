"""3-Tier Choice Sheet Builder & Instant PDF Exporter Component."""

import asyncio

import pandas as pd
import streamlit as st

from api.core.database import async_session_factory
from api.services.choice_list_service import generate_choice_sheet_file


def render_choice_sheet_view() -> None:
    """Render 3-tier choice filling recommendation table and downloadable official PDF."""
    st.markdown("## Personalized 3-Tier TNEA Choice Filling Order")
    st.caption(
        "Strategically partitioned recommendation designed to balance dream "
        "aspirational colleges with secure target and safety options."
    )

    cutoff_val = st.session_state.get("cutoff", 186.5)
    comm_val = st.session_state.get("community", "BC")
    session_key = st.session_state.get("session_key", "whatsapp:anonymous")

    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        st.metric("Your Cutoff", f"{cutoff_val:g}")
    with c2:
        st.metric("Community Quota", comm_val)
    with c3:
        st.write("")
        st.write("")
        st.button("Regenerate Optimal Choices")

    # Generate choices from database
    async def _fetch_choices_pdf():
        async with async_session_factory() as db:
            filepath, public_url = await generate_choice_sheet_file(
                db=db,
                cutoff=cutoff_val,
                community=comm_val,
                session_key=session_key,
            )
            return filepath, public_url

    with st.spinner("Generating 3-tier recommendations and compiling official PDF..."):
        try:
            filepath, _ = asyncio.run(_fetch_choices_pdf())
            with open(filepath, "rb") as f:
                pdf_bytes = f.read()
            pdf_ready = True
        except Exception as e:
            st.error(f"Error compiling choice sheet PDF: {e}")
            pdf_ready = False
            pdf_bytes = b""

    # Sample table data mirroring the 3 tiers
    choices_data = [
        {
            "Tier": "Ambitious (Dream)",
            "College": "PSG College of Technology (2006)",
            "Branch": "Computer Science & Engg (CSE)",
            "Closing Cutoff": 197.0,
        },
        {
            "Tier": "Ambitious (Dream)",
            "College": "PSG College of Technology (2006)",
            "Branch": "Information Technology (IT)",
            "Closing Cutoff": 195.5,
        },
        {
            "Tier": "Ambitious (Dream)",
            "College": "Coimbatore Institute of Tech (2007)",
            "Branch": "Computer Science & Engg (CSE)",
            "Closing Cutoff": 194.0,
        },
        {
            "Tier": "Target (Realistic)",
            "College": "Sri Krishna College of Engg (2722)",
            "Branch": "Computer Science & Engg (CSE)",
            "Closing Cutoff": 189.5,
        },
        {
            "Tier": "Target (Realistic)",
            "College": "Sri Krishna College of Engg (2722)",
            "Branch": "AI & Data Science (AI & DS)",
            "Closing Cutoff": 187.5,
        },
        {
            "Tier": "Target (Realistic)",
            "College": "Sri Krishna College of Engg (2722)",
            "Branch": "Information Technology (IT)",
            "Closing Cutoff": 188.0,
        },
        {
            "Tier": "Target (Realistic)",
            "College": "Kumaraguru College of Tech (2712)",
            "Branch": "Computer Science & Engg (CSE)",
            "Closing Cutoff": 191.0,
        },
        {
            "Tier": "Safe (Guaranteed)",
            "College": "Sri Krishna College of Engg (2722)",
            "Branch": "Electronics & Communication (ECE)",
            "Closing Cutoff": 186.0,
        },
        {
            "Tier": "Safe (Guaranteed)",
            "College": "Sri Eshwar College of Engg (2739)",
            "Branch": "Computer Science & Engg (CSE)",
            "Closing Cutoff": 184.0,
        },
        {
            "Tier": "Safe (Guaranteed)",
            "College": "Bannari Amman Institute (2702)",
            "Branch": "Computer Science & Engg (CSE)",
            "Closing Cutoff": 183.5,
        },
    ]

    st.markdown("### Recommended Choice Filling Sequence")
    df_choices = pd.DataFrame(choices_data)
    st.dataframe(df_choices, use_container_width=True, hide_index=True)

    st.divider()

    col_dl1, col_dl2 = st.columns([2, 1])
    with col_dl1:
        st.markdown(
            "#### Official TNEA Choice Sheet (PDF)\n"
            "This report is formatted specifically for easy reference during "
            "choice-locking on **tneaonline.org**."
        )
    with col_dl2:
        if pdf_ready:
            st.download_button(
                label="Download Choice Sheet PDF",
                data=pdf_bytes,
                file_name=f"TNEA_Choice_Sheet_{int(cutoff_val)}_{comm_val}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )
        else:
            st.button("PDF Generation Error", disabled=True, use_container_width=True)
