"""Task schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from diting_web.models.task import TaskStatus, TaskType


class ModelConfig(BaseModel):
    """Model configuration schema."""

    name: str = Field(..., description="Model name")
    api_key: Optional[str] = Field(None, description="API key")
    base_url: Optional[str] = Field(None, description="Base URL")
    parameters: dict = Field(default_factory=dict, description="Model parameters")
    timeout: int = Field(default=300, description="Request timeout in seconds")


class MetricConfig(BaseModel):
    """Metric configuration schema."""

    metric_name: str = Field(..., description="Metric name")
    metric_type: str = Field(..., description="Metric type: builtin_metric or custom_metric")
    prompt: Optional[str] = Field(None, description="Custom prompt template")


class EvalCase(BaseModel):
    """Evaluation case schema."""

    user_input: Optional[str] = Field(None, description="User input")
    actual_output: Optional[str] = Field(None, description="Actual output")
    expected_output: Optional[str] = Field(None, description="Expected output")
    context: Optional[list[str]] = Field(None, description="Context list")
    retrieval_context: Optional[list[str]] = Field(None, description="Retrieval context list")
    metadata: dict = Field(default_factory=dict, description="Metadata")


class CreateEvaluationTaskRequest(BaseModel):
    """Create evaluation task request schema."""

    evaluator_id: UUID = Field(..., description="Evaluator ID (required)")
    llm_config: Optional[ModelConfig] = Field(None, description="LLM configuration")
    embedding_config: Optional[ModelConfig] = Field(None, description="Embedding configuration")
    eval_case: EvalCase = Field(..., description="Evaluation case")


class SynthesizerConfig(BaseModel):
    """Synthesizer configuration schema."""

    synthesizer_name: str = Field(..., description="Synthesizer name")
    config: dict = Field(default_factory=dict, description="Synthesizer configuration")


class InputData(BaseModel):
    """Input data schema - supports three modes: manual, dataset, file."""

    # Mode 1: Manual input (direct context/themes)
    context: Optional[list[str]] = Field(None, description="Context list (manual input)")
    themes: Optional[list[str]] = Field(None, description="Themes list (manual input)")
    
    # Mode 2: Dataset import (reference existing dataset)
    dataset_id: Optional[UUID] = Field(None, description="Dataset ID (dataset import mode)")
    context_field: Optional[str] = Field(None, description="Field name for context in dataset")
    theme_field: Optional[str] = Field(None, description="Field name for theme in dataset")
    
    # Mode 3: File upload (temporary file parsing)
    file_content: Optional[str] = Field(None, description="Base64 encoded file content (file upload mode)")
    file_name: Optional[str] = Field(None, description="Original file name")
    file_type: Optional[str] = Field(None, description="File type (csv/jsonl/xlsx)")
    file_context_field: Optional[str] = Field(None, description="Field name for context in uploaded file")
    file_theme_field: Optional[str] = Field(None, description="Field name for theme in uploaded file")


class CreateSynthesisTaskRequest(BaseModel):
    """Create synthesis task request schema."""

    llm_config: Optional[ModelConfig] = Field(
        None, description="LLM configuration (optional, fallback to default if omitted)"
    )
    embedding_config: Optional[ModelConfig] = Field(None, description="Embedding configuration")
    synthesizer_config: SynthesizerConfig = Field(..., description="Synthesizer configuration")
    input_data: InputData = Field(..., description="Input data")
    metadata: dict = Field(default_factory=dict, description="Metadata")


class CreateBatchEvaluationTaskRequest(BaseModel):
    """Create batch evaluation task request schema."""

    name: Optional[str] = Field(None, description="Task name (optional, auto-generated if not provided)")
    dataset_id: UUID = Field(..., description="Dataset ID")
    evaluator_id: UUID = Field(..., description="Evaluator ID")
    llm_config: Optional[ModelConfig] = Field(None, description="LLM configuration")
    embedding_config: Optional[ModelConfig] = Field(None, description="Embedding configuration")



class NegativeMiningInputData(BaseModel):
    """Negative mining input data schema."""

    # Mode 1: Manual train_data input
    train_data: Optional[list[dict]] = Field(None, description="Training data: list of {query, pos: [], neg: []}")
    candidate_pool: Optional[list[str]] = Field(None, description="Optional candidate pool for mining")
    
    # Mode 2: Dataset import with field mapping
    dataset_id: Optional[str] = Field(None, description="Dataset ID to load training data from")
    query_field: Optional[str] = Field(None, description="Field name for query in dataset")
    pos_field: Optional[str] = Field(None, description="Field name for positive samples in dataset")
    neg_field: Optional[str] = Field(None, description="Field name for negative samples in dataset (optional)")


class CreateNegativeMiningTaskRequest(BaseModel):
    """Create negative mining task request schema."""

    embedding_config: ModelConfig = Field(..., description="Embedding model configuration")
    input_data: NegativeMiningInputData = Field(..., description="Input training data")
    sample_range: str = Field(default="10-210", description="Sample range for negative mining (e.g., '10-210')")
    negative_number: int = Field(default=15, ge=1, le=1000, description="Number of negative samples per query")
    use_gpu: bool = Field(default=False, description="Whether to use GPU for FAISS indexing")
    embedding_batch_size: int = Field(default=32, ge=1, le=256, description="Batch size for embedding encoding")
    metadata: dict = Field(default_factory=dict, description="Metadata")


class TaskResponse(BaseModel):
    """Task response schema."""

    id: UUID
    name: Optional[str] = None
    task_type: TaskType
    status: TaskStatus
    progress: Decimal
    dataset_id: Optional[UUID] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[dict] = None
    error: Optional[str] = None
    total_tokens: int
    total_cost: Decimal
    config: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskCreateResponse(BaseModel):
    """Task create response schema."""

    task_id: UUID = Field(..., description="Task ID")
    status: TaskStatus = Field(..., description="Task status")
    created_at: datetime = Field(..., description="Task creation time")
    estimated_time: Optional[int] = Field(None, description="Estimated execution time in seconds")


class EvaluationResultResponse(BaseModel):
    """Evaluation result response schema."""

    id: UUID
    task_id: UUID
    metric_name: str
    score: Optional[Decimal] = None
    reason: Optional[str] = None
    user_input: Optional[str] = None
    actual_output: Optional[str] = None
    expected_output: Optional[str] = None
    context: Optional[list[str]] = None
    retrieval_context: Optional[list[str]] = None
    usages: Optional[list[dict]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SynthesisResultResponse(BaseModel):
    """Synthesis result response schema."""

    id: UUID
    task_id: UUID
    question: str
    answer: str
    source_context: Optional[list[str]] = None
    quality_score: Optional[Decimal] = None
    usages: Optional[list[dict]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateDatasetFromSynthesisRequest(BaseModel):
    """Create dataset from synthesis results request schema."""

    name: str = Field(..., description="Dataset name")
    description: Optional[str] = Field(None, description="Dataset description")


class DashboardStatisticsResponse(BaseModel):
    """Dashboard statistics response schema."""

    total_tasks: int = Field(..., description="Total number of tasks")
    completed_tasks: int = Field(..., description="Number of completed tasks")
    failed_tasks: int = Field(..., description="Number of failed tasks")
    success_rate: float = Field(..., description="Success rate (0.0 - 1.0)")
    total_tokens: int = Field(default=0, description="Total tokens used")
    total_cost: Decimal = Field(default=Decimal("0.00"), description="Total cost")
    recent_tasks: list[TaskResponse] = Field(default_factory=list, description="Recent tasks")

