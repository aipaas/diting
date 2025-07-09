"""
Service for running evaluations on test cases using metrics.
Handles concurrent execution and result management.
"""

import asyncio
from copy import deepcopy
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from enum import Enum

from diting_core.cases.llm_case import LLMCase
from diting_core.models.embeddings.factory import embedding_factory
from diting_core.models.llms.factory import llm_factory
from diting_core.utilities.slug import camel_to_snake
from diting_inspect.models.case_model import LLMCaseData, CaseRepository
from diting_inspect.models.evaluation_model import (
    EvaluationResult,
    EvaluationRepository,
)
from diting_core.metrics.base_metric import BaseMetric
from diting_inspect.metrics import MetricFactory, MetricOptionSchema, discover_metrics
from diting_inspect.models.model_management import ModelManagementData, ModelType
from pydantic import SecretStr

logger = logging.getLogger(__name__)


class EvaluationStatus(Enum):
    """Enumeration of evaluation statuses."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class EvaluationService:
    """
    Service for managing and executing evaluations.

    Provides functionality to run metrics on test cases concurrently,
    track evaluation progress, and store results.
    """

    def __init__(
        self,
        evaluation_repository: EvaluationRepository,
        case_repository: Optional[CaseRepository] = None,
        max_concurrent_evaluations: int = 10,
    ):
        """
        Initialize evaluation service.

        Args:
            evaluation_repository: Repository for storing evaluation results
            case_repository: Repository for accessing test cases
            max_concurrent_evaluations: Maximum concurrent evaluations
        """
        self._evaluation_repository = evaluation_repository
        self._case_repository = case_repository
        self._max_concurrent = max_concurrent_evaluations
        self._active_evaluations: Dict[str, Dict[str, Any]] = {}

    async def get_available_metrics(self) -> list[MetricOptionSchema]:
        metrics = discover_metrics()
        return [
            MetricOptionSchema(
                name=k,
                threshold=getattr(v, "threshold", None),
                debug=getattr(v, "debug", None),
            )
            for k, v in metrics.items()
        ]

    async def run_evaluation(
        self,
        evaluation_id: str,
        case_ids: List[str],
        metric_configs: List[Dict[str, Any]],
        model_configs: Optional[List[ModelManagementData]] = None,
    ) -> None:
        """
        Run evaluation on specified cases with given metrics.

        Args:
            evaluation_id: Unique identifier for this evaluation
            case_ids: List of test case IDs to evaluate
            metric_configs: List of metric configurations
        """
        try:
            # Initialize evaluation tracking
            self._active_evaluations[evaluation_id] = {
                "status": EvaluationStatus.RUNNING.value,
                "started_at": datetime.now(),
                "total_cases": len(case_ids),
                "completed_cases": 0,
                "results": [],
            }

            # Save initial evaluation status to the repository
            initial_result = EvaluationResult(
                id=evaluation_id,
                case_ids=case_ids,
                metric_configs=metric_configs,
                model_configs=model_configs,
                results=[],
                status=EvaluationStatus.RUNNING.value,
                started_at=datetime.now(),
                completed_at=None,
                total_cases=len(case_ids),
                total_metrics=len(metric_configs),
                error=None,
            )
            await self._evaluation_repository.save(initial_result)

            # Get test cases
            cases: list[LLMCaseData] = []
            if self._case_repository:
                for case_id in case_ids:
                    case = await self._case_repository.get_by_id(case_id)
                    if case:
                        cases.append(case)

            if not cases:
                raise ValueError("No valid test cases found")

            # Load metrics from configs
            metric_configs_loaded = self._load_metrics(metric_configs)

            # Create a semaphore to limit concurrent evaluations
            semaphore = asyncio.Semaphore(self._max_concurrent)

            async def evaluate_case(
                case: LLMCaseData,
                metric_config: Dict[str, Any],
                model_config: Optional[List[ModelManagementData]] = None,
            ):
                async with semaphore:
                    return await self._evaluate_case_with_metric(
                        case, metric_config, evaluation_id, model_config
                    )

            # Run evaluations concurrently using TaskGroup
            tasks: list[asyncio.Task[Any]] = []
            async with asyncio.TaskGroup() as tg:
                for case in cases:
                    for metric_config in metric_configs_loaded:
                        task = tg.create_task(
                            evaluate_case(case, metric_config, model_configs)
                        )
                        tasks.append(task)

            # Process results
            evaluation_results: List[Dict[str, Any]] = []
            for task in tasks:
                try:
                    result = await task
                    if result:
                        evaluation_results.append(result)
                except Exception as e:
                    logger.error(f"Error processing task: {e}")

            # Save final results
            final_result = EvaluationResult(
                id=evaluation_id,
                case_ids=case_ids,
                metric_configs=metric_configs,
                model_configs=model_configs,
                results=evaluation_results,
                status=EvaluationStatus.COMPLETED.value,
                started_at=self._active_evaluations[evaluation_id]["started_at"],
                completed_at=datetime.now(),
                total_cases=len(cases),
                total_metrics=len(metric_configs),
                error=None,
            )

            await self._evaluation_repository.save(final_result)

            # Update tracking
            self._active_evaluations[evaluation_id].update(
                {
                    "status": EvaluationStatus.COMPLETED.value,
                    "completed_at": datetime.now(),
                    "results": evaluation_results,
                }
            )

        except Exception as e:
            logger.error(f"Evaluation {evaluation_id} failed: {e}")

            # Mark as failed
            if evaluation_id in self._active_evaluations:
                self._active_evaluations[evaluation_id].update(
                    {
                        "status": EvaluationStatus.FAILED.value,
                        "error": str(e),
                        "completed_at": datetime.now(),
                    }
                )

    async def delete_evaluation(self, evaluation_id: str) -> bool:
        return await self._evaluation_repository.delete(evaluation_id)

    async def _evaluate_case_with_metric(
        self,
        case: LLMCaseData,
        metric_config: Dict[str, Any],
        evaluation_id: str,
        model_configs: Optional[List[ModelManagementData]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate a single case with a single metric.

        Args:
            case: Test case to evaluate
            metric: Metric to apply
            evaluation_id: Evaluation identifier for tracking

        Returns:
            Evaluation result dictionary or None if failed
        """
        try:
            metric_case = LLMCase(
                user_input=case.input,
                actual_output=case.actual_output,
                expected_output=case.expected_output,
                context=case.context,
                retrieval_context=case.retrieval_context,
            )
            metric: BaseMetric = metric_config["class"]()

            is_model_deps = hasattr(metric, "model")
            is_embedding_deps = hasattr(metric, "embedding_model")
            llm_model_configs, embedding_model_configs = None, None
            if model_configs:
                llm_model_configs = [
                    m for m in model_configs if m.model_type == ModelType.INFERENCE
                ]
                embedding_model_configs = [
                    m for m in model_configs if m.model_type == ModelType.EMBEDDING
                ]

            if is_model_deps and llm_model_configs:
                _model = llm_model_configs[0]
                llm_model = llm_factory(
                    model=_model.model_name,
                    base_url=_model.access_endpoint,
                    api_key=SecretStr(_model.api_key),
                )
                setattr(metric, "model", llm_model)
            if is_embedding_deps and embedding_model_configs:
                _model = embedding_model_configs[0]
                embedding_model = embedding_factory(
                    model=_model.model_name,
                    base_url=_model.access_endpoint,
                    api_key=_model.api_key,
                )
                setattr(metric, "embedding_model", embedding_model)

            metric_value = await metric.compute(
                metric_case, verbose=metric_config["debug"]
            )

            result = {
                "case_id": case.id,
                "metric_name": metric.name,
                "score": metric_value.score,
                "evaluated_at": datetime.now().isoformat(),
            }
            # Update progress
            if evaluation_id in self._active_evaluations:
                self._active_evaluations[evaluation_id]["completed_cases"] += 1

            return result

        except Exception as e:
            logger.error(
                f"Failed to evaluate case {case.id} with {camel_to_snake(metric_config['class'].__name__)}: {e}"
            )
            return {
                "case_id": case.id,
                "metric_name": camel_to_snake(metric_config["class"].__name__),
                "score": None,
                "error": str(e),
                "evaluated_at": datetime.now().isoformat(),
            }

    def _load_metrics(self, configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Load metrics from configuration dictionaries.

        Args:
            configs: List of metric configurations

        Returns:
            List of initialized metric instances

        Note:
            This is a simplified implementation. In a real application,
            you would implement a metric factory or registry pattern.
        """
        configs_copy = deepcopy(configs)
        metric_factory = MetricFactory()

        for config in configs_copy:
            metric_type = config.get("type", "")
            metric = metric_factory.create(metric_type)
            config["class"] = metric

        return configs_copy

    async def get_evaluation_result(
        self, evaluation_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get evaluation status and results.

        Args:
            evaluation_id: Unique evaluation identifier

        Returns:
            Evaluation result dictionary or None if not found
        """
        # Check active evaluations first
        if evaluation_id in self._active_evaluations:
            return self._active_evaluations[evaluation_id]

        # Check persisted results
        result = await self._evaluation_repository.get_by_id(evaluation_id)
        if result:
            return result.model_dump()

        return None

    async def get_evaluations(
        self, skip: int = 0, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get list of evaluation results.

        Args:
            skip: Number of results to skip for pagination
            limit: Maximum number of results to return

        Returns:
            List of evaluation result dictionaries
        """
        results = await self._evaluation_repository.get_all(skip=skip, limit=limit)
        return [result.model_dump() for result in results]
