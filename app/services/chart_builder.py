"""Visual Altair Chart Builders for Coligo Streamlit Portal."""

from typing import cast

import altair as alt
import pandas as pd

# Verified Cutoff Data for Visual Charting
BENCHMARK_CUTOFFS = [
    {"college": "SKCET (2722)", "branch": "CSE", "community": "OC", "cutoff": 192.0},
    {"college": "SKCET (2722)", "branch": "CSE", "community": "BC", "cutoff": 189.5},
    {"college": "SKCET (2722)", "branch": "CSE", "community": "MBC", "cutoff": 187.0},
    {"college": "SKCET (2722)", "branch": "CSE", "community": "SC", "cutoff": 174.5},
    {"college": "SKCET (2722)", "branch": "IT", "community": "OC", "cutoff": 190.5},
    {"college": "SKCET (2722)", "branch": "IT", "community": "BC", "cutoff": 188.0},
    {"college": "SKCET (2722)", "branch": "IT", "community": "MBC", "cutoff": 185.0},
    {"college": "SKCET (2722)", "branch": "IT", "community": "SC", "cutoff": 172.0},
    {
        "college": "SKCET (2722)",
        "branch": "AI & DS",
        "community": "OC",
        "cutoff": 190.0,
    },
    {
        "college": "SKCET (2722)",
        "branch": "AI & DS",
        "community": "BC",
        "cutoff": 187.5,
    },
    {
        "college": "SKCET (2722)",
        "branch": "AI & DS",
        "community": "MBC",
        "cutoff": 184.0,
    },
    {
        "college": "SKCET (2722)",
        "branch": "AI & DS",
        "community": "SC",
        "cutoff": 171.0,
    },
    {"college": "SKCET (2722)", "branch": "ECE", "community": "OC", "cutoff": 189.0},
    {"college": "SKCET (2722)", "branch": "ECE", "community": "BC", "cutoff": 186.0},
    {"college": "SKCET (2722)", "branch": "ECE", "community": "MBC", "cutoff": 182.5},
    {"college": "SKCET (2722)", "branch": "ECE", "community": "SC", "cutoff": 168.0},
    {"college": "SKCET (2722)", "branch": "Mech", "community": "OC", "cutoff": 176.0},
    {"college": "SKCET (2722)", "branch": "Mech", "community": "BC", "cutoff": 171.0},
    {"college": "SKCET (2722)", "branch": "Mech", "community": "MBC", "cutoff": 165.0},
    {"college": "SKCET (2722)", "branch": "Mech", "community": "SC", "cutoff": 148.0},
    {"college": "PSG Tech (2006)", "branch": "CSE", "community": "OC", "cutoff": 198.5},
    {"college": "PSG Tech (2006)", "branch": "CSE", "community": "BC", "cutoff": 197.0},
    {
        "college": "PSG Tech (2006)",
        "branch": "CSE",
        "community": "MBC",
        "cutoff": 195.5,
    },
    {"college": "PSG Tech (2006)", "branch": "CSE", "community": "SC", "cutoff": 188.0},
    {"college": "PSG Tech (2006)", "branch": "IT", "community": "OC", "cutoff": 197.0},
    {"college": "PSG Tech (2006)", "branch": "IT", "community": "BC", "cutoff": 195.5},
    {"college": "PSG Tech (2006)", "branch": "IT", "community": "MBC", "cutoff": 193.5},
    {"college": "PSG Tech (2006)", "branch": "IT", "community": "SC", "cutoff": 185.0},
    {
        "college": "PSG Tech (2006)",
        "branch": "AI & DS",
        "community": "OC",
        "cutoff": 196.5,
    },
    {
        "college": "PSG Tech (2006)",
        "branch": "AI & DS",
        "community": "BC",
        "cutoff": 195.0,
    },
    {
        "college": "PSG Tech (2006)",
        "branch": "AI & DS",
        "community": "MBC",
        "cutoff": 193.0,
    },
    {
        "college": "PSG Tech (2006)",
        "branch": "AI & DS",
        "community": "SC",
        "cutoff": 183.5,
    },
    {"college": "PSG Tech (2006)", "branch": "ECE", "community": "OC", "cutoff": 196.0},
    {"college": "PSG Tech (2006)", "branch": "ECE", "community": "BC", "cutoff": 194.5},
    {
        "college": "PSG Tech (2006)",
        "branch": "ECE",
        "community": "MBC",
        "cutoff": 192.0,
    },
    {"college": "PSG Tech (2006)", "branch": "ECE", "community": "SC", "cutoff": 181.0},
    {
        "college": "PSG Tech (2006)",
        "branch": "Mech",
        "community": "OC",
        "cutoff": 189.0,
    },
    {
        "college": "PSG Tech (2006)",
        "branch": "Mech",
        "community": "BC",
        "cutoff": 185.5,
    },
    {
        "college": "PSG Tech (2006)",
        "branch": "Mech",
        "community": "MBC",
        "cutoff": 180.0,
    },
    {
        "college": "PSG Tech (2006)",
        "branch": "Mech",
        "community": "SC",
        "cutoff": 165.0,
    },
    {
        "college": "CIT Coimbatore (2007)",
        "branch": "CSE",
        "community": "OC",
        "cutoff": 196.0,
    },
    {
        "college": "CIT Coimbatore (2007)",
        "branch": "CSE",
        "community": "BC",
        "cutoff": 194.0,
    },
    {
        "college": "CIT Coimbatore (2007)",
        "branch": "CSE",
        "community": "MBC",
        "cutoff": 191.5,
    },
    {
        "college": "CIT Coimbatore (2007)",
        "branch": "CSE",
        "community": "SC",
        "cutoff": 181.0,
    },
    {
        "college": "CIT Coimbatore (2007)",
        "branch": "ECE",
        "community": "OC",
        "cutoff": 193.5,
    },
    {
        "college": "CIT Coimbatore (2007)",
        "branch": "ECE",
        "community": "BC",
        "cutoff": 191.0,
    },
    {
        "college": "CIT Coimbatore (2007)",
        "branch": "ECE",
        "community": "MBC",
        "cutoff": 187.0,
    },
    {
        "college": "CIT Coimbatore (2007)",
        "branch": "ECE",
        "community": "SC",
        "cutoff": 174.0,
    },
    {
        "college": "Kumaraguru KCT (2712)",
        "branch": "CSE",
        "community": "OC",
        "cutoff": 193.5,
    },
    {
        "college": "Kumaraguru KCT (2712)",
        "branch": "CSE",
        "community": "BC",
        "cutoff": 191.0,
    },
    {
        "college": "Kumaraguru KCT (2712)",
        "branch": "CSE",
        "community": "MBC",
        "cutoff": 188.0,
    },
    {
        "college": "Kumaraguru KCT (2712)",
        "branch": "CSE",
        "community": "SC",
        "cutoff": 176.0,
    },
]


