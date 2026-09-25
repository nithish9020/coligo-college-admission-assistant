from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.deps import AuthenticatedUser, get_current_user
from api.core.logging import get_logger
from api.schemas.auth import (
    CollegeSignupRequest,
    CurrentUserResponse,
    LoginRequest,
    TokenResponse,
    WhatsAppOtpSendRequest,
    WhatsAppOtpSendResponse,
    WhatsAppOtpVerifyRequest,
    WhatsAppOtpVerifyResponse,
)
from api.services.auth_service import login as login_service
from api.services.auth_service import signup_college
from api.services.otp_service import (
    normalize_phone,
    send_whatsapp_otp,
    verify_whatsapp_otp,
)
from api.services.student_profile_service import get_student_profile

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


@router.post(
    "/otp/send",
    response_model=WhatsAppOtpSendResponse,
    summary="Send login OTP code to student's WhatsApp number",
)
async def send_otp_endpoint(
    request: WhatsAppOtpSendRequest,
) -> WhatsAppOtpSendResponse:
    success, msg, expires_in = await send_whatsapp_otp(request.phone)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )
    return WhatsAppOtpSendResponse(
        status="success",
        message=msg,
        phone=normalize_phone(request.phone),
        expires_in=expires_in,
    )


@router.post(
    "/otp/verify",
    response_model=WhatsAppOtpVerifyResponse,
    summary="Verify WhatsApp OTP code and retrieve student session",
)
async def verify_otp_endpoint(
    request: WhatsAppOtpVerifyRequest,
) -> WhatsAppOtpVerifyResponse:
    verified, msg = verify_whatsapp_otp(request.phone, request.code)
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=msg,
        )

    norm_phone = normalize_phone(request.phone)
    session_key = f"whatsapp:{norm_phone}"
    profile = get_student_profile(session_key)

    return WhatsAppOtpVerifyResponse(
        status="verified",
        verified=True,
        session_key=session_key,
        phone=norm_phone,
        cutoff=profile.calculated_cutoff,
        community=profile.community,
        district=profile.preferred_district,
    )
