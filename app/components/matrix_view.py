"""Seat Matrix & Reservation Quota Pie Charts View."""

import streamlit as st

from app.services.chart_builder import build_college_intake_chart, build_quota_pie_chart


def render_matrix_view() -> None:
    """Render Tamil Nadu reservation quota pie charts and college seat matrix."""
    st.markdown("## 🥧 TNEA Seat Matrix & Reservation Quota Visualizer")
    st.caption(
        "Understand government reservation distribution policies and "
        "institutional seat intakes."
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🏛️ Tamil Nadu Government Reservation (100%)")
        st.markdown(
            "Engineering seat allocations follow statutory reservation guidelines:"
        )
        q_chart = build_quota_pie_chart()
        st.altair_chart(q_chart, use_container_width=True)

        st.info(
            "💡 **Special 7.5% Preferential Quota**: 7.5% of seats across all "
            "government and autonomous colleges are reserved on a preferential basis "
            "for students who studied in Tamil Nadu Government Schools (6th-12th)."
        )

    with col2:
        st.markdown("### 🎓 SKCET Coimbatore (2722) Department Intake")
        st.markdown(
            "Distribution of approved intake seats across engineering departments:"
        )
        intake_chart = build_college_intake_chart()
        st.altair_chart(intake_chart, use_container_width=True)

        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.metric("Total Intake", "1,080+")
        with m_col2:
            st.metric("Circuit Seats", "660")
        with m_col3:
            st.metric("Core / Mech", "240")
