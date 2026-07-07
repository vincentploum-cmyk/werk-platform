"""
Auth middleware: FastAPI dependency injection for JWT authentication and RBAC.
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.security import (
    decode_access_token,
    check_permission,
    role_has_access,
)

# HTTP Bearer token scheme (auto-extracts from Authorization header)
bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Current user extraction
# ---------------------------------------------------------------------------


class CurrentUser:
    """Represents the authenticated user extracted from a JWT."""

    def __init__(
        self,
        user_id: str,
        username: str,
        role: str,
        token: str,
    ):
        self.user_id = user_id
        self.username = username
        self.role = role
        self.token = token

    def has_permission(self, permission: str) -> bool:
        return check_permission(self.role, permission)

    def has_role_level(self, required_role: str) -> bool:
        return role_has_access(self.role, required_role)

    def __repr__(self) -> str:
        return f"CurrentUser(id={self.user_id}, role={self.role})"


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> CurrentUser:
    """
    FastAPI dependency: extract and validate the current user from the JWT token.

    Returns a CurrentUser object with user_id, username, role, and token.
    Raises 401 if the token is missing or invalid.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    username = payload.get("username", "unknown")
    role = payload.get("role", "viewer")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing 'sub' (user ID).",
        )

    return CurrentUser(
        user_id=str(user_id),
        username=str(username),
        role=str(role),
        token=token,
    )


# ---------------------------------------------------------------------------
# RBAC permission guard
# ---------------------------------------------------------------------------


class RequirePermission:
    """
    FastAPI dependency factory: requires a specific permission.

    Usage:
        @router.get("/projects")
        async def list_projects(
            user: CurrentUser = Depends(RequirePermission("projects:read")),
        ):
            ...
    """

    def __init__(self, permission: str):
        self.permission = permission

    async def __call__(self, user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not user.has_permission(self.permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: '{self.permission}' is required.",
            )
        return user


class RequireRole:
    """
    FastAPI dependency factory: requires a minimum role level.

    Usage:
        @router.post("/deploy")
        async def deploy(
            user: CurrentUser = Depends(RequireRole("lead")),
        ):
            ...
    """

    def __init__(self, required_role: str):
        self.required_role = required_role

    async def __call__(self, user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not user.has_role_level(self.required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: minimum role '{self.required_role}' is required.",
            )
        return user


# ---------------------------------------------------------------------------
# Optional auth (for endpoints that work with or without auth)
# ---------------------------------------------------------------------------


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[CurrentUser]:
    """
    FastAPI dependency: like get_current_user but returns None if no token provided.
    Useful for endpoints that work in both authenticated and anonymous modes.
    """
    if not credentials:
        return None

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        return None

    user_id = payload.get("sub")
    return CurrentUser(
        user_id=str(user_id) if user_id else "anonymous",
        username=str(payload.get("username", "anonymous")),
        role=str(payload.get("role", "viewer")),
        token=token,
    )