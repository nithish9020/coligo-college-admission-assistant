from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.deps import AuthenticatedUser, get_current_admin, get_current_college
from api.core.logging import get_logger
from api.schemas.college import (
    CollegeDetailResponse,
    CollegeListItem,
    CollegeProfileResponse,
    CollegeProfileUpdate,
)
from api.services.college_service import (
    get_college_by_id,
    get_college_detail,
    list_all_colleges,
    save_logo,
)
from api.services.college_service import update_profile as update_profile_service

router = APIRouter(prefix="/colleges", tags=["Colleges"])
logger = get_logger(__name__)


@router.get(
    "/me",
    response_model=CollegeProfileResponse,
    summary="Get the logged-in college's own profile",
)
async def get_my_profile(
    user: AuthenticatedUser = Depends(get_current_college),
    db: AsyncSession = Depends(get_db),
) -> CollegeProfileResponse:
    college = await get_college_by_id(db, user.college_id)  # type: ignore[arg-type]
    return CollegeProfileResponse.model_validate(college)


@router.put(
    "/me",
    response_model=CollegeProfileResponse,
    summary="Update the logged-in college's own profile",
)
async def update_my_profile(
    data: CollegeProfileUpdate,
    user: AuthenticatedUser = Depends(get_current_college),
    db: AsyncSession = Depends(get_db),
) -> CollegeProfileResponse:
    college = await update_profile_service(db, user.college_id, data)  # type: ignore[arg-type]
    return CollegeProfileResponse.model_validate(college)


@router.post(
    "/me/logo",
    response_model=CollegeProfileResponse,
    summary="Upload/replace the logged-in college's logo",
)
async def upload_logo(
    file: UploadFile = File(...),
    user: AuthenticatedUser = Depends(get_current_college),
    db: AsyncSession = Depends(get_db),
) -> CollegeProfileResponse:
    content = await file.read()
    college = await save_logo(db, user.college_id, file.filename or "logo.png", content)  # type: ignore[arg-type]
    return CollegeProfileResponse.model_validate(college)


@router.get(
    "",
    response_model=list[CollegeListItem],
    summary="[Admin] List all registered colleges",
)
async def list_colleges(
    _: AuthenticatedUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[CollegeListItem]:
    return await list_all_colleges(db)


@router.get(
    "/{college_id}",
    response_model=CollegeDetailResponse,
    summary="[Admin] Get full details for a college",
)
async def get_college_detail_endpoint(
    college_id: int,
    _: AuthenticatedUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> CollegeDetailResponse:
    return await get_college_detail(db, college_id)
