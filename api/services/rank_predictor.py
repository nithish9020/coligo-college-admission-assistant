"""TNEA State Overall Rank and Community Rank Predictor."""

from typing import Any

from api.core.logging import get_logger

logger = get_logger(__name__)

# Cutoff brackets mapping:
# (cutoff_low, cutoff_high, min_rank, max_rank, round, round_name, strategy)
RANK_BRACKETS = [
    (
        199.0,
        200.0,
        1,
        250,
        1,
        "Round 1 (Top 1%)",
        "Direct eligibility for CEG Guindy, PSG Tech, and MIT Anna Univ CSE/ECE.",
    ),
    (
        197.0,
        198.99,
        251,
        1200,
        1,
        "Round 1 (Elite)",
        "Strong chance for PSG Tech, CIT, GCT, and SKCET top circuit branches.",
    ),
    (
        194.0,
        196.99,
        1201,
        4500,
        1,
        "Round 1 (High Merit)",
        "Guaranteed top tier autonomous colleges (PSG iTech, CIT, SKCET, KCT).",
    ),
    (
        190.0,
        193.99,
        4501,
        9500,
        1,
        "Round 1 (Merit)",
        "Aim for SKCET, KCT, Bannari Amman, and Kongu CSE/IT/AIDS branches.",
    ),
    (
        185.0,
        189.99,
        9501,
        16500,
        1,
        "Round 1 (Upper Mid)",
        "Competitive for SKCET, Sri Eshwar, SREC, KPR, and Bannari Amman.",
    ),
    (
        179.0,
        184.99,
        16501,
        25000,
        1,
        "Round 1 (Closing)",
        "Fill 30+ choices. Target circuit branches in autonomous institutions.",
    ),
    (
        174.0,
        178.99,
        25001,
        38000,
        2,
        "Round 2 (Top)",
        "Prime seat availability in Kongu, Sri Eshwar, Karpagam, and Bannari.",
    ),
    (
        165.0,
        173.99,
        38001,
        56000,
        2,
        "Round 2 (Mid)",
        "Strong choices in Dr. Mahalingam, SRIT, Hindusthan, and SNS.",
    ),
    (
        155.0,
        164.99,
        56001,
        78000,
        2,
        "Round 2 (Closing)",
        "Focus on established accredited autonomous colleges across districts.",
    ),
    (
        145.0,
        154.99,
        78001,
        98000,
        3,
        "Round 3 (Opening)",
        "Ensure broad branch selection including ECE, EEE, and Mechanical.",
    ),
    (
        120.0,
        144.99,
        98001,
        135000,
        3,
        "Round 3 (Mid)",
        "Prioritize colleges with verified NAAC/NBA accreditation & placement records.",
    ),
    (
        77.5,
        119.99,
        135001,
        180000,
        3,
        "Round 3 (Extended)",
        "Add maximum choices (50+) to guarantee seat allocation in Round 3.",
    ),
]

# Community percentage distribution factors (approximate TNEA quota ratios)
COMMUNITY_RATIOS = {
    "OC": 1.0,
    "BC": 0.48,
    "BCM": 0.04,
    "MBC": 0.22,
    "SC": 0.15,
    "SCA": 0.03,
    "ST": 0.01,
}


def predict_tnea_rank(cutoff: float, community: str = "BC") -> dict[str, Any]:
    """Calculate predicted State Overall Rank, Community Rank, and Counselling Round."""
    comm = community.upper().strip() if community else "BC"
    c = max(min(cutoff, 200.0), 77.5)

    bracket_match = None
    for low, high, min_r, max_r, rnd, rnd_name, strat in RANK_BRACKETS:
        if low <= c <= high:
            bracket_match = (min_r, max_r, rnd, rnd_name, strat)
            break

    if not bracket_match:
        bracket_match = (
            135001,
            180000,
            3,
            "Round 3",
            "Fill maximum choices to secure admission.",
        )

    min_rank, max_rank, round_num, round_name, strategy = bracket_match
    ratio = COMMUNITY_RATIOS.get(comm, 0.48)
    comm_min = max(1, int(min_rank * ratio))
    comm_max = max(comm_min + 50, int(max_rank * ratio))

    return {
        "cutoff": c,
        "community": comm,
        "overall_rank_min": min_rank,
        "overall_rank_max": max_rank,
        "community_rank_min": comm_min,
        "community_rank_max": comm_max,
        "round_number": round_num,
        "round_name": round_name,
        "strategy": strategy,
    }


def format_rank_prediction_message(cutoff: float, community: str = "BC") -> str:
    """Format rank prediction as a clean WhatsApp-native card."""
    res = predict_tnea_rank(cutoff, community)

    return (
        f"*TNEA Rank & Counselling Round Prediction*\n\n"
        f"• *Your Cutoff:* *{res['cutoff']:g} / 200.0*\n"
        f"• *Community Quota:* *{res['community']}*\n\n"
        f"*Predicted State Overall Rank:*\n"
        f"• *~{res['overall_rank_min']:,} to {res['overall_rank_max']:,}*\n\n"
        f"*Predicted Community Rank ({res['community']}):*\n"
        f"• *~{res['community_rank_min']:,} to {res['community_rank_max']:,}*\n\n"
        f"*Eligible Counselling Stage:*\n"
        f"• *ROUND {res['round_number']}* — _{res['round_name']}_\n\n"
        f"*Expert Round Strategy:*\n"
        f"{res['strategy']}\n\n"
        f"Would you like me to generate your *3-Tier Choice Filling Order* "
        f"for Round {res['round_number']}?"
    )
