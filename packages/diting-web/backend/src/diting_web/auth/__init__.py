"""Authentication and authorization module."""

from .dependencies import (
    get_current_active_user,
    get_current_user,
    get_user_from_refresh_token,
    require_admin,
    require_auth,
    security,
)
from .security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    get_password_hash,
    verify_password,
)

__all__ = [
    # Dependencies
    "get_current_active_user",
    "get_current_user",
    "get_user_from_refresh_token",
    "require_admin",
    "require_auth",
    "security",
    # Security
    "create_access_token",
    "create_refresh_token",
    "decode_access_token",
    "decode_refresh_token",
    "get_password_hash",
    "verify_password",
]

