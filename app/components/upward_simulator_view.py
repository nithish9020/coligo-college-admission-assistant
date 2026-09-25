"""TNEA Upward Movement & Vacancy Clearance Simulator Component for Coligo."""

import asyncio
from typing import Any

import pandas as pd
import streamlit as st

from api.core.database import async_session_factory
from api.services.upward_movement_simulator import simulate_upward_movement

COLLEGE_OPTIONS = [
    "Sri Krishna College of Engineering and Technology (SKCET)",
    "PSG College of Technology (Autonomous)",
    "Coimbatore Institute of Technology (CIT)",
    "Kumaraguru College of Technology (KCT)",
    "Government College of Technology (GCT)",
    "Kongu Engineering College (Autonomous)",
    "Bannari Amman Institute of Technology (BIT)",
    "Sri Ramakrishna Engineering College (SREC)",
    "Sri Eshwar College of Engineering",
    "KPR Institute of Engineering and Technology",
    "PSG Institute of Technology and Applied Research (PSG iTech)",
]

BRANCH_OPTIONS = [
    "Mechanical Engineering",
    "Civil Engineering",
    "Electrical and Electronics Engineering (EEE)",
    "Electronics and Communication Engineering (ECE)",
    "Information Technology (IT)",
    "Computer Science and Engineering (CSE)",
    "Artificial Intelligence and Data Science (AI & DS)",
    "Biomedical Engineering",
    "Biotechnology",
]


def render_upward_simulator_view() -> None:
    """Render interactive TNEA Upward Movement decision simulator."""
    st.markdown("## 🔄 TNEA Upward Movement & Vacancy Simulator")
    st.caption(
        "Evaluate your tentative seat allotment, calculate upgrade probabilities "
        "for higher choices, and select the optimal counselling strategy."
    )

    default_cutoff = float(st.session_state.get("cutoff", 182.0))
    default_comm = st.session_state.get("community", "BC")

    with st.container(border=True):
        st.markdown("#### 1️⃣ Your Tentative Allotment Details")
        c1, c2 = st.columns(2)
        with c1:
            college_sel = st.selectbox(
                "Tentatively Allotted College",
                options=COLLEGE_OPTIONS,
                index=0,
            )
        with c2:
            branch_sel = st.selectbox(
                "Tentatively Allotted Department",
                options=BRANCH_OPTIONS,
                index=0,
            )

        c3, c4 = st.columns(2)
        with c3:
            cutoff_in = st.number_input(
                "Your Cutoff Score",
                min_value=77.5,
                max_value=200.0,
                value=default_cutoff,
                step=0.25,
            )
        with c4:
            comm_sel = st.selectbox(
                "Community Category",
                options=["OC", "BC", "BCM", "MBC", "SC", "SCA", "ST"],
                index=["OC", "BC", "BCM", "MBC", "SC", "SCA", "ST"].index(default_comm)
                if default_comm in ["OC", "BC", "BCM", "MBC", "SC", "SCA", "ST"]
                else 1,
            )

        target_branches = st.multiselect(
            "Higher Preference Target Branches",
            options=["cse", "it", "aids", "ece", "eee"],
            default=["cse", "it", "aids"],
            help="Select the departments placed higher on your choice sheet.",
        )

        st.button(
            "🚀 Simulate Upward Movement Chances",
            type="primary",
            use_container_width=True,
        )

    # Clean short names for simulation query
    short_college = (
        "Sri Krishna"
        if "Krishna" in college_sel
        else ("PSG" if "PSG" in college_sel else "CIT")
    )
    short_branch = branch_sel.split()[0]

    async def _run_sim() -> dict[str, Any]:
        async with async_session_factory() as db:
            return await simulate_upward_movement(
                db=db,
                allotted_college=short_college,
                allotted_branch=short_branch,
                student_cutoff=cutoff_in,
                community=comm_sel,
                target_branches=target_branches or ["cse", "it", "aids"],
            )

    sim_res = None
    with st.spinner("Analyzing cutoff margins and historical vacancy clearance..."):
        try:
            sim_res = asyncio.run(_run_sim())
        except Exception as e:
            st.error(f"Simulation error: {e}")

    if sim_res:
        st.write("")
        st.markdown("#### 2️⃣ Strategic Recommendation")

        rec_color = (
            "#059669" if "Option 2" in sim_res["recommended_option"] else "#2563EB"
        )
        st.markdown(
            f"""
            <div style="background: #F0FDF4; border: 2px solid {rec_color}; border-radius: 10px; padding: 18px; margin-bottom: 20px;">
                <div style="font-size: 0.95rem; font-weight: 700; color: #166534; text-transform: uppercase;">Coligo Strategic Verdict</div>
                <div style="font-size: 1.5rem; font-weight: 800; color: {rec_color}; margin: 6px 0;">{sim_res["recommended_option"]}</div>
                <p style="margin: 0; color: #15803D; font-size: 0.95rem; line-height: 1.5;">{sim_res["strategy_advice"]}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("#### 3️⃣ Upward Movement Target Breakdown")
        targets = sim_res.get("upward_targets", [])
        if targets:
            table_rows = []
            for t in targets[:8]:
                gap_val = t["cutoff_gap"]
                gap_str = f"+{gap_val:g}" if gap_val > 0 else f"{gap_val:g}"
                table_rows.append(
                    {
                        "Target Branch": t["branch_name"],
                        "2024 Cutoff": f"{t['cutoff_mark']:g}",
                        "Cutoff Gap": gap_str,
                        "Likelihood": f"{t['probability_icon']} {t['probability_label']}",
                        "Clearance Est.": f"{t['probability_pct']}%",
                    }
                )
            df = pd.DataFrame(table_rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No higher cutoff target branches found for the chosen filters.")

        st.write("")
        st.markdown("#### 4️⃣ Complete TNEA Round Decision Matrix")
        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(
                """
                <div style="background: #F8FAFC; border: 1.5px solid #CBD5E1; border-radius: 8px; padding: 14px;">
                    <div style="font-weight: 700; color: #334155;">1️⃣ Accept & Join</div>
                    <p style="font-size: 0.85rem; color: #64748B; margin-top: 6px;">
                        Locks your current seat immediately. Allotment order generated; you exit counselling.
                    </p>
                    <span style="font-size: 0.8rem; background: #E2E8F0; padding: 2px 8px; border-radius: 4px; font-weight: 600;">Zero Risk</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with m2:
            st.markdown(
                """
                <div style="background: #F0FDF4; border: 1.5px solid #22C55E; border-radius: 8px; padding: 14px;">
                    <div style="font-weight: 700; color: #166534;">2️⃣ Accept & Upward 🌟</div>
                    <p style="font-size: 0.85rem; color: #15803D; margin-top: 6px;">
                        Retains current seat safely. If a choice ranked higher vacates, you are automatically upgraded!
                    </p>
                    <span style="font-size: 0.8rem; background: #DCFCE7; color: #166534; padding: 2px 8px; border-radius: 4px; font-weight: 700;">Recommended</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with m3:
            st.markdown(
                """
                <div style="background: #FEF2F2; border: 1.5px solid #EF4444; border-radius: 8px; padding: 14px;">
                    <div style="font-weight: 700; color: #991B1B;">3️⃣ Decline & Upward</div>
                    <p style="font-size: 0.85rem; color: #B91C1C; margin-top: 6px;">
                        Rejects current seat completely. If higher choices don't vacate, you leave empty-handed!
                    </p>
                    <span style="font-size: 0.8rem; background: #FEE2E2; color: #991B1B; padding: 2px 8px; border-radius: 4px; font-weight: 700;">High Risk</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
