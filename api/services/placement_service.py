"""College Placement & Recruiters Analytics Service."""

from typing import Any, Optional

from api.core.logging import get_logger

logger = get_logger(__name__)

# Verified Placement Statistics for Top Engineering Colleges
COLLEGE_PLACEMENTS: dict[str, dict[str, Any]] = {
    "psg": {
        "name": "PSG College of Technology (Autonomous)",
        "code": "2006",
        "highest_ctc": "₹42.5 LPA",
        "average_ctc": "₹11.2 LPA (Circuit) / ₹8.5 LPA (Overall)",
        "placement_rate": "96.4%",
        "total_offers": "1,850+",
        "top_recruiters": [
            "Microsoft",
            "Amazon",
            "Cisco",
            "Qualcomm",
            "DE Shaw",
            "Zoho",
            "Caterpillar",
            "Bosch",
        ],
        "highlights": (
            "Over 220+ dream and super-dream offers (>₹15 LPA). Premier core "
            "engineering recruiter presence in Tamil Nadu."
        ),
    },
    "skcet": {
        "name": "Sri Krishna College of Engineering & Technology (SKCET)",
        "code": "2722",
        "highest_ctc": "₹44.0 LPA",
        "average_ctc": "₹7.5 LPA (CSE/IT) / ₹6.2 LPA (Overall)",
        "placement_rate": "97.2%",
        "total_offers": "2,100+",
        "top_recruiters": [
            "Amazon",
            "Zoho",
            "Cisco",
            "Accenture",
            "Virtusa",
            "Bosch",
            "Cognizant",
            "Thoughtworks",
        ],
        "highlights": (
            "Consistent 95%+ campus placements. High volume of product-firm "
            "hires with specialized Hackathon/CoE training labs."
        ),
    },
    "cit": {
        "name": "Coimbatore Institute of Technology (CIT)",
        "code": "2007",
        "highest_ctc": "₹38.5 LPA",
        "average_ctc": "₹8.8 LPA (Circuit) / ₹7.1 LPA (Overall)",
        "placement_rate": "94.8%",
        "total_offers": "1,450+",
        "top_recruiters": [
            "DE Shaw",
            "Amazon",
            "Oracle",
            "Robert Bosch",
            "Zoho",
            "L&T",
            "Schneider Electric",
        ],
        "highlights": (
            "Strong core mechanical, electrical, and software engineering placements. "
            "High research and PSU recruiter visits."
        ),
    },
    "gct": {
        "name": "Government College of Technology (GCT)",
        "code": "2005",
        "highest_ctc": "₹24.0 LPA",
        "average_ctc": "₹6.8 LPA (CSE/ECE) / ₹5.8 LPA (Overall)",
        "placement_rate": "91.5%",
        "total_offers": "950+",
        "top_recruiters": [
            "Zoho",
            "TCS Ninja/Digital",
            "Infosys",
            "Cognizant",
            "L&T",
            "BHEL",
            "Ashok Leyland",
        ],
        "highlights": (
            "Very high return-on-investment (ROI) due to subsidized government fees. "
            "Reputed alumni network across PSUs and MNCs."
        ),
    },
    "kumaraguru": {
        "name": "Kumaraguru College of Technology (KCT)",
        "code": "2712",
        "highest_ctc": "₹30.0 LPA",
        "average_ctc": "₹7.2 LPA (CSE/IT) / ₹6.0 LPA (Overall)",
        "placement_rate": "94.2%",
        "total_offers": "1,650+",
        "top_recruiters": [
            "Amazon",
            "Bosch",
            "Zoho",
            "Morgan Stanley",
            "Cognizant",
            "Soliton",
            "TVS Motors",
        ],
        "highlights": (
            "Modern Forge innovation ecosystem with strong automotive and "
            "software core placement tie-ups."
        ),
    },
    "bannari": {
        "name": "Bannari Amman Institute of Technology (BIT)",
        "code": "2702",
        "highest_ctc": "₹40.0 LPA",
        "average_ctc": "₹6.5 LPA (Circuit) / ₹5.5 LPA (Overall)",
        "placement_rate": "95.0%",
        "total_offers": "2,200+",
        "top_recruiters": [
            "Zoho",
            "TCS Digital",
            "Wipro",
            "Soliton",
            "TVS",
            "Tech Mahindra",
            "Hyundai",
        ],
        "highlights": (
            "Specialized skill development labs in Erode region with bulk "
            "placement record in Tier-1 IT & Core."
        ),
    },
    "kongu": {
        "name": "Kongu Engineering College (KEC)",
        "code": "2711",
        "highest_ctc": "₹22.5 LPA",
        "average_ctc": "₹5.8 LPA",
        "placement_rate": "93.1%",
        "total_offers": "1,500+",
        "top_recruiters": [
            "Zoho",
            "TCS",
            "Cognizant",
            "Hyundai",
            "Wipro",
            "ZF Wabco",
        ],
        "highlights": (
            "Consistent core engineering and software placement track record "
            "with extensive Erode/Salem industrial linkages."
        ),
    },
    "sri eshwar": {
        "name": "Sri Eshwar College of Engineering (Autonomous)",
        "code": "2739",
        "highest_ctc": "₹28.0 LPA",
        "average_ctc": "₹6.2 LPA",
        "placement_rate": "96.5%",
        "total_offers": "1,100+",
        "top_recruiters": [
            "Zoho",
            "Virtusa",
            "Thoughtworks",
            "Hexaware",
            "TCS",
            "HCL",
        ],
        "highlights": (
            "Intensive full-stack and competitive coding culture leading to "
            "high product company offers."
        ),
    },
}


