from enum import StrEnum
from uuid import uuid4
from pydantic import BaseModel, Field
from typing import Optional


class ModelType(StrEnum):
    INFERENCE = "inference"
    EMBEDDING = "embedding"
    EVALUATION = "evaluation"


class ModelManagementData(BaseModel):
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for the model",
    )
    model_type: ModelType = Field(
        ..., description="Type of the model (e.g., inference, embedding, evaluation)"
    )
    model_name: str = Field(..., description="Name of the model")
    access_endpoint: str = Field(
        ..., description="API endpoint for accessing the model"
    )
    api_key: str = Field(..., description="API key for authentication")
    notes: Optional[str] = Field(None, description="Additional notes about the model")
    is_default: bool = Field(
        False, description="Indicates if this model is the default model for its type"
    )
