from dataclasses import dataclass

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.core.exceptions import NotAuthenticatedError, NotAuthorizedError
from api.core.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthenticatedUser:
    role: str  # "admin" or "college"
    email: str
    college_id: int | None = None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedUser:
    """Decode the bearer token and return the authenticated principal.

    Raises NotAuthenticatedError if the token is missing, malformed, or expired —
    handled globally in main.py and mapped to HTTP 401.
    """
    if credentials is None:
        raise NotAuthenticatedError("Missing authentication token")

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise NotAuthenticatedError("Invalid or expired authentication token")

    role = payload.get("role")
    email = payload.get("email")
    if role not in {"admin", "college"} or not email:
        raise NotAuthenticatedError("Malformed authentication token")

    return AuthenticatedUser(
        role=role, email=email, college_id=payload.get("college_id")
    )


async def get_current_college(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Require the caller to be an authenticated college account."""
    if user.role != "college" or user.college_id is None:
        raise NotAuthorizedError("This action requires a college account")
    return user


async def get_current_admin(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Require the caller to be the platform admin."""
    if user.role != "admin":
        raise NotAuthorizedError("This action requires an admin account")
    return user
