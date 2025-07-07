"""
Data models and repository for LLM test cases.
Provides the core data structures and persistence layer for test cases.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from abc import ABC, abstractmethod
import asyncio
from datetime import datetime


class LLMCase(BaseModel):
    """
    Represents a test case for LLM evaluation.

    Contains input data, expected/actual outputs, and contextual information
    used for evaluating language model performance.
    """

    id: str = Field(..., description="Unique identifier for the test case")
    input: str = Field(..., description="Input prompt or query")
    actual_output: str = Field(..., description="Actual LLM response")
    expected_output: Optional[str] = Field(
        None, description="Expected or reference output"
    )
    context: Optional[List[str]] = Field(
        None, description="Additional context information"
    )
    retrieval_context: Optional[List[str]] = Field(
        None, description="Retrieved context for RAG systems"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Timestamp when case was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="Timestamp when case was last updated"
    )
    tags: Optional[List[str]] = Field(
        None, description="Tags for categorizing test cases"
    )

    class Config:
        """Pydantic configuration for the model."""

        json_encoders = {datetime: lambda v: v.isoformat()}  # type: ignore


class CaseRepository(ABC):
    """
    Abstract repository interface for LLM test cases.

    Defines the contract for data persistence operations on test cases.
    Implementations can use different storage backends (database, file, etc).
    """

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[LLMCase]:
        """
        Retrieve all test cases with pagination.

        Args:
            skip: Number of cases to skip
            limit: Maximum number of cases to return

        Returns:
            List of test cases
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, case_id: str) -> Optional[LLMCase]:
        """
        Retrieve a test case by its ID.

        Args:
            case_id: Unique identifier for the case

        Returns:
            Test case if found, None otherwise
        """
        raise NotImplementedError

    @abstractmethod
    async def create(self, case: LLMCase) -> LLMCase:
        """
        Create a new test case.

        Args:
            case: Test case to create

        Returns:
            Created test case with any generated fields
        """
        raise NotImplementedError

    @abstractmethod
    async def update(self, case_id: str, updates: Dict[str, Any]) -> Optional[LLMCase]:
        """
        Update an existing test case.

        Args:
            case_id: Unique identifier for the case
            updates: Dictionary of fields to update

        Returns:
            Updated test case if found, None otherwise
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, case_id: str) -> bool:
        """
        Delete a test case.

        Args:
            case_id: Unique identifier for the case

        Returns:
            True if case was deleted, False if not found
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_tags(self, tags: List[str]) -> List[LLMCase]:
        """
        Retrieve test cases by tags.

        Args:
            tags: List of tags to filter by

        Returns:
            List of test cases matching the tags
        """
        raise NotImplementedError


class InMemoryCaseRepository(CaseRepository):
    """
    In-memory implementation of CaseRepository for development/testing.

    Stores test cases in memory using a dictionary. Data is lost when
    application restarts. Suitable for development and testing purposes.
    """

    def __init__(self):
        """Initialize empty in-memory storage."""
        self._cases: Dict[str, LLMCase] = {}
        self._lock = asyncio.Lock()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[LLMCase]:
        """
        Retrieve all test cases with pagination.

        Args:
            skip: Number of cases to skip
            limit: Maximum number of cases to return

        Returns:
            List of test cases
        """
        async with self._lock:
            cases = list(self._cases.values())
            # Sort by creation date (newest first)
            cases.sort(key=lambda x: x.created_at, reverse=True)
            return cases[skip : skip + limit]

    async def get_by_id(self, case_id: str) -> Optional[LLMCase]:
        """
        Retrieve a test case by its ID.

        Args:
            case_id: Unique identifier for the case

        Returns:
            Test case if found, None otherwise
        """
        async with self._lock:
            return self._cases.get(case_id)

    async def create(self, case: LLMCase) -> LLMCase:
        """
        Create a new test case.

        Args:
            case: Test case to create

        Returns:
            Created test case
        """
        async with self._lock:
            case.created_at = datetime.now()
            case.updated_at = datetime.now()
            self._cases[case.id] = case
            return case

    async def update(self, case_id: str, updates: Dict[str, Any]) -> Optional[LLMCase]:
        """
        Update an existing test case.

        Args:
            case_id: Unique identifier for the case
            updates: Dictionary of fields to update

        Returns:
            Updated test case if found, None otherwise
        """
        async with self._lock:
            if case_id not in self._cases:
                return None

            case = self._cases[case_id]

            # Filter out None values and update only provided fields
            filtered_updates = {
                k: v for k, v in updates.items() if v is not None and hasattr(case, k)
            }

            # Update the case
            for key, value in filtered_updates.items():
                setattr(case, key, value)

            case.updated_at = datetime.now()
            self._cases[case_id] = case
            return case

    async def delete(self, case_id: str) -> bool:
        """
        Delete a test case.

        Args:
            case_id: Unique identifier for the case

        Returns:
            True if case was deleted, False if not found
        """
        async with self._lock:
            if case_id in self._cases:
                del self._cases[case_id]
                return True
            return False

    async def get_by_tags(self, tags: List[str]) -> List[LLMCase]:
        """
        Retrieve test cases by tags.

        Args:
            tags: List of tags to filter by

        Returns:
            List of test cases matching any of the provided tags
        """
        async with self._lock:
            matching_cases: list[LLMCase] = []
            for case in self._cases.values():
                if case.tags and any(tag in case.tags for tag in tags):
                    matching_cases.append(case)

            # Sort by creation date (newest first)
            matching_cases.sort(key=lambda x: x.created_at, reverse=True)
            return matching_cases
