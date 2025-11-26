"""Evaluator service for business logic."""

from typing import Optional
from uuid import UUID

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from diting_web.common.exceptions import ResourceNotFoundError
from diting_web.common.logging import get_logger
from diting_web.common.response import PaginatedResponse
from diting_web.models.evaluator import Evaluator
from diting_web.schemas.evaluator import EvaluatorCreate, EvaluatorResponse, EvaluatorUpdate
from diting_web.services.metric_service import MetricService

logger = get_logger(__name__)


class EvaluatorService:
    """Evaluator service for business logic."""

    def __init__(self, db: AsyncSession):
        """Initialize evaluator service.

        Args:
            db: Database session
        """
        self.db = db

    async def create_evaluator(
        self,
        evaluator_data: EvaluatorCreate,
        created_by: UUID,
    ) -> Evaluator:
        """Create a new evaluator.

        Args:
            evaluator_data: Evaluator creation data
            created_by: User ID who creates the evaluator

        Returns:
            Created evaluator

        Raises:
            ResourceNotFoundError: If any metric not found
        """
        metric_service = MetricService(self.db)

        # Verify all metric IDs exist
        for metric_id in evaluator_data.metric_ids:
            await metric_service.get_metric_by_id(metric_id)

        # Create evaluator
        # Use mode="python" to ensure nested Pydantic models are converted to dicts
        evaluator_dict = evaluator_data.model_dump(mode="python")
        evaluator = Evaluator(
            **evaluator_dict,
            created_by=created_by,
        )
        self.db.add(evaluator)
        await self.db.commit()
        await self.db.refresh(evaluator)

        logger.info("Evaluator created", evaluator_id=str(evaluator.id), name=evaluator.name)
        return evaluator

    async def get_evaluators_list(
        self,
        offset: int = 0,
        limit: int = 20,
    ) -> PaginatedResponse[EvaluatorResponse]:
        """Get paginated list of evaluators.

        Args:
            offset: Pagination offset
            limit: Pagination limit

        Returns:
            Paginated response with evaluators
        """
        # Build query
        query = select(Evaluator)

        # Get total count
        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar() or 0

        # Get paginated items
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        items = result.scalars().all()

        # Calculate pagination info
        page = (offset // limit) + 1 if limit > 0 else 1
        page_size = limit

        # Create response
        return PaginatedResponse.create(
            items=[EvaluatorResponse.model_validate(item).model_dump(mode="json") for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_evaluator_by_id(
        self,
        evaluator_id: UUID,
    ) -> Evaluator:
        """Get evaluator by ID.

        Args:
            evaluator_id: Evaluator ID

        Returns:
            Evaluator

        Raises:
            ResourceNotFoundError: If evaluator not found
        """
        result = await self.db.execute(select(Evaluator).where(Evaluator.id == evaluator_id))
        evaluator = result.scalar_one_or_none()

        if evaluator is None:
            raise ResourceNotFoundError(
                "Evaluator", str(evaluator_id), status_code=status.HTTP_404_NOT_FOUND
            )

        return evaluator

    async def update_evaluator(
        self,
        evaluator_id: UUID,
        evaluator_data: EvaluatorUpdate,
    ) -> Evaluator:
        """Update evaluator.

        Args:
            evaluator_id: Evaluator ID
            evaluator_data: Update data

        Returns:
            Updated evaluator

        Raises:
            ResourceNotFoundError: If evaluator or any metric not found
        """
        # Get evaluator
        evaluator = await self.get_evaluator_by_id(evaluator_id)

        # Verify metric IDs if provided
        # Use mode="python" to ensure nested Pydantic models are converted to dicts
        update_data = evaluator_data.model_dump(exclude_unset=True, mode="python")
        if "metric_ids" in update_data:
            metric_service = MetricService(self.db)
            for metric_id in update_data["metric_ids"]:
                await metric_service.get_metric_by_id(metric_id)

        # Update fields
        for field, value in update_data.items():
            setattr(evaluator, field, value)

        await self.db.commit()
        await self.db.refresh(evaluator)

        logger.info("Evaluator updated", evaluator_id=str(evaluator.id))
        return evaluator

    async def delete_evaluator(
        self,
        evaluator_id: UUID,
    ) -> None:
        """Delete evaluator.

        Args:
            evaluator_id: Evaluator ID

        Raises:
            ResourceNotFoundError: If evaluator not found
        """
        # Get evaluator
        evaluator = await self.get_evaluator_by_id(evaluator_id)

        # TODO: Check if evaluator is being used by running tasks

        # Delete evaluator
        await self.db.delete(evaluator)
        await self.db.commit()

        logger.info("Evaluator deleted", evaluator_id=str(evaluator_id))
