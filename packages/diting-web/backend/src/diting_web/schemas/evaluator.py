"""Evaluator schemas."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ModelConfig(BaseModel):
    """Model configuration for a metric."""
    
    name: str = Field(..., description="Model name (e.g., gpt-4, gpt-3.5-turbo)")
    api_key: Optional[str] = Field(None, description="API key for the model")
    base_url: Optional[str] = Field(None, description="Base URL for the model API")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Model parameters (e.g., temperature)")
    timeout: int = Field(default=300, description="Request timeout in seconds")


class MetricModelConfig(BaseModel):
    """Model configuration for a specific metric."""
    
    metric_id: UUID = Field(..., description="Metric ID")
    llm_config: Optional[ModelConfig] = Field(None, description="LLM configuration for this metric")
    embedding_config: Optional[ModelConfig] = Field(None, description="Embedding configuration for this metric")


class EvaluatorConfig(BaseModel):
    """Evaluator configuration structure."""
    
    metric_model_configs: list[MetricModelConfig] = Field(
        default_factory=list,
        description="Model configurations for each metric"
    )
    default_llm_config: Optional[ModelConfig] = Field(
        None,
        description="Default LLM config for metrics without specific configuration"
    )
    default_embedding_config: Optional[ModelConfig] = Field(
        None,
        description="Default embedding config for metrics without specific configuration"
    )


class EvaluatorBase(BaseModel):
    """Evaluator base schema."""

    name: str = Field(..., min_length=1, max_length=100, description="Evaluator name")
    description: Optional[str] = Field(None, description="Evaluator description")
    metric_ids: list[UUID] = Field(..., min_length=1, description="List of metric IDs")
    config: EvaluatorConfig = Field(
        default_factory=EvaluatorConfig,
        description="Evaluator configuration with per-metric model settings"
    )
    
    @field_validator("config", mode="before")
    @classmethod
    def parse_config(cls, v: Any) -> EvaluatorConfig:
        """Parse config from dict or EvaluatorConfig."""
        if isinstance(v, dict):
            return EvaluatorConfig(**v)
        return v


class EvaluatorCreate(EvaluatorBase):
    """Evaluator create schema."""

    pass


class EvaluatorUpdate(BaseModel):
    """Evaluator update schema."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    metric_ids: Optional[list[UUID]] = Field(None, min_length=1)
    config: Optional[EvaluatorConfig] = None
    
    @field_validator("config", mode="before")
    @classmethod
    def parse_config(cls, v: Any) -> Optional[EvaluatorConfig]:
        """Parse config from dict or EvaluatorConfig."""
        if v is None:
            return None
        if isinstance(v, dict):
            return EvaluatorConfig(**v)
        return v


class EvaluatorResponse(EvaluatorBase):
    """Evaluator response schema."""

    id: UUID
    created_by: UUID
    created_by_username: Optional[str] = Field(None, description="创建人用户名")
    usage_count: int
    last_used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

