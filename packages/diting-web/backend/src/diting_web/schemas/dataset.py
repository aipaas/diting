"""Dataset schemas."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class DatasetBase(BaseModel):
    """Dataset base schema."""

    name: str = Field(..., min_length=1, max_length=100, description="Dataset name")
    description: Optional[str] = Field(None, description="Dataset description")


class DatasetCreate(DatasetBase):
    """Dataset create schema."""

    pass


class DatasetUpdate(BaseModel):
    """Dataset update schema."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None


class DatasetDataUpdate(BaseModel):
    """Dataset data update schema - for updating preview data."""

    preview_data: list[dict] = Field(..., description="Updated preview data")
    row_count: Optional[int] = Field(None, description="Updated row count")


class DatasetRowUpdate(BaseModel):
    """Dataset single row update schema - for updating a single row."""

    row_index: int = Field(..., ge=0, description="Row index to update (0-based)")
    data: dict = Field(..., description="Updated row data")


class DatasetRowDelete(BaseModel):
    """Dataset single row delete schema - for deleting a single row."""

    row_index: int = Field(..., ge=0, description="Row index to delete (0-based)")


class AnnotationColumnCreate(BaseModel):
    """Annotation column create schema."""

    column_name: str = Field(..., min_length=1, max_length=100, description="Annotation column name")
    column_type: str = Field(default="text", description="Column type: text, number, category, etc.")
    description: Optional[str] = Field(None, description="Column description")
    options: Optional[list[str]] = Field(None, description="Options for category type")


class AnnotationColumnUpdate(BaseModel):
    """Annotation column update schema."""

    old_column_name: str = Field(..., description="Current column name")
    new_column_name: str = Field(..., min_length=1, max_length=100, description="New column name")
    column_type: Optional[str] = Field(None, description="Column type: text, number, category, etc.")
    description: Optional[str] = Field(None, description="Column description")
    options: Optional[list[str]] = Field(None, description="Options for category type")


class AnnotationColumnDelete(BaseModel):
    """Annotation column delete schema."""

    column_name: str = Field(..., description="Annotation column name to delete")


class DatasetResponse(DatasetBase):
    """Dataset response schema (Simplified: user-level)."""

    id: UUID
    # User-level fields
    project_id: Optional[UUID] = Field(None, description="所属项目ID（已简化，保留字段以兼容）")
    created_by: UUID = Field(..., description="创建者ID")
    # Optional relationship data
    creator: Optional[dict] = Field(None, description="创建者信息")
    project: Optional[dict] = Field(None, description="项目信息")
    # File info
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    row_count: int
    columns: Optional[dict] = None
    metadata_: dict = Field(default_factory=dict, alias="metadata")
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }

    @field_validator("metadata_", mode="before")
    @classmethod
    def validate_metadata(cls, v: Any) -> dict:
        """Ensure metadata is always a dict."""
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        # If it's an object, try to convert it to dict
        if hasattr(v, "__dict__"):
            return dict(v.__dict__)
        return {}

    @field_validator("columns", mode="before")
    @classmethod
    def validate_columns(cls, v: Any) -> Optional[dict]:
        """Ensure columns is always a dict or None."""
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        # If it's an object, try to convert it to dict
        if hasattr(v, "__dict__"):
            return dict(v.__dict__)
        return None

