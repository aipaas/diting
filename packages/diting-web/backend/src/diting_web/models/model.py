"""Model management model (模型管理) - Simplified."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional
from uuid import UUID

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from diting_web.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from diting_web.models.user import User


class ModelTypeEnum(str, enum.Enum):
    """Model type enum (模型类型)."""

    LLM = "llm"           # 大语言模型
    EMBEDDING = "embedding"   # 嵌入模型


class Model(Base, UUIDMixin, TimestampMixin):
    """Model management model (user-level isolation)."""

    __tablename__ = "models"

    # 基本信息
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="模型显示名称")
    model_type: Mapped[ModelTypeEnum] = mapped_column(
        Enum(ModelTypeEnum),
        nullable=False,
        index=True,
        comment="模型类型",
    )
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True, comment="提供商")
    model_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="实际调用的模型标识")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="模型描述")
    
    # User relationship
    created_by: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="创建者ID",
    )
    
    # 配置信息
    api_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="API Key")
    base_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="自定义 API 端点")
    parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, 
        nullable=False, 
        default=dict,
        comment="模型参数配置",
    )
    timeout: Mapped[int] = mapped_column(Integer, default=60, nullable=False, comment="超时时间（秒）")
    
    # 默认标记（用户默认）
    is_default: Mapped[bool] = mapped_column(
        Boolean, 
        default=False, 
        nullable=False, 
        index=True, 
        comment="是否为用户该类型的默认模型",
    )
    
    # 使用统计
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="使用次数统计")
    last_used_at: Mapped[Optional[datetime]] = mapped_column(nullable=True, comment="最后使用时间")

    # Relationships
    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by],
    )

    def __repr__(self) -> str:
        """String representation."""
        provider_str = self.provider or "N/A"
        return f"<Model(id={self.id}, name={self.name}, type={self.model_type}, provider={provider_str})>"

    def mask_api_key(self) -> Optional[str]:
        """Mask API key for security (脱敏处理)."""
        if not self.api_key:
            return None
        if len(self.api_key) <= 10:
            return "***"
        return f"{self.api_key[:4]}***{self.api_key[-3:]}"

