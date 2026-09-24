import streamlit as st
from utils.api_client import (
    APIError,
    get_choice_recommendations,
    search_cutoffs,
)
from utils.styling import (
    badge,
    page_header,
    render_footer,
)


def render_choice_filling() -> None:
    token = st.session_state.token

    page_header(
        "🎯",
        "TNEA Choice Filling & Cutoff Engine",
        "Algorithmic 3-tier preference list generator (Dream, Target, Safe) and official cutoff database",
        "blue",
    )

    tab_rec, tab_search = st.tabs(
        ["🚀 Choice Filling Generator", "🔍 Cutoff Database Explorer"]
    )

    with tab_rec:
        st.markdown(
            "Generate an optimal, verified TNEA counselling preference list "
            "based on a student's marks and community category."
        )

        c1, c2, c3 = st.columns([1.5, 1.2, 2.5])
        with c1:
            cutoff = st.number_input(
                "TNEA Cutoff Mark (out of 200)",
                min_value=70.0,
                max_value=200.0,
                value=185.0,
                step=0.5,
            )
        with c2:
            community = st.selectbox(
                "Community",
                options=["BC", "OC", "BCM", "MBC", "SC", "SCA", "ST"],
                index=0,
            )
        with c3:
            branches = st.multiselect(
                "Preferred Branches",
                options=[
                    "CSE",
                    "IT",
                    "AIDS",
                    "AIML",
                    "ECE",
                    "EEE",
                    "MECH",
                    "CIVIL",
                    "CSBS",
                ],
                default=["CSE", "IT", "ECE"],
            )

        if st.button("✨ Generate Choice Filling List", type="primary"):
            try:
                with st.spinner("Analyzing cutoff distributions across colleges..."):
                    recs = get_choice_recommendations(
                        cutoff=cutoff,
                        community=community,
                        branches=branches or None,
                        token=token,
                    )

                st.success(
                    f"Generated personalized choice recommendations for Cutoff **{cutoff}** ({community})"
                )

                col_amb, col_tgt, col_safe = st.columns(3)

                with col_amb:
                    st.markdown("#### 🌟 Ambitious (Dream)")
                    st.caption("Reach colleges (Cutoff +0.1 to +3.0)")
                    amb = recs.get("ambitious", [])
                    if not amb:
                        st.info("No colleges in this range.")
                    for it in amb:
                        diff = (
                            f"+{it['difference']:g}"
                            if it["difference"] > 0
                            else f"{it['difference']:g}"
                        )
                        st.markdown(
                            f"**{it['college_name']}**  \n"
                            f"📌 {it['branch_name']}  \n"
                            f"Closing: **{it['cutoff_mark']}** ({diff})"
                        )
                        st.divider()

                with col_tgt:
                    st.markdown("#### 🎯 Realistic (Target)")
                    st.caption("Strong likelihood (Cutoff -2.5 to 0.0)")
                    tgt = recs.get("target", [])
                    if not tgt:
                        st.info("No colleges in this range.")
                    for it in tgt:
                        st.markdown(
                            f"**{it['college_name']}**  \n"
                            f"📌 {it['branch_name']}  \n"
                            f"Closing: **{it['cutoff_mark']}** ({it['difference']:g})"
                        )
                        st.divider()

                with col_safe:
                    st.markdown("#### 🛡️ Safe (Backup)")
                    st.caption("Guaranteed safety (Cutoff -6.0 to -2.5)")
                    safe = recs.get("safe", [])
                    if not safe:
                        st.info("No colleges in this range.")
                    for it in safe:
                        st.markdown(
                            f"**{it['college_name']}**  \n"
                            f"📌 {it['branch_name']}  \n"
                            f"Closing: **{it['cutoff_mark']}** ({it['difference']:g})"
                        )
                        st.divider()

            except APIError as e:
                st.error(f"Failed to generate choices: {e.message}")

    with tab_search:
        st.markdown(
            "Explore verified official TNEA closing cutoffs across all ingested institutions."
        )
        sc1, sc2, sc3 = st.columns([2, 2, 1.5])
        with sc1:
            search_col = st.text_input(
                "College Name", placeholder="e.g. PSG, Sri Krishna, CIT, Kongu"
            )
        with sc2:
            search_br = st.text_input(
                "Branch", placeholder="e.g. Computer Science, Electronics"
            )
        with sc3:
            search_comm = st.selectbox(
                "Filter Community",
                options=["ALL", "OC", "BC", "BCM", "MBC", "SC", "SCA", "ST"],
                index=0,
            )

        if st.button("🔍 Search Cutoffs"):
            try:
                results = search_cutoffs(
                    college=search_col or None,
                    branch=search_br or None,
                    community=None if search_comm == "ALL" else search_comm,
                    limit=50,
                    token=token,
                )
                if not results:
                    st.info("No cutoff records found matching your filters.")
                else:
                    st.write(f"Found **{len(results)}** records:")
                    for row in results:
                        st.markdown(
                            f"• **{row['college_name']}** | {row['branch_name']} | "
                            f"{badge(row['community'])} | Cutoff: **{row['cutoff_mark']}**",
                            unsafe_allow_html=True,
                        )
            except APIError as e:
                st.error(f"Search failed: {e.message}")

    render_footer()
