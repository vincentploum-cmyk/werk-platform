"""
Security module: JWT authentication, password hashing, and token management.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional, List

from jose import JWTError, jwt
import bcrypt

from app.core.config import settings

# ---------------------------------------------------------------------------
# Password utilities (bcrypt direct — avoids passlib compat issues)
# ---------------------------------------------------------------------------


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


# ---------------------------------------------------------------------------
# JWT token utilities
# ---------------------------------------------------------------------------


def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token with an expiration claim."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    """Decode and validate a JWT access token. Returns the payload or None."""
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# Role definitions
# ---------------------------------------------------------------------------

ROLE_HIERARCHY: dict[str, int] = {
    "admin": 100,
    "lead": 80,
    "developer": 60,
    "viewer": 40,
    "agent": 20,
}


def role_has_access(user_role: str, required_role: str) -> bool:
    """Check if a user's role level meets the required access level."""
    user_level = ROLE_HIERARCHY.get(user_role, 0)
    required_level = ROLE_HIERARCHY.get(required_role, 0)
    return user_level >= required_level


# ---------------------------------------------------------------------------
# Built-in RBAC policies
# ---------------------------------------------------------------------------

RBAC_POLICIES: dict[str, List[str]] = {
    "admin": [
        "projects:create", "projects:read", "projects:update", "projects:delete",
        "agents:create", "agents:read", "agents:update", "agents:delete",
        "tasks:create", "tasks:read", "tasks:update", "tasks:delete",
        "artifacts:create", "artifacts:read", "artifacts:delete",
        "users:manage", "settings:manage", "deploy:trigger",
    ],
    "lead": [
        "projects:create", "projects:read", "projects:update",
        "agents:read",
        "tasks:create", "tasks:read", "tasks:update",
        "artifacts:create", "artifacts:read",
        "deploy:trigger",
    ],
    "developer": [
        "projects:read",
        "agents:read",
        "tasks:read", "tasks:update",
        "artifacts:create", "artifacts:read",
    ],
    "viewer": [
        "projects:read",
        "agents:read",
        "tasks:read",
        "artifacts:read",
    ],
    "agent": [
        "tasks:read", "tasks:update",
        "artifacts:create", "artifacts:read",
    ],
}


def check_permission(user_role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    allowed = RBAC_POLICIES.get(user_role, [])
    return permission in allowed


def get_role_permissions(role: str) -> list[str]:
    """Get all permissions for a given role."""
    return RBAC_POLICIES.get(role, [])