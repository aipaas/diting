"""Task models - Simplified."""

import enum
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from diting_web.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from diting_web.models.dataset import Dataset
    from diting_web.models.user import User


class TaskType(str, enum.Enum):
    """Task type enum."""

    EVALUATION = "evaluation"
    SYNTHESIS = "synthesis"
    BATCH_EVALUATION = "batch_evaluation"
    NEGATIVE_MINING = "negative_mining"


class TaskStatus(str, enum.Enum):
    """Task status enum."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(Base, UUIDMixin, TimestampMixin):
    """Task model (user-level isolation)."""

    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("progress >= 0 AND progress <= 100", name="chk_progress"),
    )

    # Basic info
    name: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        index=True,
    )
    task_type: Mapped[TaskType] = mapped_column(
        Enum(TaskType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, values_callable=lambda x: [e.value for e in x]),
        default=TaskStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Relations
    dataset_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="创建者ID",
    )

    # Task configuration
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    input_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Execution info
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    job_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    worker_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Results
    result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Statistics
    progress: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        default=Decimal("0.00"),
        nullable=False,
    )

    # Metadata
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    # Relationships
    dataset: Mapped[Optional["Dataset"]] = relationship("Dataset", back_populates="tasks")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    evaluation_results: Mapped[list["EvaluationResult"]] = relationship(
        "EvaluationResult",
        back_populates="task",
        cascade="all, delete-orphan",
    )
    synthesis_results: Mapped[list["SynthesisResult"]] = relationship(
        "SynthesisResult",
        back_populates="task",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<Task(id={self.id}, type={self.task_type}, status={self.status}, created_by={self.created_by})>"


class EvaluationResult(Base, UUIDMixin):
    """Evaluation result model."""

    __tablename__ = "evaluation_results"

    task_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Evaluation info
    metric_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4), nullable=True, index=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Input data
    user_input: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actual_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    context: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    retrieval_context: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Execution details
    run_logs: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    usages: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Metadata
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="evaluation_results")

    def __repr__(self) -> str:
        """String representation."""
        return f"<EvaluationResult(id={self.id}, metric={self.metric_name}, score={self.score})>"


class SynthesisResult(Base, UUIDMixin):
    """Synthesis result model."""

    __tablename__ = "synthesis_results"

    task_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Synthesis data
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)

    # Input context
    source_context: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Quality score
    quality_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4), nullable=True, index=True)

    # Execution details
    usages: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Metadata
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="synthesis_results")

    def __repr__(self) -> str:
        """String representation."""
        return f"<SynthesisResult(id={self.id}, question={self.question[:50]})>"

