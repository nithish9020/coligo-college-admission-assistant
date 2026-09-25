"""Head-to-Head College Comparator Component for Coligo Streamlit Portal."""

import pandas as pd
import streamlit as st

from app.services.chart_builder import (
    BENCHMARK_CUTOFFS,
    build_head_to_head_chart,
)

COLLEGE_SPECS = {
    "SKCET (2722)": {
        "full_name": "Sri Krishna College of Engineering & Technology",
        "district": "Coimbatore",
        "nirf_band": "Top 100",
        "naac": "A++ Grade",
        "highest_ctc": "₹44.0 LPA",
        "avg_ctc": "₹7.5 LPA",
        "intake": "1,440 seats",
        "strengths": "AI & Software, Amazon/Zoho recruitments, Modern Labs",
    },
    "PSG Tech (2006)": {
        "full_name": "PSG College of Technology",
        "district": "Coimbatore",
        "nirf_band": "Top 65",
        "naac": "A++ Grade",
        "highest_ctc": "₹42.5 LPA",
        "avg_ctc": "₹11.2 LPA",
        "intake": "1,380 seats",
        "strengths": "Pioneer Core Industry, Research, Global Alumni Network",
    },
    "CIT Coimbatore (2007)": {
        "full_name": "Coimbatore Institute of Technology",
        "district": "Coimbatore",
        "nirf_band": "Top 100",
        "naac": "A Grade",
        "highest_ctc": "₹38.5 LPA",
        "avg_ctc": "₹8.8 LPA",
        "intake": "1,140 seats",
        "strengths": "Government-Aided, Strong Core Engineering, Low Fees",
    },
    "Kumaraguru KCT (2712)": {
        "full_name": "Kumaraguru College of Technology",
        "district": "Coimbatore",
        "nirf_band": "Top 100",
        "naac": "A++ Grade",
        "highest_ctc": "₹30.0 LPA",
        "avg_ctc": "₹6.5 LPA",
        "intake": "1,560 seats",
        "strengths": "Campus Life, Forge Innovation Hub, Sports & Clubs",
    },
    "Bannari Amman (2702)": {
        "full_name": "Bannari Amman Institute of Technology",
        "district": "Erode",
        "nirf_band": "Top 100",
        "naac": "A+ Grade",
        "highest_ctc": "₹40.0 LPA",
        "avg_ctc": "₹6.5 LPA",
        "intake": "1,680 seats",
        "strengths": "Residential Campus, Coding Culture, Specialized Labs",
    },
    "Sri Eshwar (2739)": {
        "full_name": "Sri Eshwar College of Engineering",
        "district": "Coimbatore",
        "nirf_band": "Rank 151-200",
        "naac": "A+ Grade",
        "highest_ctc": "₹28.0 LPA",
        "avg_ctc": "₹6.2 LPA",
        "intake": "1,080 seats",
        "strengths": "Product Placements, Intensive Coding, Faculty Mentorship",
    },
}


