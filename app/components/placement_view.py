"""Placement & Recruiter Analytics View for Coligo Streamlit Portal."""

import streamlit as st

from api.services.placement_service import (
    COLLEGE_PLACEMENTS,
    get_college_placement_info,
)
from app.services.chart_builder import (
    build_placement_comparison_chart,
    build_recruiter_split_chart,
)


def render_placement_view() -> None:
    """Render structured placement statistics, comparative charts, and recruiters."""
    st.markdown("## 💼 Placement & Recruiter Analytics")
    st.caption(
        "Verified campus placement records, average packages, and top recruiters "
        "across premier Tamil Nadu engineering colleges."
    )

    st.markdown("### 📊 Highest vs Average CTC Comparison (₹ LPA)")
    p_chart = build_placement_comparison_chart()
    st.altair_chart(p_chart, use_container_width=True)

    c_split1, c_split2 = st.columns([1, 1])
    with c_split1:
        st.markdown("### 🏢 Hiring Sector Breakdown")
        st.caption("Distribution across Product Firms, Core, and IT Services:")
        r_chart = build_recruiter_split_chart()
        st.altair_chart(r_chart, use_container_width=True)

    with c_split2:
        st.markdown("### 🔍 College Placement Profile")
        selected_key = st.selectbox(
            "Select Institution",
            options=list(COLLEGE_PLACEMENTS.keys()),
            format_func=lambda k: COLLEGE_PLACEMENTS[k]["name"],
        )
        info = get_college_placement_info(selected_key)
        if info:
            with st.container(border=True):
                st.markdown(f"#### {info['name']} (Code: {info['code']})")
                m1, m2 = st.columns(2)
                with m1:
                    st.metric("Highest CTC", info["highest_ctc"])
                    st.metric("Placement Rate", info["placement_rate"])
                with m2:
                    st.metric("Average CTC", info["average_ctc"])
                    st.metric("Total Offers", info["total_offers"])

                st.markdown(
                    f"**🏢 Key Recruiters:** {', '.join(info['top_recruiters'])}"
                )
                st.info(f"💡 {info['highlights']}")
