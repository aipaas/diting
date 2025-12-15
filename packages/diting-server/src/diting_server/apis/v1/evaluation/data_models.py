#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pydantic import Field
from enum import Enum
from typing import Optional, Dict, Any, List
from diting_server.common.schema import Usage, StatusEnum, BaseSchema, ModelConfig


class EvalMetricTypeEnum(str, Enum):
    Custom = "custom_metric"
    Builtin = "builtin_metric"


class MetricConfig(BaseSchema):
    metric_name: str = Field(..., description="指标名称")
    prompt: Optional[str] = Field("", description="评估提示词")
    metric_type: EvalMetricTypeEnum = Field(
        EvalMetricTypeEnum.Builtin, description="指标类型"
    )


class MetricDefinition(BaseSchema):
    """Complete metric configuration"""

    name: str = Field(..., description="Unique identifier for the metric")
    description: str = Field(
        ..., description="Human-readable description of what the metric measures"
    )
    require_user_input: bool = Field(False, description="Is required input")
    require_actual_output: bool = Field(False, description="Is required actual_output")
    require_expected_output: bool = Field(
        False, description="Is required expected_output"
    )
    require_context: bool = Field(False, description="Is required context")
    require_retrieval_context: bool = Field(
        False, description="Is required retrieval_context"
    )


class EvalCase(BaseSchema):
    user_input: Optional[str] = Field(None, description="用户输入")
    actual_output: Optional[str] = Field(None, description="实际输出")
    expected_output: Optional[str] = Field(None, description="期望输出")
    context: Optional[List[str]] = Field(None, description="上下文")
    retrieval_context: Optional[List[str]] = Field(None, description="检索上下文")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class EvaluationRequest(BaseSchema):
    llm_config: Optional[ModelConfig] = Field(None, description="llm模型配置")
    embedding_config: Optional[ModelConfig] = Field(
        None, description="embedding模型配置"
    )
    metric_config: MetricConfig = Field(..., description="指标配置")
    eval_case: EvalCase = Field(..., description="输入数据")


class EvaluationResult(BaseSchema):
    metric_name: str = Field(..., description="指标名称")
    score: float = Field(..., description="评估分数", ge=0.0, le=1.0)
    reason: Optional[str] = Field(None, description="详细说明")
    run_logs: Optional[Dict[str, Any]] = Field(None, description="运行日志")


class RerankEvalCase(BaseSchema):
    """Rerank评估案例"""

    q: str = Field(..., description="查询问题")
    retrieval_reference_list: List[dict] = Field(
        ..., description="检索参考文档ID列表(仅retrieval)"
    )
    expected_dataid: List[str] = Field(..., description="期望的数据ID列表")


class RerankMetricConfig(BaseSchema):
    metric_name: str = Field("rerank_metric", description="指标名称")
    k_values: Optional[List[int]] = Field(
        default_factory=lambda: [5, 10, 15],
        description="评估的top-k值列表，系统将根据k值自动生成对应的评估列名",
    )
    prefixes: Optional[List[str]] = Field(
        default_factory=lambda: ["rerank"],
        description="评估列名前缀列表，用于生成如 '{prefix}_top{k}' 的列名，支持多个前缀",
    )

    def get_columns_to_evaluate(self) -> List[str]:
        """
        根据k值和前缀列表动态生成要评估的列名列表

        Returns:
            List[str]: 生成的列名列表，如 ['rerank_top5', 'rerank_top10', 'rerank_top15', 'embedding_top5', ...]
        """
        columns = []
        for prefix in self.prefixes:
            for k in self.k_values:
                columns.append(f"{prefix}_top{k}")
        return columns

    model_config = {
        "json_schema_extra": {
            "example": {
                "metric_name": "rerank_metric",
                "k_values": [5, 10, 15],
                "prefixes": ["rerank", "embedding"],
            }
        }
    }


class RerankEvaluationRequest(BaseSchema):
    """Rerank数据集评估请求"""

    dataset: List[RerankEvalCase] = Field(..., description="评估数据集")
    reranker_config: ModelConfig = Field(..., description="reranker模型配置")
    metric_config: RerankMetricConfig = Field(..., description="指标配置")


class EvaluationResponse(BaseSchema):
    request_id: str = Field(..., description="请求唯一标识符")
    status: StatusEnum = Field(..., description="评估状态")
    data: Optional[EvaluationResult] = Field(None, description="评估结果")
    usages: Optional[List[Usage]] = Field(None, description="token使用情况")
    error: Optional[str] = Field(None, description="错误信息")