def build_cutoff_comparison_chart(
    selected_colleges: list[str] | None = None,
    community: str = "BC",
) -> alt.Chart:
    """Grouped bar chart comparing cutoffs across branches and institutions."""
    df = pd.DataFrame(BENCHMARK_CUTOFFS)
    df_filtered = df[df["community"] == community.upper()]

    if selected_colleges:
        df_filtered = df_filtered[
            df_filtered["college"].str.contains("|".join(selected_colleges), case=False)
        ]

    chart = (
        alt.Chart(df_filtered)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X(
                "branch:N", title="Engineering Branch", axis=alt.Axis(labelAngle=0)
            ),
            y=alt.Y(
                "cutoff:Q",
                title=f"Closing Cutoff (Out of 200) — {community.upper()}",
                scale=alt.Scale(domain=[140, 200]),
            ),
            color=alt.Color(
                "college:N",
                title="Institution",
                scale=alt.Scale(scheme="tableau10"),
            ),
            tooltip=["college", "branch", "community", "cutoff"],
        )
        .properties(height=340)
        .configure_axis(grid=True, gridColor="#f0f2f6")
    )
    return cast(alt.Chart, chart)


def build_quota_pie_chart() -> alt.Chart:
    """Donut chart illustrating Tamil Nadu official reservation percentages."""
    quota_data = [
        {"Category": "Open Competition (OC)", "Percentage": 31.0, "Color": "#4F46E5"},
        {"Category": "Backward Class (BC)", "Percentage": 26.5, "Color": "#06B6D4"},
        {
            "Category": "Most Backward Class (MBC/DNC)",
            "Percentage": 20.0,
            "Color": "#10B981",
        },
        {"Category": "Scheduled Caste (SC)", "Percentage": 15.0, "Color": "#F59E0B"},
        {
            "Category": "Backward Class Muslim (BCM)",
            "Percentage": 3.5,
            "Color": "#8B5CF6",
        },
        {"Category": "SC Arunthathiyar (SCA)", "Percentage": 3.0, "Color": "#EF4444"},
        {"Category": "Scheduled Tribe (ST)", "Percentage": 1.0, "Color": "#EC4899"},
    ]
    df = pd.DataFrame(quota_data)

    chart = (
        alt.Chart(df)
        .mark_arc(innerRadius=65, outerRadius=120)
        .encode(
            theta=alt.Theta(field="Percentage", type="quantitative"),
            color=alt.Color(
                field="Category",
                type="nominal",
                scale=alt.Scale(
                    domain=[str(d["Category"]) for d in quota_data],
                    range=[str(d["Color"]) for d in quota_data],
                ),
                legend=alt.Legend(title="Community Quota", orient="right"),
            ),
            tooltip=["Category", "Percentage"],
        )
        .properties(height=300)
    )
    return cast(alt.Chart, chart)


