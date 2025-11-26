"""Admin user model (Single Admin Mode)."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from diting_web.db.base import Base, TimestampMixin, UUIDMixin


class AdminUser(Base, UUIDMixin, TimestampMixin):
    """Admin user model (Single Admin Mode)."""

    __tablename__ = "admin_users"

    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        """String representation."""
        return f"<AdminUser(id={self.id}, username={self.username})>"

