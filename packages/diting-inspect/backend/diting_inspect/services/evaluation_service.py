"""
Service for running evaluations on test cases using metrics.
Handles concurrent execution and result management.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from enum import Enum

from diting_inspect.models.case_model import LLMCase, CaseRepository
from diting_inspect.models.evaluation_model import (
    EvaluationResult,
    EvaluationRepository,
)
from diting_inspect.metrics.base_metric import BaseMetric
from diting_inspect.metrics.metric_factory import MetricFactory

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

    async def run_evaluation(
        self,
        evaluation_id: str,
        case_ids: List[str],
        metric_configs: List[Dict[str, Any]],
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
            cases: list[LLMCase] = []
            if self._case_repository:
                for case_id in case_ids:
                    case = await self._case_repository.get_by_id(case_id)
                    if case:
                        cases.append(case)

            if not cases:
                raise ValueError("No valid test cases found")

            # Load metrics from configs
            metrics = self._load_metrics(metric_configs)

            # Run evaluations concurrently
            semaphore = asyncio.Semaphore(self._max_concurrent)
            tasks = []

            for case in cases:
                for metric in metrics:
                    task = await self._evaluate_case_with_metric(
                        semaphore, case, metric, evaluation_id
                    )
                    tasks.append(task)  # type: ignore

            # Wait for all evaluations to complete
            results: List[Dict[str, Any]] = await asyncio.gather(
                *tasks, return_exceptions=True
            )  # type: ignore[misc]

            # Process results
            evaluation_results: List[Dict[str, Any]] = []
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Evaluation error: {result}")
                    continue
                if result:
                    evaluation_results.append(result)

            # Save final results
            final_result = EvaluationResult(
                id=evaluation_id,
                case_ids=case_ids,
                metric_configs=metric_configs,
                results=evaluation_results,
                status=EvaluationStatus.COMPLETED.value,
                started_at=self._active_evaluations[evaluation_id]["started_at"],
                completed_at=datetime.now(),
                total_cases=len(cases),
                total_metrics=len(metrics),
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
        semaphore: asyncio.Semaphore,
        case: LLMCase,
        metric: BaseMetric,
        evaluation_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate a single case with a single metric.

        Args:
            semaphore: Concurrency control semaphore
            case: Test case to evaluate
            metric: Metric to apply
            evaluation_id: Evaluation identifier for tracking

        Returns:
            Evaluation result dictionary or None if failed
        """
        async with semaphore:
            try:
                score = await metric.compute(case)

                result = {
                    "case_id": case.id,
                    "metric_name": metric.name,
                    "score": score,
                    "threshold": metric.threshold,
                    "passed": metric.is_passing(),
                    "evaluated_at": datetime.now().isoformat(),
                }

                # Update progress
                if evaluation_id in self._active_evaluations:
                    self._active_evaluations[evaluation_id]["completed_cases"] += 1

                return result

            except Exception as e:
                logger.error(
                    f"Failed to evaluate case {case.id} with {metric.__class__.__name__}: {e}"
                )
                return {
                    "case_id": case.id,
                    "metric_name": metric.__class__.__name__,
                    "score": None,
                    "threshold": metric.threshold,
                    "passed": False,
                    "error": str(e),
                    "evaluated_at": datetime.now().isoformat(),
                }

    def _load_metrics(self, configs: List[Dict[str, Any]]) -> List[BaseMetric]:
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
        metrics: list[BaseMetric] = []

        for config in configs:
            metric_type = config.get("type", "")
            threshold = config.get("threshold", 0.8)

            # Create metric using the MetricFactory
            metric = MetricFactory.create(metric_type, threshold)
            metrics.append(metric)

        return metrics

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
