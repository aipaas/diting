#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, Optional
import math

import httpx

from diting_core.metrics import (
    AverageSimilarityMetric,
    WeightedRetrievalMetric,
)
from diting_core.optimization.datasets.base_dataset import InMemoryDataset
from diting_core.optimization.optimization_result import OptimizationResult
from diting_core.optimization.retrieval.semantic_search.optimizer import (
    SemanticSearchExhaustiveOptimizer,
)
from diting_core.optimization.target.semantic_search_config import SemanticSearchConfig
from diting_server.apis.v1.optimization.data_models import (
    DatasetItem,
    MetricSpec,
    OptimizationRequest,
    OptimizationResponse,
    StageRequest,
    StageResult,
)
from diting_server.common.logging_config.config import get_logger
from diting_server.common.schema import StatusEnum
from diting_server.services.optimization.callback_retriever import (
    CallbackSemanticRetriever,
)

logger = get_logger(__name__)


class RAGOptimizationService:
    """Service entry point for running RAG parameter optimization via diting-core."""

    async def run_optimization(
        self, request: OptimizationRequest, request_id: str
    ) -> OptimizationResponse:
        if not request.stage_sequence:
            raise ValueError("stage_sequence must contain at least one stage.")

        stage_map = {stage.name: stage for stage in request.stages}
        results: list[StageResult] = []
        best_score: Optional[float] = None
        final_params: Dict[str, Any] = {}
        callback_cfg = request.callback

        # Currently only retrieval.semantic_search stage is implemented.
        for stage_name in request.stage_sequence:
            stage_request = stage_map.get(stage_name)
            if not stage_request:
                raise ValueError(f"stage '{stage_name}' missing in stages definition.")

            if stage_name == "retrieval.semantic_search":
                stage_result = await self._optimize_retrieval_stage(
                    request=request,
                    stage=stage_request,
                    request_id=request_id,
                )
            else:
                raise ValueError(
                    f"Stage '{stage_name}' is not supported yet. "
                    "Currently only retrieval.semantic_search is available."
                )

            results.append(stage_result)
            best_score = stage_result.best_score
            final_params.update(stage_result.best_params or {})
            if callback_cfg and callback_cfg.stage_result_webhook:
                await self._post_callback(
                    url=callback_cfg.stage_result_webhook,
                    payload={
                        "event": "stage_completed",
                        "requestId": request_id,
                        "runId": request.run_id or request_id,
                        "schemaId": request.schema_id,
                        "stageResult": stage_result.model_dump(by_alias=True),
                    },
                    request_id=request_id,
                )

        # 确保分数不是无穷大或NaN
        if best_score is not None:
            if math.isinf(best_score) or math.isnan(best_score):
                best_score = 0.0

        # 确保参数不是无穷大或NaN
        sanitized_params = {}
        for key, value in final_params.items():
            if isinstance(value, float) and (math.isinf(value) or math.isnan(value)):
                sanitized_params[key] = 0.0
            else:
                sanitized_params[key] = value

        response = OptimizationResponse(
            request_id=request_id,
            status=StatusEnum.SUCCESS,
            stages=results,
            best_overall_score=best_score if best_score is not None else 0.0,
            best_parameters=sanitized_params,
        )
        if callback_cfg and callback_cfg.result_webhook:
            final_payload = response.model_dump(by_alias=True)
            final_payload["runId"] = request.run_id or request_id
            final_payload["schemaId"] = request.schema_id
            await self._post_callback(
                url=callback_cfg.result_webhook,
                payload=final_payload,
                request_id=request_id,
                event="optimization_completed",
            )
        return response

    async def _optimize_retrieval_stage(
        self,
        *,
        request: OptimizationRequest,
        stage: StageRequest,
        request_id: str,
    ) -> StageResult:
        """优化检索阶段

        使用 diting-core 的 SemanticSearchExhaustiveOptimizer 进行优化。
        通过 CallbackSemanticRetriever 调用发起方的检索服务获取结果。
        """
        base_url = request.global_context.remote_base_url if request.global_context else None
        if not base_url:
            raise ValueError("global_context.remote_base_url is required for retrieval stage.")

        # 构建数据集和指标
        dataset = self._build_dataset(request.dataset_items)
        metric = self._build_metric(request.metric)

        # 创建回调检索器（通过发起方的 URL 获取检索结果）
        retriever = CallbackSemanticRetriever(callback_url=base_url, timeout=30.0)

        # 创建语义搜索配置
        config = SemanticSearchConfig(
            similarity_threshold=float(stage.parameters.get("similarity_threshold", 0.4)),
            context_recall_max_tokens=int(
                stage.parameters.get("context_recall_max_tokens", 4000)
            ),
            semantic_retriever=retriever,
        )

        # 创建穷举优化器
        optimizer = SemanticSearchExhaustiveOptimizer(
            similarity_threshold_range=self._resolve_float_range(
                stage.parameters_overrides.similarity_threshold_range
            ),
            similarity_threshold_step=self._resolve_float_step(
                stage.parameters_overrides.similarity_threshold_step
            ),
            context_recall_tokens_range=self._resolve_int_range(
                stage.parameters_overrides.context_recall_tokens_range
            ),
            context_recall_tokens_step=self._resolve_int_step(
                stage.parameters_overrides.context_recall_tokens_step
            ),
            max_workers=5,  # 控制并发数
        )

        # 执行优化
        result: OptimizationResult = await optimizer.optimize(
            config=config,
            dataset=dataset,
            metric=metric,
            n_samples=request.global_context.n_samples if request.global_context else None,
            run_id=request.run_id or request_id,
        )

        # 确保分数不是无穷大或NaN
        best_score = result.best_score
        if best_score is not None:
            if math.isinf(best_score) or math.isnan(best_score):
                best_score = 0.0

        # 确保改进不是无穷大或NaN
        improvement = result.improvement if result.improvement is not None else 0.0
        if math.isinf(improvement) or math.isnan(improvement):
            improvement = 0.0

        # 确保参数不是无穷大或NaN
        best_params = result.details.get("best_params", {})
        sanitized_params = {}
        for key, value in best_params.items():
            if isinstance(value, float) and (math.isinf(value) or math.isnan(value)):
                sanitized_params[key] = 0.0
            else:
                sanitized_params[key] = value

        # 构造阶段结果
        return StageResult(
            name=stage.name,
            best_score=best_score,
            best_params=sanitized_params,
            history=result.history,
            improvement=improvement,
        )

    def _build_dataset(self, items: list[DatasetItem]) -> InMemoryDataset:
        dict_items = [item.model_dump() for item in items]
        return InMemoryDataset(name="rag-optimization-dataset", items=dict_items)

    def _build_metric(self, metric_spec: Optional[MetricSpec]) -> AverageSimilarityMetric:
        if not metric_spec or metric_spec.type == "average_similarity":
            return AverageSimilarityMetric()
        if metric_spec.type == "weighted_retrieval":
            target_doc = metric_spec.params.get("target_document")
            alpha = float(metric_spec.params.get("alpha", 0.7))
            if not target_doc:
                raise ValueError("weighted_retrieval metric requires 'target_document'.")
            return WeightedRetrievalMetric(target_document=target_doc, alpha=alpha)
        raise ValueError(f"Unsupported metric type: {metric_spec.type}")

    def _resolve_float_range(
        self, value: Optional[tuple[float, float]]
    ) -> tuple[float, float]:
        if not value:
            return (0.3, 0.9)
        return (float(value[0]), float(value[1]))

    def _resolve_float_step(self, value: Optional[float]) -> float:
        return float(value) if value is not None else 0.05

    def _resolve_int_range(self, value: Optional[tuple[int, int]]) -> tuple[int, int]:
        if not value:
            return (3000, 7000)
        return (int(value[0]), int(value[1]))

    def _resolve_int_step(self, value: Optional[int]) -> int:
        return int(value) if value is not None else 500

    async def _post_callback(
        self,
        *,
        url: str,
        payload: dict[str, Any],
        request_id: str,
        event: str | None = None,
    ) -> None:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
        except Exception as exc:
            logger.warning(
                "Failed to send optimization callback",
                request_id=request_id,
                callback_url=url,
                event=event,
                error=str(exc),
            )


rag_optimization_service = RAGOptimizationService()