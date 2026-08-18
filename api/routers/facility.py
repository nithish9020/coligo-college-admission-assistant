from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.deps import AuthenticatedUser, get_current_college, get_current_user
from api.core.exceptions import NotAuthorizedError
from api.core.logging import get_logger
from api.schemas.facility import FacilityCreate, FacilityResponse, FacilityUpdate
from api.services.facility_service import (
    create_facility,
    delete_facility,
    list_facilities,
    update_facility,
)

router = APIRouter(prefix="/facilities", tags=["Facilities"])
logger = get_logger(__name__)


@router.get(
    "",
    response_model=list[FacilityResponse],
    summary="List facilities (own college, or ?college_id= for admins)",
)
async def get_facilities(
    college_id: int | None = Query(
        None, description="Required for admin callers; ignored for college callers"
    ),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FacilityResponse]:
    if user.role == "college":
        target_college_id = user.college_id
    else:
        if college_id is None:
            raise NotAuthorizedError("college_id query param is required for admins")
        target_college_id = college_id

    facilities = await list_facilities(db, target_college_id)  # type: ignore[arg-type]
    return [FacilityResponse.model_validate(f) for f in facilities]


@router.post(
    "",
    response_model=FacilityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new facility for the logged-in college",
)
async def add_facility(
    data: FacilityCreate,
    user: AuthenticatedUser = Depends(get_current_college),
    db: AsyncSession = Depends(get_db),
) -> FacilityResponse:
    facility = await create_facility(db, user.college_id, data)  # type: ignore[arg-type]
    return FacilityResponse.model_validate(facility)


@router.put(
    "/{facility_id}",
    response_model=FacilityResponse,
    summary="Update a facility owned by the logged-in college",
)
async def edit_facility(
    facility_id: int,
    data: FacilityUpdate,
    user: AuthenticatedUser = Depends(get_current_college),
    db: AsyncSession = Depends(get_db),
) -> FacilityResponse:
    facility = await update_facility(db, user.college_id, facility_id, data)  # type: ignore[arg-type]
    return FacilityResponse.model_validate(facility)


@router.delete(
    "/{facility_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a facility owned by the logged-in college",
)
async def remove_facility(
    facility_id: int,
    user: AuthenticatedUser = Depends(get_current_college),
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_facility(db, user.college_id, facility_id)  # type: ignore[arg-type]
