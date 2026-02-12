#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, Dict, Any
from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class BaseSchema(BaseModel):
    """统一配置的基类：支持别名(camelCase)，允许 orm_mode"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",  # 默认禁止多余字段，防止 API 滥用
        from_attributes=True,
    )


class SchemaBase(BaseModel):
    model_config = ConfigDict(use_enum_values=True)


class StatusEnum(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"


class ModelConfig(BaseSchema):
    name: str = Field(..., description="模型名称")
    base_url: Optional[str] = Field(None, description="模型API基础URL")
    api_key: Optional[str] = Field(None, description="API密钥")
    parameters: Optional[Dict[str, Any]] = Field(None, description="模型参数")
    timeout: Optional[float] = Field(600, description="超时时间(秒)")
