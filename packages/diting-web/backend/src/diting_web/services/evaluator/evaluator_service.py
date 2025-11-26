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
        is_admin: bool = False,
    ) -> Evaluator:
        """Create a new evaluator (user-level).

        Args:
            evaluator_data: Evaluator creation data
            created_by: User ID who creates the evaluator
            is_admin: Whether user is admin

        Returns:
            Created evaluator

        Raises:
            ResourceNotFoundError: If any metric not found
        """
        from diting_web.services.metric.metric_service import MetricService
        
        metric_service = MetricService(self.db)

        # Verify all metric IDs exist
        for metric_id in evaluator_data.metric_ids:
            await metric_service.get_metric_by_id(metric_id, user_id=created_by, is_admin=is_admin)

        # Create evaluator (user-level)
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
        user_id: UUID,
        is_admin: bool,
        offset: int = 0,
        limit: int = 20,
    ) -> PaginatedResponse[EvaluatorResponse]:
        """Get paginated list of evaluators (filtered by user access).

        Args:
            user_id: User ID for filtering (non-admin users see only their evaluators)
            is_admin: Whether user is admin (admins see all evaluators)
            offset: Pagination offset
            limit: Pagination limit

        Returns:
            Paginated response with evaluators
        """
        # Build query with user-based access control
        query = select(Evaluator)
        
        # Apply user-based filtering: non-admin users only see their own evaluators
        if not is_admin:
            query = query.where(Evaluator.created_by == user_id)
        
        query = query.order_by(Evaluator.created_at.desc())

        # Get total count
        count_query = select(func.count(Evaluator.id))
        if not is_admin:
            count_query = count_query.where(Evaluator.created_by == user_id)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Get paginated items with creator info
        from sqlalchemy.orm import selectinload
        
        query = query.options(selectinload(Evaluator.creator))
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        items = result.scalars().all()

        # Calculate pagination info
        page = (offset // limit) + 1 if limit > 0 else 1
        page_size = limit

        # Create response with creator username
        response_items = []
        for item in items:
            item_dict = EvaluatorResponse.model_validate(item).model_dump(mode="json")
            if item.creator:
                item_dict["created_by_username"] = item.creator.username
            response_items.append(item_dict)

        return PaginatedResponse.create(
            items=response_items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_evaluator_by_id(
        self,
        evaluator_id: UUID,
        user_id: UUID,
        is_admin: bool,
    ) -> Evaluator:
        """Get evaluator by ID (with user-level access control).

        Args:
            evaluator_id: Evaluator ID
            user_id: User ID for access control
            is_admin: Whether user is admin

        Returns:
            Evaluator

        Raises:
            ResourceNotFoundError: If evaluator not found or no access
        """
        from sqlalchemy.orm import selectinload
        
        query = select(Evaluator).where(Evaluator.id == evaluator_id)
        
        # Apply user-based access control
        if not is_admin:
            query = query.where(Evaluator.created_by == user_id)
        
        # Load creator relationship
        query = query.options(selectinload(Evaluator.creator))
        
        result = await self.db.execute(query)
        evaluator = result.scalar_one_or_none()

        if evaluator is None:
            raise ResourceNotFoundError("Evaluator", str(evaluator_id))

        return evaluator

    async def update_evaluator(
        self,
        evaluator_id: UUID,
        evaluator_data: EvaluatorUpdate,
        user_id: UUID,
        is_admin: bool,
    ) -> Evaluator:
        """Update evaluator.

        Args:
            evaluator_id: Evaluator ID
            evaluator_data: Update data
            user_id: User ID for access control
            is_admin: Whether user is admin

        Returns:
            Updated evaluator

        Raises:
            ResourceNotFoundError: If evaluator or any metric not found or no access
        """
        from diting_web.services.metric.metric_service import MetricService
        
        # Get evaluator (with access control)
        evaluator = await self.get_evaluator_by_id(evaluator_id, user_id=user_id, is_admin=is_admin)

        # Verify metric IDs if provided
        # Use mode="python" to ensure nested Pydantic models are converted to dicts
        update_data = evaluator_data.model_dump(exclude_unset=True, mode="python")
        if "metric_ids" in update_data:
            metric_service = MetricService(self.db)
            for metric_id in update_data["metric_ids"]:
                await metric_service.get_metric_by_id(metric_id, user_id=user_id, is_admin=is_admin)

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
        user_id: UUID,
        is_admin: bool,
    ) -> None:
        """Delete evaluator.

        Args:
            evaluator_id: Evaluator ID
            user_id: User ID for access control
            is_admin: Whether user is admin

        Raises:
            ResourceNotFoundError: If evaluator not found or no access
        """
        # Get evaluator (with access control)
        evaluator = await self.get_evaluator_by_id(evaluator_id, user_id=user_id, is_admin=is_admin)

        # TODO: Check if evaluator is being used by running tasks

        # Delete evaluator
        await self.db.delete(evaluator)
        await self.db.commit()

        logger.info("Evaluator deleted", evaluator_id=str(evaluator_id))

