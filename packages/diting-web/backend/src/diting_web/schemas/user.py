"""User schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class UserBase(BaseModel):
    """User base schema."""

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: Optional[str] = Field(None, description="邮箱（可选）")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")


class UserRegister(BaseModel):
    """User registration schema."""

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: Optional[str] = Field(None, description="邮箱（可选）")
    password: str = Field(..., min_length=8, max_length=100, description="密码")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("密码长度至少为8位")
        if not any(c.isupper() for c in v):
            raise ValueError("密码必须包含至少一个大写字母")
        if not any(c.islower() for c in v):
            raise ValueError("密码必须包含至少一个小写字母")
        if not any(c.isdigit() for c in v):
            raise ValueError("密码必须包含至少一个数字")
        return v


class UserLogin(BaseModel):
    """User login schema."""

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., description="密码")


class UserUpdate(BaseModel):
    """User update schema."""

    full_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)


class UserResponse(UserBase):
    """User response schema."""

    id: UUID
    avatar_url: Optional[str]
    is_active: bool
    is_email_verified: bool
    is_admin: bool  # Changed from is_superuser to match User model
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserWithOrganizations(UserResponse):
    """User response with organizations."""

    organizations: list[dict] = Field(default_factory=list, description="用户所属组织列表")


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token 过期时间（秒）")
    user: UserResponse


class TokenRefreshResponse(BaseModel):
    """Token refresh response schema."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int

