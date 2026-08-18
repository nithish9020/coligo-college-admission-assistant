import os
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.core.config import settings
from api.core.exceptions import InvalidFileError, ResourceNotFoundError
from api.core.logging import get_logger
from api.models import College, Course, Facility
from api.schemas.brochure_extraction import ApplyBrochureExtractionRequest
from api.schemas.college import (
    CollegeDetailResponse,
    CollegeListItem,
    CollegeProfileUpdate,
)

logger = get_logger(__name__)

ALLOWED_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg"}


async def get_college_by_id(db: AsyncSession, college_id: int) -> College:
    query = (
        select(College)
        .where(College.id == college_id)
        .options(
            selectinload(College.courses),
            selectinload(College.facilities),
            selectinload(College.brochures),
        )
    )
    college = (await db.execute(query)).scalars().first()
    if college is None:
        raise ResourceNotFoundError(f"College with id {college_id} not found")
    return college


async def update_profile(
    db: AsyncSession, college_id: int, data: CollegeProfileUpdate
) -> College:
    college = await get_college_by_id(db, college_id)
    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(college, field, value)
    await db.commit()
    await db.refresh(college)
    logger.info("college_profile_updated", college_id=college_id)
    return college


async def apply_brochure_extraction(
    db: AsyncSession, college_id: int, data: ApplyBrochureExtractionRequest
) -> College:
    """Write the college-reviewed subset of a brochure extraction: profile
    field updates plus new Course/Facility rows. Nothing here is called
    unless the college has already confirmed it in the review UI."""
    college = await get_college_by_id(db, college_id)

    if data.college_profile is not None:
        updates = data.college_profile.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(college, field, value)

    for course_data in data.courses:
        db.add(Course(college_id=college_id, **course_data.model_dump()))

    for facility_data in data.facilities:
        db.add(Facility(college_id=college_id, **facility_data.model_dump()))

    await db.commit()
    await db.refresh(college)
    logger.info(
        "brochure_extraction_applied",
        college_id=college_id,
        profile_updated=data.college_profile is not None,
        courses_added=len(data.courses),
        facilities_added=len(data.facilities),
    )
    return college


async def save_logo(
    db: AsyncSession, college_id: int, filename: str, content: bytes
) -> College:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_LOGO_EXTENSIONS:
        raise InvalidFileError("Logo must be a PNG or JPG image")
    if len(content) > settings.MAX_LOGO_SIZE_MB * 1024 * 1024:
        raise InvalidFileError(
            f"Logo must be smaller than {settings.MAX_LOGO_SIZE_MB}MB"
        )

    college = await get_college_by_id(db, college_id)

    logo_dir = os.path.join(settings.UPLOAD_DIR, "logos", str(college_id))
    os.makedirs(logo_dir, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{ext}"
    full_path = os.path.join(logo_dir, stored_name)
    with open(full_path, "wb") as f:
        f.write(content)

    college.logo_path = full_path.replace(os.sep, "/")
    await db.commit()
    await db.refresh(college)
    logger.info("college_logo_uploaded", college_id=college_id, path=college.logo_path)
    return college


async def list_all_colleges(db: AsyncSession) -> list[CollegeListItem]:
    query = select(College).options(
        selectinload(College.courses), selectinload(College.brochures)
    )
    colleges = (await db.execute(query)).scalars().all()
    return [
        CollegeListItem(
            id=c.id,
            college_name=c.college_name,
            email=c.email,
            contact_person=c.contact_person,
            is_active=c.is_active,
            course_count=len(c.courses),
            brochure_count=len(c.brochures),
            created_at=c.created_at,
        )
        for c in colleges
    ]


async def get_college_detail(
    db: AsyncSession, college_id: int
) -> CollegeDetailResponse:
    college = await get_college_by_id(db, college_id)
    base = CollegeDetailResponse.model_validate(college, from_attributes=True)
    base.course_count = len(college.courses)
    base.brochure_count = len(college.brochures)
    base.facility_count = len(college.facilities)
    return base
