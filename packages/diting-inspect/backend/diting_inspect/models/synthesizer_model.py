"""
Data models for synthesizer results and repository interface.
Provides structures for storing and retrieving synthesizer outcomes.
"""

import asyncio
from typing import List, Dict, Any, Optional
from diting_inspect.models.model_management import ModelManagementData
from diting_inspect.models.model_pickle_persistence import PicklePersistentMixin
from pydantic import BaseModel, Field
from datetime import datetime
from abc import ABC, abstractmethod


class SynthesizerResult(BaseModel):
    """
    Represents the result of a synthesizer run.

    Contains metadata about the synthesizer and detailed results
    for each case-metric combination.
    """

    id: str = Field(..., description="Unique synthesizer identifier")
    case_ids: List[str] = Field(..., description="IDs of synthesized test cases")
    synthesizer_configs: List[Dict[str, Any]] = Field(
        ..., description="Configuration for synthesizer used"
    )
    model_configs: Optional[List[ModelManagementData]] = Field(
        None, description="Models configuration for synthesizer used"
    )
    results: List[Dict[str, Any]] = Field(
        ..., description="Detailed synthesizer results"
    )
    status: str = Field(..., description="Synthesizer status")
    started_at: datetime = Field(..., description="Synthesizer start time")
    completed_at: Optional[datetime] = Field(
        None, description="Synthesizer completion time"
    )
    total_cases: int = Field(..., description="Total number of cases synthesized")
    total_synthesizers: int = Field(
        ..., description="Total number of synthesizers applied"
    )
    error: Optional[str] = Field(None, description="Error message if failed")

    class Config:
        """Pydantic configuration for the model."""

        json_encoders = {datetime: lambda v: v.isoformat()}  # type: ignore

    @property
    def duration_seconds(self) -> Optional[float]:
        """
        Calculate synthesizer duration in seconds.

        Returns:
            Duration in seconds if completed, None otherwise
        """
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def success_rate(self) -> float:
        """
        Calculate the success rate of synthesizer evaluations.

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
        Calculate average score across all synthesizer evaluations.

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


class SynthesizerRepository(ABC):
    """
    Abstract repository interface for synthesizer results.

    Defines the contract for persisting and retrieving synthesizer data.
    """

    @abstractmethod
    async def save(self, result: SynthesizerResult) -> SynthesizerResult:
        """
        Save synthesizer result.

        Args:
            result: Synthesizer result to save

        Returns:
            Saved synthesizer result
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, synthesizer_id: str) -> Optional[SynthesizerResult]:
        """
        Retrieve synthesizer result by ID.

        Args:
            synthesizer_id: Unique synthesizer identifier

        Returns:
            Synthesizer result if found, None otherwise
        """
        raise NotImplementedError

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[SynthesizerResult]:
        """
        Retrieve all synthesizer results with pagination.

        Args:
            skip: Number of results to skip
            limit: Maximum number of results to return

        Returns:
            List of synthesizer results
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, synthesizer_id: str) -> bool:
        """
        Delete synthesizer result.

        Args:
            synthesizer_id: Unique synthesizer identifier

        Returns:
            True if deleted, False if not found
        """
        raise NotImplementedError


class InMemorySynthesizerRepository(SynthesizerRepository, PicklePersistentMixin):
    """
    In-memory implementation of SynthesizerRepository.

    Stores synthesizer results in memory for development and testing.
    Data is lost when application restarts.
    """

    def __init__(self, pickle_file: str = "data/synthesizers.pkl"):
        """Initialize empty in-memory storage."""
        super().__init__(pickle_file)
        self._results: Dict[str, SynthesizerResult] = self.load_from_pickle({})
        self._lock = asyncio.Lock()

    async def save(self, result: SynthesizerResult) -> SynthesizerResult:
        """
        Save synthesizer result.

        Args:
            result: Synthesizer result to save

        Returns:
            Saved synthesizer result
        """
        async with self._lock:
            self._results[result.id] = result
            self.save_to_pickle(self._results)
            return result

    async def get_by_id(self, synthesizer_id: str) -> Optional[SynthesizerResult]:
        """
        Retrieve synthesizer result by ID.

        Args:
            synthesizer_id: Unique synthesizer identifier

        Returns:
            Synthesizer result if found, None otherwise
        """
        async with self._lock:
            return self._results.get(synthesizer_id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[SynthesizerResult]:
        """
        Retrieve all synthesizer results with pagination.

        Args:
            skip: Number of results to skip
            limit: Maximum number of results to return

        Returns:
            List of synthesizer results sorted by start time (newest first)
        """
        async with self._lock:
            results = list(self._results.values())
            results.sort(key=lambda x: x.started_at, reverse=True)
            return results[skip : skip + limit]

    async def delete(self, synthesizer_id: str) -> bool:
        """
        Delete synthesizer result.

        Args:
            synthesizer_id: Unique synthesizer identifier

        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            if synthesizer_id in self._results:
                del self._results[synthesizer_id]
                self.save_to_pickle(self._results)
                return True
            return False