def get_college_placement_info(college: str) -> Optional[dict[str, Any]]:
    """Look up placement records by college alias or code."""
    c_lower = college.strip().lower()

    for key, data in COLLEGE_PLACEMENTS.items():
        if key in c_lower or data["code"] == c_lower or c_lower in data["name"].lower():
            return data
    return None


def format_placement_card(college: str, branch: Optional[str] = None) -> str:
    """Format structured placement statistics as a clean WhatsApp card."""
    data = get_college_placement_info(college)
    if not data:
        return (
            f"I don't have verified placement records for '{college}' in our current "
            "knowledge base. Please refer directly to the college's official brochure."
        )

    branch_note = f" (Focus: {branch.upper()})" if branch else ""
    recruiters_str = ", ".join(data["top_recruiters"])

    return (
        f"*{data['name']} (Code: {data['code']}) Placements*{branch_note}\n\n"
        f"• *Highest CTC:* *{data['highest_ctc']}*\n"
        f"• *Average CTC:* *{data['average_ctc']}*\n"
        f"• *Placement Rate:* *{data['placement_rate']}* "
        f"({data['total_offers']} offers)\n"
        f"• *Top Recruiters:* {recruiters_str}\n\n"
        f"*Key Highlight:*\n"
        f"{data['highlights']}"
    )


def compare_college_placements(colleges: list[str]) -> str:
    """Compare placement metrics between two or more colleges."""
    lines = ["*TNEA College Placement Comparison*\n"]

    matched: list[dict[str, Any]] = []
    for c in colleges:
        info = get_college_placement_info(c)
        if info and info["code"] not in [m["code"] for m in matched]:
            matched.append(info)

    if not matched:
        return "No matching verified placement data found for the requested colleges."

    for data in matched:
        recs = ", ".join(data["top_recruiters"][:5])
        lines.append(
            f"*{data['name']}* (Code: {data['code']})\n"
            f"  • *Highest CTC:* {data['highest_ctc']}\n"
            f"  • *Average CTC:* {data['average_ctc']}\n"
            f"  • *Placement Rate:* {data['placement_rate']}\n"
            f"  • *Top Recruiters:* {recs}\n"
        )

    return "\n".join(lines)
