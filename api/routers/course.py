from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.deps import AuthenticatedUser, get_current_college, get_current_user
from api.core.exceptions import NotAuthorizedError
from api.core.logging import get_logger
from api.schemas.course import CourseCreate, CourseResponse, CourseUpdate
from api.services.course_service import (
    create_course,
    delete_course,
    list_courses,
    update_course,
)

router = APIRouter(prefix="/courses", tags=["Courses"])
logger = get_logger(__name__)


@router.get(
    "",
    response_model=list[CourseResponse],
    summary="List courses (own college, or ?college_id= for admins)",
)
async def get_courses(
    college_id: int | None = Query(
        None, description="Required for admin callers; ignored for college callers"
    ),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CourseResponse]:
    if user.role == "college":
        target_college_id = user.college_id
    else:
        if college_id is None:
            raise NotAuthorizedError("college_id query param is required for admins")
        target_college_id = college_id

    courses = await list_courses(db, target_college_id)  # type: ignore[arg-type]
    return [CourseResponse.model_validate(c) for c in courses]


@router.post(
    "",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new course for the logged-in college",
)
async def add_course(
    data: CourseCreate,
    user: AuthenticatedUser = Depends(get_current_college),
    db: AsyncSession = Depends(get_db),
) -> CourseResponse:
    course = await create_course(db, user.college_id, data)  # type: ignore[arg-type]
    return CourseResponse.model_validate(course)


@router.put(
    "/{course_id}",
    response_model=CourseResponse,
    summary="Update a course owned by the logged-in college",
)
async def edit_course(
    course_id: int,
    data: CourseUpdate,
    user: AuthenticatedUser = Depends(get_current_college),
    db: AsyncSession = Depends(get_db),
) -> CourseResponse:
    course = await update_course(db, user.college_id, course_id, data)  # type: ignore[arg-type]
    return CourseResponse.model_validate(course)


@router.delete(
    "/{course_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a course owned by the logged-in college",
)
async def remove_course(
    course_id: int,
    user: AuthenticatedUser = Depends(get_current_college),
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_course(db, user.college_id, course_id)  # type: ignore[arg-type]
