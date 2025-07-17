"""
Data models for tool execution results and repository interface.
Provides structures for storing and retrieving tool execution outcomes.
"""

import asyncio
from typing import List, Dict, Any, Optional
from diting_inspect.models.model_pickle_persistence import PicklePersistentMixin
from pydantic import BaseModel, Field
from datetime import datetime
from abc import ABC, abstractmethod


class ToolExecutionResult(BaseModel):
    """
    Represents the result of a tool execution.

    Contains metadata about the tool execution and detailed results
    for each case-metric combination.
    """

    id: str = Field(..., description="Unique tool execution identifier")
    case_ids: List[str] = Field(..., description="IDs of executed test cases")
    results: List[Any] = Field(..., description="Detailed tool execution results")
    status: str = Field(..., description="Tool execution status")
    started_at: datetime = Field(..., description="Tool execution start time")
    completed_at: Optional[datetime] = Field(
        None, description="Tool execution completion time"
    )
    error: Optional[str] = Field(None, description="Error message if failed")

    class Config:
        """Pydantic configuration for the model."""

        json_encoders = {datetime: lambda v: v.isoformat()}  # type: ignore

    @property
    def duration_seconds(self) -> Optional[float]:
        """
        Calculate tool execution duration in seconds.

        Returns:
            Duration in seconds if completed, None otherwise
        """
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def success_rate(self) -> float:
        """
        Calculate the success rate of tool executions.

        Returns:
            Percentage of executions that passed their thresholds
        """
        if not self.results:
            return 0.0

        passed_count = sum(1 for result in self.results if result.get("passed", False))
        return (passed_count / len(self.results)) * 100.0


class ToolExecutionRepository(ABC):
    """
    Abstract repository interface for tool execution results.

    Defines the contract for persisting and retrieving tool execution data.
    """

    @abstractmethod
    async def save(self, result: ToolExecutionResult) -> ToolExecutionResult:
        """
        Save tool execution result.

        Args:
            result: Tool execution result to save

        Returns:
            Saved tool execution result
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, execution_id: str) -> Optional[ToolExecutionResult]:
        """
        Retrieve tool execution result by ID.

        Args:
            execution_id: Unique tool execution identifier

        Returns:
            Tool execution result if found, None otherwise
        """
        raise NotImplementedError

    @abstractmethod
    async def get_all(
        self, skip: int = 0, limit: int = 100
    ) -> List[ToolExecutionResult]:
        """
        Retrieve all tool execution results with pagination.

        Args:
            skip: Number of results to skip
            limit: Maximum number of results to return

        Returns:
            List of tool execution results
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, execution_id: str) -> bool:
        """
        Delete tool execution result.

        Args:
            execution_id: Unique tool execution identifier

        Returns:
            True if deleted, False if not found
        """
        raise NotImplementedError


class InMemoryToolExecutionRepository(ToolExecutionRepository, PicklePersistentMixin):
    """
    In-memory implementation of ToolExecutionRepository.

    Stores tool execution results in memory for development and testing.
    Data is lost when application restarts.
    """

    def __init__(self, pickle_file: str = "data/tool_executions.pkl"):
        """Initialize empty in-memory storage."""
        super().__init__(pickle_file)
        self._results: Dict[str, ToolExecutionResult] = self.load_from_pickle({})
        self._lock = asyncio.Lock()

    async def save(self, result: ToolExecutionResult) -> ToolExecutionResult:
        """
        Save tool execution result.

        Args:
            result: Tool execution result to save

        Returns:
            Saved tool execution result
        """
        async with self._lock:
            self._results[result.id] = result
            self.save_to_pickle(self._results)
            return result

    async def get_by_id(self, execution_id: str) -> Optional[ToolExecutionResult]:
        """
        Retrieve tool execution result by ID.

        Args:
            execution_id: Unique tool execution identifier

        Returns:
            Tool execution result if found, None otherwise
        """
        async with self._lock:
            return self._results.get(execution_id)

    async def get_all(
        self, skip: int = 0, limit: int = 100
    ) -> List[ToolExecutionResult]:
        """
        Retrieve all tool execution results with pagination.

        Args:
            skip: Number of results to skip
            limit: Maximum number of results to return

        Returns:
            List of tool execution results sorted by start time (newest first)
        """
        async with self._lock:
            results = list(self._results.values())
            results.sort(key=lambda x: x.started_at, reverse=True)
            return results[skip : skip + limit]

    async def delete(self, execution_id: str) -> bool:
        """
        Delete tool execution result.

        Args:
            execution_id: Unique tool execution identifier

        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            if execution_id in self._results:
                del self._results[execution_id]
                self.save_to_pickle(self._results)
                return True
            return False
