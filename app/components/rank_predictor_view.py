"""TNEA State Overall Rank & Counselling Round Predictor View."""

import pandas as pd
import streamlit as st

from api.services.rank_predictor import predict_tnea_rank


def render_rank_predictor_view() -> None:
    """Render interactive TNEA cutoff-to-rank regression predictor and round advisory."""
    st.markdown("## TNEA State Overall & Community Rank Predictor")
    st.caption(
        "TNEA engineering seat allotments depend strictly on State Overall Merit Rank "
        "and Community Rank, not marks alone."
    )

    student_cutoff = st.session_state.get("cutoff", 186.5)
    current_comm = st.session_state.get("community", "BC")

    col_in1, col_in2 = st.columns([2, 1])
    with col_in1:
        cutoff_val = st.slider(
            "Select or Adjust Your Cutoff Score",
            min_value=77.5,
            max_value=200.0,
            value=float(student_cutoff),
            step=0.25,
            format="%.2f",
        )
    with col_in2:
        comm_val = st.selectbox(
            "Community Quota Category",
            options=["OC", "BC", "BCM", "MBC", "SC", "SCA", "ST"],
            index=["OC", "BC", "BCM", "MBC", "SC", "SCA", "ST"].index(current_comm)
            if current_comm in ["OC", "BC", "BCM", "MBC", "SC", "SCA", "ST"]
            else 1,
        )

    res = predict_tnea_rank(cutoff_val, comm_val)

    st.markdown("### Predicted Rank & Eligibility Results")
    m1, m2, m3 = st.columns(3)

    with m1:
        st.metric(
            "State Overall Rank",
            f"~{res['overall_rank_min']:,} - {res['overall_rank_max']:,}",
        )
    with m2:
        st.metric(
            f"Community Rank ({comm_val})",
            f"~{res['community_rank_min']:,} - {res['community_rank_max']:,}",
        )
    with m3:
        st.metric(
            "Counselling Stage",
            f"ROUND {res['round_number']}",
            delta=res["round_name"],
            delta_color="normal",
        )

    st.info(f"**Expert Round {res['round_number']} Strategy:**\n\n{res['strategy']}")

    st.divider()

    st.markdown("### TNEA Rank Bracket Reference Model")
    brackets_data = [
        {
            "Cutoff Range": "199.0 - 200.0",
            "State Overall Rank": "1 - 250",
            "Round": "Round 1",
            "Eligibility": "CEG Guindy, PSG Tech, MIT Anna Univ",
        },
        {
            "Cutoff Range": "197.0 - 198.99",
            "State Overall Rank": "251 - 1,200",
            "Round": "Round 1",
            "Eligibility": "PSG Tech, CIT, GCT, SKCET Top Circuit",
        },
        {
            "Cutoff Range": "194.0 - 196.99",
            "State Overall Rank": "1,201 - 4,500",
            "Round": "Round 1",
            "Eligibility": "SKCET, CIT, PSG iTech, KCT Circuit",
        },
        {
            "Cutoff Range": "190.0 - 193.99",
            "State Overall Rank": "4,501 - 9,500",
            "Round": "Round 1",
            "Eligibility": "SKCET, KCT, Bannari Amman, Kongu CSE/IT",
        },
        {
            "Cutoff Range": "185.0 - 189.99",
            "State Overall Rank": "9,501 - 16,500",
            "Round": "Round 1",
            "Eligibility": "SKCET, Sri Eshwar, SREC, KPR Circuit",
        },
        {
            "Cutoff Range": "179.0 - 184.99",
            "State Overall Rank": "16,501 - 25,000",
            "Round": "Round 1",
            "Eligibility": "Autonomous Top 30 Colleges (30+ choices)",
        },
        {
            "Cutoff Range": "174.0 - 178.99",
            "State Overall Rank": "25,001 - 38,000",
            "Round": "Round 2",
            "Eligibility": "Kongu, Sri Eshwar, Bannari, Karpagam",
        },
        {
            "Cutoff Range": "165.0 - 173.99",
            "State Overall Rank": "38,001 - 56,000",
            "Round": "Round 2",
            "Eligibility": "Dr. Mahalingam, SRIT, Hindusthan, SNS",
        },
        {
            "Cutoff Range": "145.0 - 164.99",
            "State Overall Rank": "56,001 - 98,000",
            "Round": "Round 2/3",
            "Eligibility": "Established Accredited Institutions",
        },
    ]
    st.dataframe(pd.DataFrame(brackets_data), use_container_width=True, hide_index=True)
