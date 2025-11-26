"""Dataset model - Simplified."""

from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from diting_web.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from diting_web.models.task import Task
    from diting_web.models.user import User


class Dataset(Base, UUIDMixin, TimestampMixin):
    """Dataset model (user-level isolation)."""

    __tablename__ = "datasets"

    # Basic info
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
    
    # File info
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    file_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    columns: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    # Relationships
    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by],
    )
    tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="dataset",
    )
    rows: Mapped[list["DatasetRow"]] = relationship(
        "DatasetRow",
        back_populates="dataset",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<Dataset(id={self.id}, name={self.name}, created_by={self.created_by})>"


class DatasetRow(Base, UUIDMixin, TimestampMixin):
    """Dataset row model - stores individual data rows."""

    __tablename__ = "dataset_rows"
    __table_args__ = (
        UniqueConstraint("dataset_id", "row_index", name="unique_dataset_row"),
    )

    dataset_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    row_index: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Relationships
    dataset: Mapped["Dataset"] = relationship(
        "Dataset",
        back_populates="rows",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<DatasetRow(id={self.id}, dataset_id={self.dataset_id}, row_index={self.row_index})>"

