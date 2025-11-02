#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from pydantic import Field

from diting_server.common.schema import BaseSchema, StatusEnum


class DatasetItem(BaseSchema):
    id: str = Field(..., description="样本唯一标识")
    user_input: str = Field(..., description="用户输入")
    expected_output: Optional[str] = Field(None, description="期望答案")
    metadata: Optional[Dict[str, Any]] = Field(None, description="样本元数据")


class StageParameterOverrides(BaseSchema):
    similarity_threshold_range: Optional[Tuple[float, float]] = Field(
        None, description="相似度阈值范围 (min, max)"
    )
    similarity_threshold_step: Optional[float] = Field(
        None, description="相似度阈值步长"
    )
    context_recall_tokens_range: Optional[Tuple[int, int]] = Field(
        None, description="上下文召回 token 范围 (min, max)"
    )
    context_recall_tokens_step: Optional[int] = Field(
        None, description="上下文召回 token 步长"
    )


class StageRequest(BaseSchema):
    name: str = Field(..., description="阶段名称，如 retrieval.semantic_search")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="阶段初始参数或固定参数",
    )
    parameters_overrides: StageParameterOverrides = Field(
        default_factory=StageParameterOverrides,
        description="阶段搜索空间覆盖配置",
    )


class MetricSpec(BaseSchema):
    type: str = Field(
        "average_similarity",
        description="指标类型：average_similarity 或 weighted_retrieval",
    )
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="指标参数，例如 target_document、alpha 等",
    )


class GlobalContext(BaseSchema):
    remote_base_url: str = Field(..., description="外部 RAG 系统评估接口基础地址")
    dataset_name: Optional[str] = Field(None, description="数据集名称")
    n_samples: Optional[int] = Field(None, description="采样数量")


class OptimizationCallback(BaseSchema):
    stage_result_webhook: Optional[str] = Field(
        None, description="阶段结果回调地址"
    )
    result_webhook: Optional[str] = Field(
        None, description="最终结果回调地址"
    )


class OptimizationRequest(BaseSchema):
    schema_id: str = Field(..., description="参数规范 ID")
    run_id: Optional[str] = Field(None, description="调用方运行 ID")
    stage_sequence: List[str] = Field(..., description="阶段执行顺序")
    stages: List[StageRequest] = Field(..., description="阶段配置列表")
    dataset_items: List[DatasetItem] = Field(..., description="评估样本集合")
    global_context: Optional[GlobalContext] = Field(
        None, description="全局上下文配置"
    )
    metric: Optional[MetricSpec] = Field(None, description="指标配置")
    callback: Optional[OptimizationCallback] = Field(
        None, description="回调配置"
    )


class StageResult(BaseSchema):
    name: str = Field(..., description="阶段名称")
    best_score: float = Field(..., description="最佳得分")
    best_params: Dict[str, Any] = Field(
        default_factory=dict, description="最佳参数组合"
    )
    history: List[Dict[str, Any]] = Field(
        default_factory=list, description="调优历史"
    )
    improvement: float = Field(
        0.0, description="相对初始得分的提升（百分比或倍数）"
    )


class OptimizationResponse(BaseSchema):
    request_id: str = Field(..., description="请求 ID")
    status: StatusEnum = Field(..., description="处理状态")
    stages: List[StageResult] = Field(default_factory=list, description="阶段结果")
    best_overall_score: float = Field(..., description="整体最佳得分")
    best_parameters: Dict[str, Any] = Field(
        default_factory=dict, description="最终最佳参数集合"
    )
