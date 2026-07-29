from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.deps import AuthenticatedUser, get_current_user
from api.core.logging import get_logger
from api.schemas.auth import (
    CollegeSignupRequest,
    CurrentUserResponse,
    LoginRequest,
    TokenResponse,
)
from api.services.auth_service import login as login_service
from api.services.auth_service import signup_college

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = get_logger(__name__)


@router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new college account",
)
async def signup(
    request: CollegeSignupRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    return await signup_college(db, request)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in as a college or the platform admin",
)
async def login(
    request: LoginRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    return await login_service(db, request)


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    summary="Get the currently authenticated principal",
)
async def me(
    user: AuthenticatedUser = Depends(get_current_user),
) -> CurrentUserResponse:
    return CurrentUserResponse(
        role=user.role, email=user.email, college_id=user.college_id
    )
