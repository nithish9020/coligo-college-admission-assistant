from pydantic import BaseModel, EmailStr, Field, field_validator


class CollegeSignupRequest(BaseModel):
    college_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)

    @field_validator("college_name")
    @classmethod
    def strip_college_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("College name cannot be empty")
        return cleaned


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str  # "admin" or "college"
    college_id: int | None = None
    college_name: str | None = None


class CurrentUserResponse(BaseModel):
    role: str
    email: str
    college_id: int | None = None
    college_name: str | None = None


class WhatsAppOtpSendRequest(BaseModel):
    phone: str = Field(
        ..., min_length=10, max_length=20, description="WhatsApp mobile number"
    )


class WhatsAppOtpSendResponse(BaseModel):
    status: str
    message: str
    phone: str
    expires_in: int


class WhatsAppOtpVerifyRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=20)
    code: str = Field(..., min_length=4, max_length=8)


class WhatsAppOtpVerifyResponse(BaseModel):
    status: str
    verified: bool
    session_key: str
    phone: str
    cutoff: float | None = None
    community: str | None = None
    district: str | None = None
