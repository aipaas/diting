"""Admin user schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AdminUserBase(BaseModel):
    """Admin user base schema."""

    username: str = Field(..., min_length=3, max_length=50, description="Username")


class AdminUserLogin(BaseModel):
    """Admin user login schema."""

    username: str = Field(..., description="Username (fixed: admin)")
    password: str = Field(..., min_length=6, description="Password")


class AdminUserResponse(AdminUserBase):
    """Admin user response schema."""

    id: UUID
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")

