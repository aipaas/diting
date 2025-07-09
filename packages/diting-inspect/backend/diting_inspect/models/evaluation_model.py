"""
Data models for evaluation results and repository interface.
Provides structures for storing and retrieving evaluation outcomes.
"""

from typing import List, Dict, Any, Optional
from diting_inspect.models.model_management import ModelManagementData
from diting_inspect.models.model_pickle_persistence import PicklePersistentMixin
from pydantic import BaseModel, Field
from datetime import datetime
from abc import ABC, abstractmethod
import asyncio


class EvaluationResult(BaseModel):
    """
    Represents the result of an evaluation run.

    Contains metadata about the evaluation and detailed results
    for each case-metric combination.
    """

    id: str = Field(..., description="Unique evaluation identifier")
    case_ids: List[str] = Field(..., description="IDs of evaluated test cases")
    metric_configs: List[Dict[str, Any]] = Field(
        ..., description="Configuration for metrics used"
    )
    model_configs: Optional[List[ModelManagementData]] = Field(
        None, description="Models configuration for evaluation used"
    )
    results: List[Dict[str, Any]] = Field(
        ..., description="Detailed evaluation results"
    )
    status: str = Field(..., description="Evaluation status")
    started_at: datetime = Field(..., description="Evaluation start time")
    completed_at: Optional[datetime] = Field(
        None, description="Evaluation completion time"
    )
    total_cases: int = Field(..., description="Total number of cases evaluated")
    total_metrics: int = Field(..., description="Total number of metrics applied")
    error: Optional[str] = Field(None, description="Error message if failed")

    class Config:
        """Pydantic configuration for the model."""

        json_encoders = {datetime: lambda v: v.isoformat()}  #  # type: ignore

    @property
    def duration_seconds(self) -> Optional[float]:
        """
        Calculate evaluation duration in seconds.

        Returns:
            Duration in seconds if completed, None otherwise
        """
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def success_rate(self) -> float:
        """
        Calculate the success rate of evaluations.

        Returns:
            Percentage of evaluations that passed their thresholds
        """
        if not self.results:
            return 0.0

        passed_count = sum(1 for result in self.results if result.get("passed", False))
        return (passed_count / len(self.results)) * 100.0

    @property
    def average_score(self) -> Optional[float]:
        """
        Calculate average score across all evaluations.

        Returns:
            Average score or None if no valid scores
        """
        valid_scores = [
            result["score"]
            for result in self.results
            if result.get("score") is not None
        ]

        if not valid_scores:
            return None

        return sum(valid_scores) / len(valid_scores)


class EvaluationRepository(ABC):
    """
    Abstract repository interface for evaluation results.

    Defines the contract for persisting and retrieving evaluation data.
    """

    @abstractmethod
    async def save(self, result: EvaluationResult) -> EvaluationResult:
        """
        Save evaluation result.

        Args:
            result: Evaluation result to save

        Returns:
            Saved evaluation result
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, evaluation_id: str) -> Optional[EvaluationResult]:
        """
        Retrieve evaluation result by ID.

        Args:
            evaluation_id: Unique evaluation identifier

        Returns:
            Evaluation result if found, None otherwise
        """
        raise NotImplementedError

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[EvaluationResult]:
        """
        Retrieve all evaluation results with pagination.

        Args:
            skip: Number of results to skip
            limit: Maximum number of results to return

        Returns:
            List of evaluation results
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, evaluation_id: str) -> bool:
        """
        Delete evaluation result.

        Args:
            evaluation_id: Unique evaluation identifier

        Returns:
            True if deleted, False if not found
        """
        raise NotImplementedError


class InMemoryEvaluationRepository(EvaluationRepository, PicklePersistentMixin):
    """
    In-memory implementation of EvaluationRepository.

    Stores evaluation results in memory for development and testing.
    Data is lost when application restarts.
    """

    def __init__(self, pickle_file: str = "data/evaluations.pkl"):
        """Initialize empty in-memory storage."""
        super().__init__(pickle_file)
        self._results: Dict[str, EvaluationResult] = self.load_from_pickle({})
        self._lock = asyncio.Lock()

    async def save(self, result: EvaluationResult) -> EvaluationResult:
        """
        Save evaluation result.

        Args:
            result: Evaluation result to save

        Returns:
            Saved evaluation result
        """
        async with self._lock:
            self._results[result.id] = result
            self.save_to_pickle(self._results)
            return result

    async def get_by_id(self, evaluation_id: str) -> Optional[EvaluationResult]:
        """
        Retrieve evaluation result by ID.

        Args:
            evaluation_id: Unique evaluation identifier

        Returns:
            Evaluation result if found, None otherwise
        """
        async with self._lock:
            return self._results.get(evaluation_id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[EvaluationResult]:
        """
        Retrieve all evaluation results with pagination.

        Args:
            skip: Number of results to skip
            limit: Maximum number of results to return

        Returns:
            List of evaluation results sorted by start time (newest first)
        """
        async with self._lock:
            results = list(self._results.values())
            results.sort(key=lambda x: x.started_at, reverse=True)
            return results[skip : skip + limit]

    async def delete(self, evaluation_id: str) -> bool:
        """
        Delete evaluation result.

        Args:
            evaluation_id: Unique evaluation identifier

        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            if evaluation_id in self._results:
                del self._results[evaluation_id]
                self.save_to_pickle(self._results)
                return True
            return False
