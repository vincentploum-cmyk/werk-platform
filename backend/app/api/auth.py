"""
Auth API routes: login, register, token refresh.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.security import (
    create_access_token,
    verify_password,
    get_password_hash,
    decode_access_token,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "developer"


class UserResponse(BaseModel):
    user_id: str
    username: str
    role: str


# ---------------------------------------------------------------------------
# In-memory user store (dev only — replace with DB in production)
# ---------------------------------------------------------------------------

_dev_users: dict[str, dict[str, Any]] = {
    "admin": {
        "user_id": "usr-admin-001",
        "username": "admin",
        "password": get_password_hash("admin123"),
        "role": "admin",
    },
    "lead": {
        "user_id": "usr-lead-001",
        "username": "lead",
        "password": get_password_hash("lead123"),
        "role": "lead",
    },
    "developer": {
        "user_id": "usr-dev-001",
        "username": "developer",
        "password": get_password_hash("dev123"),
        "role": "developer",
    },
    "viewer": {
        "user_id": "usr-view-001",
        "username": "viewer",
        "password": get_password_hash("view123"),
        "role": "viewer",
    },
}


def _find_user(username: str) -> dict[str, Any] | None:
    """Look up a user by username."""
    for uid, user in _dev_users.items():
        if user["username"] == username:
            return user
    return None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Authenticate a user and return a JWT access token."""
    user = _find_user(request.username)
    if not user or not verify_password(request.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    token = create_access_token(
        data={
            "sub": user["user_id"],
            "username": user["username"],
            "role": user["role"],
        },
    )

    return TokenResponse(
        access_token=token,
        expires_in_minutes=settings.access_token_expire_minutes,
    )


@router.post("/register", response_model=UserResponse)
async def register(request: RegisterRequest):
    """Register a new user (dev only — simple in-memory store)."""
    if _find_user(request.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists.",
        )

    user_id = f"usr-{request.username}-{len(_dev_users) + 1:03d}"
    _dev_users[user_id] = {
        "user_id": user_id,
        "username": request.username,
        "password": get_password_hash(request.password),
        "role": request.role,
    }

    return UserResponse(
        user_id=user_id,
        username=request.username,
        role=request.role,
    )


@router.post("/verify", response_model=UserResponse)
async def verify_token(token: str):
    """Verify a JWT token and return the user info."""
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )

    return UserResponse(
        user_id=str(payload.get("sub", "")),
        username=str(payload.get("username", "")),
        role=str(payload.get("role", "viewer")),
    )