import re
from typing import Optional, Tuple


def calculate_tnea_cutoff(
    maths: float, physics: float, chemistry: float
) -> Tuple[float, str]:
    """Calculate the official TNEA engineering cutoff out of 200.0.

    Official Tamil Nadu DTE / Anna University Formula:
    Cutoff = Maths + (Physics / 2.0) + (Chemistry / 2.0)
    """
    if not (0.0 <= maths <= 100.0):
        raise ValueError(f"Maths mark ({maths}) must be between 0 and 100.")
    if not (0.0 <= physics <= 100.0):
        raise ValueError(f"Physics mark ({physics}) must be between 0 and 100.")
    if not (0.0 <= chemistry <= 100.0):
        raise ValueError(f"Chemistry mark ({chemistry}) must be between 0 and 100.")

    phy_component = physics / 2.0
    chem_component = chemistry / 2.0
    cutoff = round(maths + phy_component + chem_component, 2)

    explanation = (
        f"**TNEA Cutoff Calculation**: {maths:g} (Maths) + "
        f"{phy_component:g} (Physics/2) + {chem_component:g} (Chemistry/2) = "
        f"**{cutoff:g} / 200.0**"
    )
    return cutoff, explanation


def extract_marks_from_text(
    text: str,
) -> Tuple[Optional[dict[str, float]], Optional[float]]:
    """Extract subject marks or directly stated cutoff mark from user text."""
    lower = text.lower()

    # 1. Check for directly stated cutoff or calculated cutoff in text/history
    calc_match = re.search(
        r"cutoff[^\n]*?=\s*[\d\.\+\-\/\s]+=\s*[*`]*(\d{2,3}(?:\.\d{1,2})?)",
        lower,
    )
    direct_cutoff = None
    if calc_match:
        direct_cutoff = float(calc_match.group(1))
    else:
        cutoff_match = re.search(
            r"(?:my\s+)?cutoff\s*(?:score)?\s*(?:is|=|:)?\s*[*`]*(\d{2,3}(?:\.\d{1,2})?)",
            lower,
        )
        if cutoff_match:
            val = float(cutoff_match.group(1))
            if 0.0 <= val <= 200.0:
                direct_cutoff = val

    # 2. Extract subject marks: Maths, Physics, Chemistry
    # Supports "maths: 100", "85 in maths", "physics: 90", "95 in physics"
    m_match = re.search(
        r"(?:(?:maths?|mat|m)\s*(?:is|=|:|\-)?\s*(\d{1,3}(?:\.\d{1,2})?)"
        r"|(\d{1,3}(?:\.\d{1,2})?)\s*(?:in|for|marks?\s*in)?\s*(?:maths?|mat|m)\b)",
        lower,
    )
    p_match = re.search(
        r"(?:(?:physics?|phy|p)\s*(?:is|=|:|\-)?\s*(\d{1,3}(?:\.\d{1,2})?)"
        r"|(\d{1,3}(?:\.\d{1,2})?)\s*(?:in|for|marks?\s*in)?\s*(?:physics?|phy|p)\b)",
        lower,
    )
    c_match = re.search(
        r"(?:(?:chemistry?|chem|che|c)\s*(?:is|=|:|\-)?\s*(\d{1,3}(?:\.\d{1,2})?)"
        r"|(\d{1,3}(?:\.\d{1,2})?)\s*(?:in|for|marks?\s*in)?\s*(?:chemistry?|chem|che|c)\b)",
        lower,
    )

    if m_match and p_match and c_match:
        m_val = float(m_match.group(1) or m_match.group(2))
        p_val = float(p_match.group(1) or p_match.group(2))
        c_val = float(c_match.group(1) or c_match.group(2))

        if 0.0 <= m_val <= 100.0 and 0.0 <= p_val <= 100.0 and 0.0 <= c_val <= 100.0:
            return {
                "maths": m_val,
                "physics": p_val,
                "chemistry": c_val,
            }, direct_cutoff

    return None, direct_cutoff