def build_college_intake_chart() -> alt.Chart:
    """Donut chart illustrating SKCET branch intake seat matrix."""
    intake_data = [
        {"Branch": "Computer Science (CSE)", "Seats": 180},
        {"Branch": "Information Tech (IT)", "Seats": 180},
        {"Branch": "AI & Data Science", "Seats": 120},
        {"Branch": "Electronics & Comm (ECE)", "Seats": 180},
        {"Branch": "CS & Business Systems", "Seats": 60},
        {"Branch": "Cyber Security", "Seats": 60},
        {"Branch": "Mechanical Engineering", "Seats": 120},
        {"Branch": "Electrical & Electronics", "Seats": 60},
        {"Branch": "Civil Engineering", "Seats": 60},
    ]
    df = pd.DataFrame(intake_data)

    chart = (
        alt.Chart(df)
        .mark_arc(innerRadius=60, outerRadius=115)
        .encode(
            theta=alt.Theta(field="Seats", type="quantitative"),
            color=alt.Color(
                field="Branch",
                type="nominal",
                scale=alt.Scale(scheme="category20"),
                legend=alt.Legend(title="Branch Seats", orient="right"),
            ),
            tooltip=["Branch", "Seats"],
        )
        .properties(height=300)
    )
    return cast(alt.Chart, chart)


def build_placement_comparison_chart() -> alt.Chart:
    """Grouped bar chart comparing Highest CTC vs Average CTC across colleges."""
    placement_data = [
        {"college": "SKCET (2722)", "Metric": "Highest CTC", "LPA": 44.0},
        {"college": "SKCET (2722)", "Metric": "Average CTC (CSE/IT)", "LPA": 7.5},
        {"college": "PSG Tech (2006)", "Metric": "Highest CTC", "LPA": 42.5},
        {"college": "PSG Tech (2006)", "Metric": "Average CTC (CSE/IT)", "LPA": 11.2},
        {"college": "CIT Coimbatore (2007)", "Metric": "Highest CTC", "LPA": 38.5},
        {
            "college": "CIT Coimbatore (2007)",
            "Metric": "Average CTC (CSE/IT)",
            "LPA": 8.8,
        },
        {"college": "Kumaraguru KCT (2712)", "Metric": "Highest CTC", "LPA": 30.0},
        {
            "college": "Kumaraguru KCT (2712)",
            "Metric": "Average CTC (CSE/IT)",
            "LPA": 6.5,
        },
        {"college": "Bannari Amman (2702)", "Metric": "Highest CTC", "LPA": 40.0},
        {
            "college": "Bannari Amman (2702)",
            "Metric": "Average CTC (CSE/IT)",
            "LPA": 6.5,
        },
        {"college": "Sri Eshwar (2739)", "Metric": "Highest CTC", "LPA": 28.0},
        {"college": "Sri Eshwar (2739)", "Metric": "Average CTC (CSE/IT)", "LPA": 6.2},
    ]
    df = pd.DataFrame(placement_data)

    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X(
                "college:N",
                title="Engineering Institution",
                axis=alt.Axis(labelAngle=-25),
            ),
            y=alt.Y("LPA:Q", title="Package (₹ in LPA)"),
            color=alt.Color(
                "Metric:N",
                scale=alt.Scale(
                    domain=["Highest CTC", "Average CTC (CSE/IT)"],
                    range=["#4F46E5", "#06B6D4"],
                ),
            ),
            tooltip=["college", "Metric", "LPA"],
        )
        .properties(height=320)
    )
    return cast(alt.Chart, chart)


def build_recruiter_split_chart() -> alt.Chart:
    """Pie chart showing placement recruiter distribution (Product vs Core vs IT Services)."""
    data = [
        {
            "Category": "Product / Dream Firms (Amazon, Zoho, Cisco)",
            "Percentage": 38.5,
            "Color": "#4F46E5",
        },
        {
            "Category": "Core Engineering (Bosch, Caterpillar, L&T)",
            "Percentage": 24.5,
            "Color": "#10B981",
        },
        {
            "Category": "IT & Consulting (Accenture, Virtusa, Cognizant)",
            "Percentage": 37.0,
            "Color": "#F59E0B",
        },
    ]
    df = pd.DataFrame(data)

    chart = (
        alt.Chart(df)
        .mark_arc(innerRadius=65, outerRadius=115)
        .encode(
            theta=alt.Theta(field="Percentage", type="quantitative"),
            color=alt.Color(
                field="Category",
                type="nominal",
                scale=alt.Scale(
                    domain=[str(d["Category"]) for d in data],
                    range=[str(d["Color"]) for d in data],
                ),
                legend=alt.Legend(title="Recruiter Category", orient="bottom"),
            ),
            tooltip=["Category", "Percentage"],
        )
        .properties(height=280)
    )
    return cast(alt.Chart, chart)
