"""Metric schemas."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from diting_web.models.metric import MetricTypeEnum


class MetricBase(BaseModel):
    """Metric base schema."""

    name: str = Field(..., min_length=1, max_length=100, description="指标名称")
    description: Optional[str] = Field(None, description="描述")
    type: MetricTypeEnum = Field(default=MetricTypeEnum.CUSTOM, description="指标类型")
    prompt: Optional[str] = Field(None, description="提示词")
    
    # 必需项配置
    user_input_required: bool = Field(default=False, description="是否需要用户输入")
    actual_output_required: bool = Field(default=True, description="是否需要实际输出")
    expected_output_required: bool = Field(default=False, description="是否需要期望输出")
    context_required: bool = Field(default=False, description="是否需要上下文")
    retrieval_context_required: bool = Field(default=False, description="是否需要检索上下文")
    
    # 模型依赖
    embedding_required: bool = Field(default=False, description="是否需要嵌入模型")
    llm_required: bool = Field(default=False, description="是否需要大语言模型")


class MetricCreate(BaseModel):
    """Metric create schema - 用户创建自定义维度只需三要素：名称、描述、提示词."""

    name: str = Field(..., min_length=1, max_length=100, description="指标名称")
    description: Optional[str] = Field(None, description="描述")
    prompt: Optional[str] = Field(None, description="提示词")
    
    # type 自动设置为 CUSTOM，不允许用户指定
    # 其他配置字段使用模型默认值


class MetricUpdate(BaseModel):
    """Metric update schema - 用户只能更新三要素：名称、描述、提示词."""

    name: Optional[str] = Field(None, min_length=1, max_length=100, description="指标名称")
    description: Optional[str] = Field(None, description="描述")
    prompt: Optional[str] = Field(None, description="提示词")
    
    # type 和其他配置字段不允许用户修改


class MetricResponse(MetricBase):
    """Metric response schema."""

    id: UUID
    created_by: Optional[UUID] = Field(None, description="创建者ID（系统内置维度为NULL）")
    creator: Optional[dict] = Field(None, description="创建者信息")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("creator", mode="before")
    @classmethod
    def validate_creator(cls, v: Any) -> Optional[dict]:
        """Convert creator relationship object to dict."""
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        # If it's a SQLAlchemy User object, convert to dict
        if hasattr(v, "id") and hasattr(v, "username"):
            return {
                "id": str(v.id),
                "username": v.username,
                "email": getattr(v, "email", ""),
            }
        return None

