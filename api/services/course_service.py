from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.exceptions import NotAuthorizedError, ResourceNotFoundError
from api.core.logging import get_logger
from api.models import Course
from api.schemas.course import CourseCreate, CourseUpdate

logger = get_logger(__name__)


async def list_courses(db: AsyncSession, college_id: int) -> list[Course]:
    query = select(Course).where(Course.college_id == college_id).order_by(Course.id)
    return list((await db.execute(query)).scalars().all())


async def get_course(db: AsyncSession, course_id: int) -> Course:
    course = (
        await db.execute(select(Course).where(Course.id == course_id))
    ).scalars().first()
    if course is None:
        raise ResourceNotFoundError(f"Course with id {course_id} not found")
    return course


async def _get_owned_course(
    db: AsyncSession, course_id: int, college_id: int
) -> Course:
    course = await get_course(db, course_id)
    if course.college_id != college_id:
        raise NotAuthorizedError("You do not have access to this course")
    return course


async def create_course(
    db: AsyncSession, college_id: int, data: CourseCreate
) -> Course:
    course = Course(college_id=college_id, **data.model_dump())
    db.add(course)
    await db.commit()
    await db.refresh(course)
    logger.info("course_created", college_id=college_id, course_id=course.id)
    return course


async def update_course(
    db: AsyncSession, college_id: int, course_id: int, data: CourseUpdate
) -> Course:
    course = await _get_owned_course(db, course_id, college_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(course, field, value)
    await db.commit()
    await db.refresh(course)
    logger.info("course_updated", college_id=college_id, course_id=course_id)
    return course


async def delete_course(db: AsyncSession, college_id: int, course_id: int) -> None:
    course = await _get_owned_course(db, course_id, college_id)
    await db.delete(course)
    await db.commit()
    logger.info("course_deleted", college_id=college_id, course_id=course_id)
