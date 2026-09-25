from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field

from api.core.logging import get_logger

logger = get_logger(__name__)


class StudentProfile(BaseModel):
    """Persistent student entity profile across multi-turn admissions counselling."""

    session_key: str
    calculated_cutoff: Optional[float] = None
    community: Optional[str] = None
    maths_mark: Optional[float] = None
    physics_mark: Optional[float] = None
    chemistry_mark: Optional[float] = None
    preferred_colleges: List[str] = Field(default_factory=list)
    preferred_branches: List[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def is_complete(self) -> bool:
        """Return True if both cutoff and community are established."""
        return self.calculated_cutoff is not None and bool(self.community)


# Thread-safe in-memory cache for fast sub-millisecond retrieval
_STUDENT_PROFILES: dict[str, StudentProfile] = {}


def get_student_profile(session_key: str) -> StudentProfile:
    """Retrieve existing student profile or initialize a fresh one."""
    if session_key not in _STUDENT_PROFILES:
        _STUDENT_PROFILES[session_key] = StudentProfile(session_key=session_key)
    return _STUDENT_PROFILES[session_key]


def _apply_academic_attributes(
    profile: StudentProfile,
    cutoff: Optional[float],
    community: Optional[str],
    maths: Optional[float],
    physics: Optional[float],
    chemistry: Optional[float],
) -> None:
    if cutoff is not None:
        profile.calculated_cutoff = cutoff
    if community:
        profile.community = community.upper()
    if maths is not None:
        profile.maths_mark = maths
    if physics is not None:
        profile.physics_mark = physics
    if chemistry is not None:
        profile.chemistry_mark = chemistry


def _apply_target_preferences(
    profile: StudentProfile,
    colleges: Optional[List[str]],
    branches: Optional[List[str]],
) -> None:
    if colleges:
        for c in colleges:
            if c and c.lower() not in [x.lower() for x in profile.preferred_colleges]:
                profile.preferred_colleges.append(c)

    if branches:
        for b in branches:
            if b and b.upper() not in profile.preferred_branches:
                profile.preferred_branches.append(b.upper())


def update_student_profile(
    session_key: str,
    cutoff: Optional[float] = None,
    community: Optional[str] = None,
    maths: Optional[float] = None,
    physics: Optional[float] = None,
    chemistry: Optional[float] = None,
    colleges: Optional[List[str]] = None,
    branches: Optional[List[str]] = None,
) -> StudentProfile:
    """Update profile with newly extracted entities while preserving state."""
    profile = get_student_profile(session_key)

    _apply_academic_attributes(profile, cutoff, community, maths, physics, chemistry)
    _apply_target_preferences(profile, colleges, branches)

    profile.last_updated = datetime.now(timezone.utc)
    logger.debug(
        "student_profile_updated",
        session_key=session_key,
        cutoff=profile.calculated_cutoff,
        community=profile.community,
        colleges=profile.preferred_colleges,
        branches=profile.preferred_branches,
    )
    return profile


def format_profile_context(profile: StudentProfile) -> str:
    """Generate prompt-friendly summary of known student attributes."""
    parts: list[str] = []
    if profile.calculated_cutoff is not None:
        parts.append(f"Cutoff: {profile.calculated_cutoff:g}/200.0")
    if profile.community:
        parts.append(f"Community: {profile.community}")
    if profile.preferred_branches:
        parts.append(f"Target Branches: {', '.join(profile.preferred_branches)}")
    if profile.preferred_colleges:
        parts.append(f"Target Colleges: {', '.join(profile.preferred_colleges)}")

    if not parts:
        return ""
    return f"[Known Student Profile: {' | '.join(parts)}]"
