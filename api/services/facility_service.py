from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.exceptions import NotAuthorizedError, ResourceNotFoundError
from api.core.logging import get_logger
from api.models import Facility
from api.schemas.facility import FacilityCreate, FacilityUpdate

logger = get_logger(__name__)


async def list_facilities(db: AsyncSession, college_id: int) -> list[Facility]:
    query = (
        select(Facility).where(Facility.college_id == college_id).order_by(Facility.id)
    )
    return list((await db.execute(query)).scalars().all())


async def _get_owned_facility(
    db: AsyncSession, facility_id: int, college_id: int
) -> Facility:
    facility = (
        (await db.execute(select(Facility).where(Facility.id == facility_id)))
        .scalars()
        .first()
    )
    if facility is None:
        raise ResourceNotFoundError(f"Facility with id {facility_id} not found")
    if facility.college_id != college_id:
        raise NotAuthorizedError("You do not have access to this facility")
    return facility


async def create_facility(
    db: AsyncSession, college_id: int, data: FacilityCreate
) -> Facility:
    facility = Facility(college_id=college_id, **data.model_dump())
    db.add(facility)
    await db.commit()
    await db.refresh(facility)
    logger.info("facility_created", college_id=college_id, facility_id=facility.id)
    return facility


async def update_facility(
    db: AsyncSession, college_id: int, facility_id: int, data: FacilityUpdate
) -> Facility:
    facility = await _get_owned_facility(db, facility_id, college_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(facility, field, value)
    await db.commit()
    await db.refresh(facility)
    logger.info("facility_updated", college_id=college_id, facility_id=facility_id)
    return facility


async def delete_facility(db: AsyncSession, college_id: int, facility_id: int) -> None:
    facility = await _get_owned_facility(db, facility_id, college_id)
    await db.delete(facility)
    await db.commit()
    logger.info("facility_deleted", college_id=college_id, facility_id=facility_id)
