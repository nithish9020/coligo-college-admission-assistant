import os
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
from api.core.exceptions import (
    InvalidFileError,
    NotAuthorizedError,
    ResourceNotFoundError,
)
from api.core.logging import get_logger
from api.models import Brochure
from api.schemas.brochure import BrochureUpdate

logger = get_logger(__name__)


async def list_brochures(db: AsyncSession, college_id: int) -> list[Brochure]:
    query = (
        select(Brochure)
        .where(Brochure.college_id == college_id)
        .order_by(Brochure.id.desc())
    )
    return list((await db.execute(query)).scalars().all())


async def _get_owned_brochure(
    db: AsyncSession, brochure_id: int, college_id: int
) -> Brochure:
    brochure = (
        await db.execute(select(Brochure).where(Brochure.id == brochure_id))
    ).scalars().first()
    if brochure is None:
        raise ResourceNotFoundError(f"Brochure with id {brochure_id} not found")
    if brochure.college_id != college_id:
        raise NotAuthorizedError("You do not have access to this brochure")
    return brochure


async def get_brochure_for_download(
    db: AsyncSession, brochure_id: int, college_id: int | None
) -> Brochure:
    """Fetch a brochure. If college_id is provided, ownership is enforced
    (college users); admins pass college_id=None to download any brochure."""
    brochure = (
        await db.execute(select(Brochure).where(Brochure.id == brochure_id))
    ).scalars().first()
    if brochure is None:
        raise ResourceNotFoundError(f"Brochure with id {brochure_id} not found")
    if college_id is not None and brochure.college_id != college_id:
        raise NotAuthorizedError("You do not have access to this brochure")
    return brochure


async def upload_brochure(
    db: AsyncSession,
    college_id: int,
    title: str,
    category: str | None,
    filename: str,
    content: bytes,
) -> Brochure:
    if not filename.lower().endswith(".pdf"):
        raise InvalidFileError("Brochures must be uploaded as PDF files")
    if len(content) > settings.MAX_BROCHURE_SIZE_MB * 1024 * 1024:
        raise InvalidFileError(
            f"Brochure must be smaller than {settings.MAX_BROCHURE_SIZE_MB}MB"
        )

    brochure_dir = os.path.join(settings.UPLOAD_DIR, "brochures", str(college_id))
    os.makedirs(brochure_dir, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}.pdf"
    full_path = os.path.join(brochure_dir, stored_name)
    with open(full_path, "wb") as f:
        f.write(content)

    brochure = Brochure(
        college_id=college_id,
        title=title,
        category=category,
        file_path=full_path.replace(os.sep, "/"),
        file_size_bytes=len(content),
    )
    db.add(brochure)
    await db.commit()
    await db.refresh(brochure)
    logger.info(
        "brochure_uploaded", college_id=college_id, brochure_id=brochure.id
    )
    return brochure


async def update_brochure(
    db: AsyncSession, college_id: int, brochure_id: int, data: BrochureUpdate
) -> Brochure:
    brochure = await _get_owned_brochure(db, brochure_id, college_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(brochure, field, value)
    await db.commit()
    await db.refresh(brochure)
    logger.info("brochure_updated", college_id=college_id, brochure_id=brochure_id)
    return brochure


async def delete_brochure(db: AsyncSession, college_id: int, brochure_id: int) -> None:
    brochure = await _get_owned_brochure(db, brochure_id, college_id)
    file_path = brochure.file_path
    await db.delete(brochure)
    await db.commit()
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except OSError as e:
        logger.warning(
            "brochure_file_delete_failed", brochure_id=brochure_id, error=str(e)
        )
    logger.info("brochure_deleted", college_id=college_id, brochure_id=brochure_id)
