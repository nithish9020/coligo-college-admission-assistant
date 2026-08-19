import re

# Dictionary of common student typos, abbreviations, and Tanglish admission terms
TYPO_MAPPINGS = {
    r"\bcutof\b": "cutoff",
    r"\bcuttoff\b": "cutoff",
    r"\bcut-off\b": "cutoff",
    r"\bfeese\b": "fees",
    r"\bfess\b": "fees",
    r"\bclg\b": "college",
    r"\bclge\b": "college",
    r"\bengeneering\b": "engineering",
    r"\benginering\b": "engineering",
    r"\badmision\b": "admission",
    r"\bhostle\b": "hostel",
    r"\bmarkes\b": "marks",
    r"\bcounselling\b": "counseling",
}

ABBREVIATION_EXPANSIONS = {
    r"\bcse\b": "computer science engineering (CSE)",
    r"\bece\b": "electronics and communication engineering (ECE)",
    r"\baids\b": "artificial intelligence and data science (AI & DS)",
    r"\beee\b": "electrical and electronics engineering (EEE)",
    r"\bmech\b": "mechanical engineering (MECH)",
    r"\bit\b": "information technology (IT)",
}


def normalize_query(query: str) -> str:
    """Normalize student typos, abbreviations, and Tanglish terms for improved vector retrieval."""
    if not query:
        return query

    normalized = query.lower().strip()

    # 1. Correct Common Typos
    for pattern, replacement in TYPO_MAPPINGS.items():
        normalized = re.sub(pattern, replacement, normalized)

    # 2. Expand Abbreviated Branch Names
    for pattern, replacement in ABBREVIATION_EXPANSIONS.items():
        normalized = re.sub(pattern, replacement, normalized)

    return normalized
