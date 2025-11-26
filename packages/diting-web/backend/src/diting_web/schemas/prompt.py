"""Prompt schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from diting_web.models.prompt import PromptCategoryEnum


class PromptBase(BaseModel):
    """Prompt base schema."""

    name: str = Field(..., min_length=1, max_length=200, description="提示词名称")
    description: Optional[str] = Field(None, description="提示词描述")
    category: PromptCategoryEnum = Field(..., description="提示词分类")
    content: str = Field(..., min_length=1, description="提示词内容")
    variables: List[str] = Field(default_factory=list, description="提示词变量列表")
    version: str = Field(default="v1.0", max_length=20, description="版本号")
    is_favorite: bool = Field(default=False, description="是否收藏")


class PromptCreate(BaseModel):
    """Prompt create schema."""

    name: str = Field(..., min_length=1, max_length=200, description="提示词名称")
    description: Optional[str] = Field(None, description="提示词描述")
    category: PromptCategoryEnum = Field(..., description="提示词分类")
    content: str = Field(..., min_length=1, description="提示词内容")
    variables: Optional[List[str]] = Field(default_factory=list, description="提示词变量列表")
    version: Optional[str] = Field(default="v1.0", max_length=20, description="版本号")
    is_favorite: Optional[bool] = Field(default=False, description="是否收藏")


class PromptUpdate(BaseModel):
    """Prompt update schema."""

    name: Optional[str] = Field(None, min_length=1, max_length=200, description="提示词名称")
    description: Optional[str] = Field(None, description="提示词描述")
    category: Optional[PromptCategoryEnum] = Field(None, description="提示词分类")
    content: Optional[str] = Field(None, min_length=1, description="提示词内容")
    variables: Optional[List[str]] = Field(None, description="提示词变量列表")
    version: Optional[str] = Field(None, max_length=20, description="版本号")
    is_favorite: Optional[bool] = Field(None, description="是否收藏")


class PromptResponse(BaseModel):
    """Prompt response schema."""

    id: UUID
    name: str
    description: Optional[str]
    category: PromptCategoryEnum
    content: str
    variables: List[str]
    version: str
    is_favorite: bool
    usage_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PromptStatistics(BaseModel):
    """Prompt statistics schema."""

    total_prompts: int = Field(description="总提示词数")
    favorite_count: int = Field(description="收藏数")
    total_usage_count: int = Field(description="总使用次数")
    category_count: int = Field(description="分类数")

