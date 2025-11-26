"""Metric model (评估维度) - Simplified."""

import enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from diting_web.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from diting_web.models.user import User


class MetricTypeEnum(str, enum.Enum):
    """Metric type enum."""

    BUILTIN = "builtin"  # 系统内置维度
    CUSTOM = "custom"    # 用户自定义维度


class Metric(Base, UUIDMixin, TimestampMixin):
    """Metric model (supports global system metrics + user custom metrics)."""

    __tablename__ = "metrics"
    __table_args__ = (
        # 系统内置维度: is_global=true, created_by=NULL
        # 用户自定义维度: is_global=false, created_by IS NOT NULL
        CheckConstraint(
            "(is_global = TRUE AND created_by IS NULL) OR "
            "(is_global = FALSE AND created_by IS NOT NULL)",
            name="check_metric_global",
        ),
    )

    # 基本信息
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="指标名称")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="描述")
    type: Mapped[MetricTypeEnum] = mapped_column(
        Enum(MetricTypeEnum, values_callable=lambda x: [e.value for e in x]),
        default=MetricTypeEnum.CUSTOM,
        nullable=False,
        index=True,
        comment="指标类型",
    )
    is_global: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="是否为系统内置维度（true=系统内置，false=用户自定义）",
    )
    prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="提示词")
    
    # User relationship (NULL for system builtin metrics)
    created_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="创建者ID（系统内置维度为NULL）",
    )
    
    # 必需项配置
    user_input_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否需要用户输入")
    actual_output_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否需要实际输出")
    expected_output_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否需要期望输出")
    context_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否需要上下文")
    retrieval_context_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否需要检索上下文")
    
    # 模型依赖
    embedding_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否需要嵌入模型")
    llm_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否需要大语言模型")

    # Relationships
    creator: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by],
    )

    def __repr__(self) -> str:
        """String representation."""
        type_str = "global" if self.is_global else "custom"
        return f"<Metric(id={self.id}, name={self.name}, is_global={type_str})>"

