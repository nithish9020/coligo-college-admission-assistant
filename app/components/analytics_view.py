"""Cutoff Visualizer, Comparative Graphs and Searchable Data Tables."""

import pandas as pd
import streamlit as st

from app.services.chart_builder import BENCHMARK_CUTOFFS, build_cutoff_comparison_chart


def render_analytics_view() -> None:
    """Render interactive college cutoff comparison visualizer and data tables."""
    st.markdown("## TNEA Cutoff Visualizer & Comparative Analytics")
    st.caption(
        "Explore historical closing cutoff marks across premier autonomous institutions "
        "and compare departments side-by-side."
    )

    student_cutoff = st.session_state.get("cutoff", 185.0)
    current_comm = st.session_state.get("community", "BC")

    # Filter controls
    f_col1, f_col2, f_col3 = st.columns([2, 1, 1])

    with f_col1:
        college_options = [
            "SKCET (2722)",
            "PSG Tech (2006)",
            "CIT Coimbatore (2007)",
            "Kumaraguru KCT (2712)",
        ]
        selected_colleges = st.multiselect(
            "Select Institutions to Compare",
            options=college_options,
            default=["SKCET (2722)", "PSG Tech (2006)", "CIT Coimbatore (2007)"],
        )

    with f_col2:
        comm_filter = st.selectbox(
            "Community Quota",
            options=["OC", "BC", "MBC", "SC"],
            index=["OC", "BC", "MBC", "SC"].index(current_comm)
            if current_comm in ["OC", "BC", "MBC", "SC"]
            else 1,
        )

    with f_col3:
        st.metric("Your Cutoff", f"{student_cutoff:g}", delta=None)

    # Render Visual Grouped Bar Chart
    st.markdown("### Branch Closing Cutoffs Comparison")
    if selected_colleges:
        chart = build_cutoff_comparison_chart(
            selected_colleges=selected_colleges,
            community=comm_filter,
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info(
            "Select at least one institution above to render the comparative bar chart."
        )

    # Searchable, sortable Dataframe Table
    st.markdown("### Detailed Cutoff Data Table")
    df = pd.DataFrame(BENCHMARK_CUTOFFS)
    df_comm = df[df["community"] == comm_filter]

    if selected_colleges:
        df_comm = df_comm[df_comm["college"].isin(selected_colleges)]

    # Compute student admission eligibility status
    df_display = df_comm.copy()

    def get_status(closing_mark: float) -> str:
        diff = student_cutoff - closing_mark
        if diff >= 0:
            return "Safe / Highly Likely"
        elif diff >= -2.5:
            return "Target / Strong Chance"
        return "Ambitious / Dream"

    df_display["Eligibility Status"] = df_display["cutoff"].apply(get_status)
    df_display = df_display.rename(
        columns={
            "college": "Institution",
            "branch": "Department",
            "community": "Quota",
            "cutoff": "Closing Mark",
        }
    )

    st.dataframe(
        df_display.sort_values(by="Closing Mark", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
