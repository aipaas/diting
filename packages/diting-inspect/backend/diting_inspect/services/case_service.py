"""
Business logic service for managing LLM test cases.
Provides high-level operations and encapsulates business rules.
"""

from typing import List, Optional, Dict, Any
from diting_inspect.models.case_model import LLMCaseData, CaseRepository


class CaseService:
    """
    Service class for managing LLM test cases.

    Encapsulates business logic and provides a clean interface for
    case management operations. Separates business rules from data access.
    """

    def __init__(self, repository: CaseRepository):
        """
        Initialize service with repository dependency.

        Args:
            repository: Case repository for data persistence
        """
        self._repository = repository

    async def get_cases(self, skip: int = 0, limit: int = 100) -> List[LLMCaseData]:
        """
        Retrieve paginated list of test cases.

        Args:
            skip: Number of cases to skip for pagination
            limit: Maximum number of cases to return (max 1000)

        Returns:
            List of test cases

        Raises:
            ValueError: If limit exceeds maximum allowed
        """
        if limit > 1000:
            raise ValueError("Limit cannot exceed 1000 cases")

        return await self._repository.get_all(skip=skip, limit=limit)

    async def get_case(self, case_id: str) -> Optional[LLMCaseData]:
        """
        Retrieve a specific test case by ID.

        Args:
            case_id: Unique identifier for the test case

        Returns:
            Test case if found, None otherwise
        """
        if not case_id or not case_id.strip():
            return None

        return await self._repository.get_by_id(case_id.strip())

    async def create_case(self, case: LLMCaseData) -> LLMCaseData:
        """
        Create a new test case with validation.

        Args:
            case: Test case to create

        Returns:
            Created test case

        Raises:
            ValueError: If case data is invalid
        """
        self._validate_case(case)
        return await self._repository.create(case)

    async def update_case(
        self, case_id: str, updates: Dict[str, Any]
    ) -> Optional[LLMCaseData]:
        """
        Update an existing test case.

        Args:
            case_id: Unique identifier for the test case
            updates: Dictionary of fields to update

        Returns:
            Updated test case if found, None otherwise

        Raises:
            ValueError: If update data is invalid
        """
        if not case_id or not case_id.strip():
            return None

        # # Validate updates if they contain critical fields
        # if "input" in updates and not updates["input"].strip():
        #     raise ValueError("Input cannot be empty")

        # if "actual_output" in updates and not updates["actual_output"].strip():
        #     raise ValueError("Actual output cannot be empty")

        return await self._repository.update(case_id.strip(), updates)

    async def delete_case(self, case_id: str) -> bool:
        """
        Delete a test case.

        Args:
            case_id: Unique identifier for the test case

        Returns:
            True if case was deleted, False if not found
        """
        if not case_id or not case_id.strip():
            return False

        return await self._repository.delete(case_id.strip())

    async def get_cases_by_tags(self, tags: List[str]) -> List[LLMCaseData]:
        """
        Retrieve test cases filtered by tags.

        Args:
            tags: List of tags to filter by

        Returns:
            List of matching test cases
        """
        if not tags:
            return []

        # Clean and filter tags
        clean_tags = [tag.strip() for tag in tags if tag.strip()]
        if not clean_tags:
            return []

        return await self._repository.get_by_tags(clean_tags)

    def _validate_case(self, case: LLMCaseData) -> None:
        """
        Validate test case data.

        Args:
            case: Test case to validate

        Raises:
            ValueError: If case data is invalid
        """
        if not case.input or not case.input.strip():
            raise ValueError("Input is required and cannot be empty")

        if not case.actual_output or not case.actual_output.strip():
            raise ValueError("Actual output is required and cannot be empty")

        if case.context and any(not ctx.strip() for ctx in case.context):
            raise ValueError("Context items cannot be empty")

        if case.retrieval_context and any(
            not ctx.strip() for ctx in case.retrieval_context
        ):
            raise ValueError("Retrieval context items cannot be empty")