def render_compare_view() -> None:
    """Render interactive side-by-side college comparator and visual diff."""
    st.markdown("## ⚖️ Head-to-Head College Comparator")
    st.caption(
        "Direct side-by-side evaluation of cutoffs, packages, NIRF rankings, and "
        "department strengths to make the right choice-filling decision."
    )

    cutoff_val = st.session_state.get("cutoff", 186.5)
    comm_val = st.session_state.get("community", "BC")

    col_options = list(COLLEGE_SPECS.keys())

    c_sel1, c_sel2, c_sel3 = st.columns([2, 2, 1])
    with c_sel1:
        college_a = st.selectbox(
            "Select College A",
            options=col_options,
            index=0,
            key="compare_col_a",
        )
    with c_sel2:
        default_b = 1 if len(col_options) > 1 else 0
        college_b = st.selectbox(
            "Select College B",
            options=col_options,
            index=default_b,
            key="compare_col_b",
        )
    with c_sel3:
        comm_filter = st.selectbox(
            "Community Quota",
            options=["OC", "BC", "MBC", "SC"],
            index=["OC", "BC", "MBC", "SC"].index(comm_val)
            if comm_val in ["OC", "BC", "MBC", "SC"]
            else 1,
            key="compare_comm_filter",
        )

    if college_a == college_b:
        st.warning("Please pick two different colleges to compare side-by-side.")
        return

    spec_a = COLLEGE_SPECS[college_a]
    spec_b = COLLEGE_SPECS[college_b]

    # Institutional Summary Cards
    st.markdown("### 🏛️ Institutional Highlights")
    card_col1, card_col2 = st.columns(2)

    with card_col1:
        st.markdown(
            f"""
            <div style="background: #F8FAFC; border: 1.5px solid #4F46E5; border-radius: 10px; padding: 16px;">
                <h4 style="margin: 0 0 6px 0; color: #4F46E5;">{college_a}</h4>
                <p style="margin: 0 0 8px 0; font-size: 0.9rem; color: #475569;">{spec_a["full_name"]}</p>
                <div style="font-size: 0.88rem; line-height: 1.6;">
                    📍 <strong>District:</strong> {spec_a["district"]}<br>
                    🏆 <strong>NIRF Ranking:</strong> {spec_a["nirf_band"]}<br>
                    🎖️ <strong>NAAC:</strong> {spec_a["naac"]}<br>
                    💼 <strong>Highest Package:</strong> {spec_a["highest_ctc"]}<br>
                    📈 <strong>Average CTC:</strong> {spec_a["avg_ctc"]}<br>
                    ⭐ <strong>Key Strength:</strong> {spec_a["strengths"]}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with card_col2:
        st.markdown(
            f"""
            <div style="background: #F8FAFC; border: 1.5px solid #06B6D4; border-radius: 10px; padding: 16px;">
                <h4 style="margin: 0 0 6px 0; color: #06B6D4;">{college_b}</h4>
                <p style="margin: 0 0 8px 0; font-size: 0.9rem; color: #475569;">{spec_b["full_name"]}</p>
                <div style="font-size: 0.88rem; line-height: 1.6;">
                    📍 <strong>District:</strong> {spec_b["district"]}<br>
                    🏆 <strong>NIRF Ranking:</strong> {spec_b["nirf_band"]}<br>
                    🎖️ <strong>NAAC:</strong> {spec_b["naac"]}<br>
                    💼 <strong>Highest Package:</strong> {spec_b["highest_ctc"]}<br>
                    📈 <strong>Average CTC:</strong> {spec_b["avg_ctc"]}<br>
                    ⭐ <strong>Key Strength:</strong> {spec_b["strengths"]}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Cutoff Comparison Visual Chart
    st.markdown(f"### 📊 Cutoff Benchmark Comparison ({comm_filter} Quota)")
    chart = build_head_to_head_chart(college_a, college_b, community=comm_filter)
    st.altair_chart(chart, use_container_width=True)

    # Branch Cutoff Table & Verdict
    st.markdown("### 📋 Branch-by-Branch Comparison & Personalized Verdict")
    branches = ["CSE", "IT", "AI & DS", "ECE", "Mech"]
    rows = []

    for br in branches:
        raw_a = next(
            (
                d["cutoff"]
                for d in BENCHMARK_CUTOFFS
                if d["college"] == college_a
                and d["branch"] == br
                and d["community"] == comm_filter
            ),
            None,
        )
        c_a_val: float | None = float(str(raw_a)) if raw_a is not None else None

        raw_b = next(
            (
                d["cutoff"]
                for d in BENCHMARK_CUTOFFS
                if d["college"] == college_b
                and d["branch"] == br
                and d["community"] == comm_filter
            ),
            None,
        )
        c_b_val: float | None = float(str(raw_b)) if raw_b is not None else None

        delta_str = "—"
        if c_a_val is not None and c_b_val is not None:
            diff = c_a_val - c_b_val
            delta_str = f"+{diff:.1f}" if diff > 0 else f"{diff:.1f}"

        # Verdict based on student's cutoff
        verdict = "—"
        if c_a_val is not None:
            if cutoff_val >= c_a_val + 2.0:
                verdict = f"Safe in {college_a.split(' ')[0]}"
            elif cutoff_val >= c_a_val - 1.5:
                verdict = f"Target Match ({college_a.split(' ')[0]})"
            else:
                verdict = f"Reach in {college_a.split(' ')[0]}"

        rows.append(
            {
                "Branch": br,
                f"{college_a} ({comm_filter})": f"{c_a_val:.1f}" if c_a_val else "N/A",
                f"{college_b} ({comm_filter})": f"{c_b_val:.1f}" if c_b_val else "N/A",
                "Difference (Δ)": delta_str,
                f"Verdict for Cutoff {cutoff_val:g}": verdict,
            }
        )

    df_comp = pd.DataFrame(rows)
    st.dataframe(df_comp, use_container_width=True, hide_index=True)

    # Recommendation Box
    st.info(
        f"💡 **Counsellor Recommendation for Cutoff {cutoff_val:g} ({comm_val}):**\n\n"
        f"• If your priority is **Product Company Placements & Modern AI/Tech**: {college_a} offers aggressive placement training with Tier-1 recruiters.\n"
        f"• If your priority is **Core Engineering, Alumni Legacy & Research**: {college_b} has historic industry partnerships and deep faculty expertise."
    )
