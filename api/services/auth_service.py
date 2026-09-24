from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
from api.core.exceptions import DuplicateEmailError, InvalidCredentialsError
from api.core.logging import get_logger
from api.core.security import create_access_token, hash_password, verify_password
from api.models import College
from api.schemas.auth import CollegeSignupRequest, LoginRequest, TokenResponse

logger = get_logger(__name__)


async def signup_college(
    db: AsyncSession, request: CollegeSignupRequest
) -> TokenResponse:
    """Register a new college account and return a login token for it."""
    normalized_email = request.email.lower()

    if normalized_email == settings.ADMIN_EMAIL.lower():
        raise DuplicateEmailError("This email address is reserved")

    existing_query = select(College).where(
        func.lower(College.email) == normalized_email
    )
    existing = (await db.execute(existing_query)).scalars().first()
    if existing is not None:
        raise DuplicateEmailError("An account with this email already exists")

    college = College(
        email=normalized_email,
        hashed_password=hash_password(request.password),
        college_name=request.college_name,
    )
    db.add(college)
    await db.commit()
    await db.refresh(college)

    logger.info("college_signed_up", college_id=college.id, email=normalized_email)

    token = create_access_token(
        {"role": "college", "email": normalized_email, "college_id": college.id}
    )
    return TokenResponse(
        access_token=token,
        role="college",
        college_id=college.id,
        college_name=college.college_name,
    )


async def login(db: AsyncSession, request: LoginRequest) -> TokenResponse:
    """Authenticate either the fixed platform admin or a college account."""
    normalized_email = request.email.lower()

    if normalized_email == settings.ADMIN_EMAIL.lower():
        import hmac

        is_valid = False
        if settings.ADMIN_PASSWORD.startswith(("$2b$", "$2a$")):
            is_valid = verify_password(request.password, settings.ADMIN_PASSWORD)
        else:
            is_valid = hmac.compare_digest(request.password, settings.ADMIN_PASSWORD)

        if not is_valid:
            raise InvalidCredentialsError("Incorrect email or password")
        logger.info("admin_logged_in", email=normalized_email)
        token = create_access_token({"role": "admin", "email": normalized_email})
        return TokenResponse(access_token=token, role="admin")

    query = select(College).where(func.lower(College.email) == normalized_email)
    college = (await db.execute(query)).scalars().first()

    if college is None or not verify_password(
        request.password, college.hashed_password
    ):
        raise InvalidCredentialsError("Incorrect email or password")

    if not college.is_active:
        raise InvalidCredentialsError("This account has been deactivated")

    logger.info("college_logged_in", college_id=college.id, email=normalized_email)
    token = create_access_token(
        {"role": "college", "email": normalized_email, "college_id": college.id}
    )
    return TokenResponse(
        access_token=token,
        role="college",
        college_id=college.id,
        college_name=college.college_name,
    )
