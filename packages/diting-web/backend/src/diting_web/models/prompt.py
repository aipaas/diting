"""Prompt repository model (提示词仓库) - Simplified."""

import enum
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from diting_web.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from diting_web.models.user import User


class PromptCategoryEnum(str, enum.Enum):
    """Prompt category enum (提示词分类)."""

    SYSTEM = "系统"          # 系统提示词
    EVALUATION = "评估"      # 评估提示词
    SYNTHESIS = "合成"       # 合成提示词
    OPTIMIZATION = "优化"    # 优化提示词
    CUSTOM = "自定义"        # 自定义提示词


class Prompt(Base, UUIDMixin, TimestampMixin):
    """Prompt repository model (提示词仓库)."""

    __tablename__ = "prompts"

    # 基本信息
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True, comment="提示词名称")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="提示词描述")
    category: Mapped[PromptCategoryEnum] = mapped_column(
        Enum(PromptCategoryEnum),
        nullable=False,
        index=True,
        comment="提示词分类",
    )
    
    # User relationship
    created_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="创建者ID（系统内置为NULL）",
    )
    
    # 内容
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="提示词内容")
    variables: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="提示词变量列表",
    )
    
    # 版本信息
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1.0", comment="版本号")
    
    # 收藏和使用统计
    is_favorite: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="是否收藏",
    )
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="使用次数统计")

    # Relationships
    creator: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by],
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<Prompt(id={self.id}, name={self.name}, category={self.category}, version={self.version})>"

