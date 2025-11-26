"""Model schemas."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from diting_web.models.model import ModelTypeEnum


class ModelBase(BaseModel):
    """Model base schema."""

    name: str = Field(..., min_length=1, max_length=100, description="模型显示名称")
    model_type: ModelTypeEnum = Field(..., description="模型类型 (llm/embedding)")
    provider: Optional[str] = Field(None, max_length=50, description="提供商")
    model_name: Optional[str] = Field(None, max_length=100, description="实际调用的模型标识")
    description: Optional[str] = Field(None, description="模型描述")
    api_key: Optional[str] = Field(None, description="API Key")
    base_url: Optional[str] = Field(None, max_length=500, description="自定义 API 端点")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="模型参数配置")
    timeout: int = Field(default=60, ge=1, le=3600, description="超时时间（秒）")
    is_default: bool = Field(default=False, description="是否为默认模型")


class ModelCreate(BaseModel):
    """Model create schema."""

    name: str = Field(..., min_length=1, max_length=100, description="模型显示名称")
    model_type: ModelTypeEnum = Field(..., description="模型类型 (llm/embedding)")
    provider: Optional[str] = Field(None, max_length=50, description="提供商")
    model_name: Optional[str] = Field(None, max_length=100, description="实际调用的模型标识")
    description: Optional[str] = Field(None, description="模型描述")
    api_key: Optional[str] = Field(None, description="API Key")
    base_url: Optional[str] = Field(None, max_length=500, description="自定义 API 端点")
    parameters: Optional[Dict[str, Any]] = Field(None, description="模型参数配置")
    timeout: Optional[int] = Field(default=60, ge=1, le=3600, description="超时时间（秒）")
    is_default: Optional[bool] = Field(default=False, description="是否为默认模型")


class ModelUpdate(BaseModel):
    """Model update schema - model_type 不可修改."""

    name: Optional[str] = Field(None, min_length=1, max_length=100, description="模型显示名称")
    provider: Optional[str] = Field(None, max_length=50, description="提供商")
    model_name: Optional[str] = Field(None, max_length=100, description="实际调用的模型标识")
    description: Optional[str] = Field(None, description="模型描述")
    api_key: Optional[str] = Field(None, description="API Key")
    base_url: Optional[str] = Field(None, max_length=500, description="自定义 API 端点")
    parameters: Optional[Dict[str, Any]] = Field(None, description="模型参数配置")
    timeout: Optional[int] = Field(None, ge=1, le=3600, description="超时时间（秒）")
    is_default: Optional[bool] = Field(None, description="是否为默认模型")


class ModelResponse(BaseModel):
    """Model response schema - API Key 脱敏处理."""

    id: UUID
    name: str
    model_type: ModelTypeEnum
    provider: Optional[str]
    model_name: Optional[str]
    description: Optional[str]
    api_key: Optional[str]  # 会在 Service 层进行脱敏
    base_url: Optional[str]
    parameters: Dict[str, Any]
    timeout: int
    is_default: bool
    usage_count: int
    last_used_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

