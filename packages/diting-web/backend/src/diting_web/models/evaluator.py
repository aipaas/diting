"""Evaluator model (评估器) - Simplified."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY as PGARRAY, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from diting_web.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from diting_web.models.user import User


class Evaluator(Base, UUIDMixin, TimestampMixin):
    """Evaluator model (user-level isolation)."""

    __tablename__ = "evaluators"

    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # User relationship
    created_by: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="创建者ID",
    )
    
    metric_ids: Mapped[list[UUID]] = mapped_column(
        PGARRAY(PGUUID(as_uuid=True)),
        nullable=False,
    )
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # Relationships
    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by],
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<Evaluator(id={self.id}, name={self.name}, created_by={self.created_by})>"

