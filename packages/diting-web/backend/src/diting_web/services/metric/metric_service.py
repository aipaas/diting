"""Metric service for business logic - Simplified."""

from typing import Optional
from uuid import UUID

from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from diting_web.common.exceptions import ResourceConflictError, ResourceNotFoundError, PermissionDeniedError
from diting_web.common.logging import get_logger
from diting_web.common.response import PaginatedResponse
from diting_web.models.evaluator import Evaluator
from diting_web.models.metric import Metric, MetricTypeEnum
from diting_web.schemas.metric import MetricCreate, MetricResponse, MetricUpdate

logger = get_logger(__name__)


class MetricService:
    """Metric service for business logic - Simplified."""

    def __init__(self, db: AsyncSession):
        """Initialize metric service.

        Args:
            db: Database session
        """
        self.db = db

    async def create_metric(
        self, 
        metric_data: MetricCreate, 
        created_by: UUID
    ) -> Metric:
        """Create a new custom metric (自定义维度) for the user.

        Args:
            metric_data: Metric creation data (name, description, prompt)
            created_by: User ID who creates this metric

        Returns:
            Created metric

        Raises:
            ResourceConflictError: If metric name already exists
        """
        # Check if metric name already exists (for user's custom metrics)
        existing_metric = await self.db.execute(
            select(Metric).where(
                Metric.name == metric_data.name,
                Metric.is_global == False,
                Metric.created_by == created_by
            )
        )
        if existing_metric.scalar_one_or_none():
            raise ResourceConflictError(
                f"Metric with name '{metric_data.name}' already exists"
            )

        # Create custom metric
        # User-created metrics require LLM to execute evaluation prompts
        metric = Metric(
            name=metric_data.name,
            description=metric_data.description,
            prompt=metric_data.prompt,
            is_global=False,  # User-created metrics are not global
            llm_required=True,  # Custom metrics require LLM
            created_by=created_by,
            # Other boolean fields use database defaults
        )
        self.db.add(metric)
        await self.db.commit()
        await self.db.refresh(metric)

        logger.info("Custom metric created", metric_id=str(metric.id), name=metric.name)
        return metric

    async def get_metrics_list(
        self,
        user_id: UUID,
        is_admin: bool = False,
        offset: int = 0,
        limit: int = 20,
        metric_type: Optional[MetricTypeEnum] = None,
    ) -> PaginatedResponse[MetricResponse]:
        """Get metrics list with pagination and filters.

        Permission model:
        - Global metrics (is_global=true): Visible to all users
        - Custom metrics (is_global=false): Only visible to creator and admins

        Args:
            user_id: User ID
            is_admin: If True, can see all metrics
            offset: Pagination offset
            limit: Pagination limit
            metric_type: Filter by metric type (optional)

        Returns:
            Paginated response with metrics
        """
        # Build query based on user permissions
        # Load creator info for display purposes
        if is_admin:
            # Admins can see all metrics
            query = select(Metric).options(selectinload(Metric.creator))
        else:
            # Regular users can see: global metrics + their own custom metrics
            query = select(Metric).options(selectinload(Metric.creator)).where(
                or_(
                    Metric.is_global == True,  # Global system metrics
                    Metric.created_by == user_id  # User's own custom metrics
                )
            )

        # Apply metric_type filter if specified
        if metric_type is not None:
            query = query.where(Metric.type == metric_type)

        # Order by creation date (newest first)
        # This ensures user-created metrics appear at the top when they're newly created
        query = query.order_by(Metric.created_at.desc())

        # Count total
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar() or 0

        # Paginate
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return PaginatedResponse.create(
            items=[MetricResponse.model_validate(item) for item in items],
            total=total,
            page=offset // limit + 1,
            page_size=limit,
        )

    async def get_metric_by_id(
        self, 
        metric_id: UUID, 
        user_id: UUID,
        is_admin: bool = False
    ) -> Metric:
        """Get metric details by ID (with access control).

        Permission model:
        - Global metrics: Accessible to all users
        - Custom metrics: Only accessible to creator and admins

        Args:
            metric_id: Metric ID
            user_id: User ID (for permission check)
            is_admin: If True, can access all metrics

        Returns:
            Metric

        Raises:
            ResourceNotFoundError: If metric not found or no access
        """
        result = await self.db.execute(
            select(Metric).options(selectinload(Metric.creator)).where(Metric.id == metric_id)
        )
        metric = result.scalar_one_or_none()
        
        if metric is None:
            raise ResourceNotFoundError("Metric", str(metric_id))
        
        # Access control
        if metric.is_global:
            # Global metrics are accessible to all
            return metric
        else:
            # Custom metrics: only creator or admin can access
            if metric.created_by == user_id or is_admin:
                return metric
            else:
                raise ResourceNotFoundError("Metric", str(metric_id))

    async def update_metric(
        self, 
        metric_id: UUID, 
        metric_data: MetricUpdate,
        user_id: UUID,
        is_admin: bool = False
    ) -> Metric:
        """Update metric.

        Permission model:
        - Global metrics: Only admins can update
        - Custom metrics: Only creator or admin can update

        Args:
            metric_id: Metric ID
            metric_data: Update data
            user_id: User ID (for permission check)
            is_admin: If True, can update all metrics

        Returns:
            Updated metric

        Raises:
            ResourceNotFoundError: If metric not found or no access
            PermissionDeniedError: If user doesn't have permission to update
        """
        metric = await self.get_metric_by_id(metric_id, user_id, is_admin)

        # Permission check
        if metric.is_global:
            # Only admins can update global metrics
            if not is_admin:
                raise PermissionDeniedError("Only administrators can modify system built-in metrics")
        else:
            # Only creator or admin can update custom metrics
            if metric.created_by != user_id and not is_admin:
                raise PermissionDeniedError("You don't have permission to update this metric")

        # Update fields
        update_data = metric_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(metric, field, value)

        await self.db.commit()
        await self.db.refresh(metric)

        logger.info("Metric updated", metric_id=str(metric.id))
        return metric

    async def delete_metric(
        self, 
        metric_id: UUID, 
        user_id: UUID,
        is_admin: bool = False
    ) -> None:
        """Delete metric.

        Permission model:
        - Global metrics: Cannot be deleted
        - Custom metrics: Only creator or admin can delete

        Args:
            metric_id: Metric ID
            user_id: User ID (for permission check)
            is_admin: If True, can delete custom metrics

        Raises:
            ResourceNotFoundError: If metric not found or no access
            ResourceConflictError: If metric is global or referenced by evaluators
            PermissionDeniedError: If user doesn't have permission to delete
        """
        metric = await self.get_metric_by_id(metric_id, user_id, is_admin)

        # Cannot delete global metrics
        if metric.is_global:
            raise ResourceConflictError("System built-in metrics cannot be deleted")

        # Permission check for custom metrics
        if metric.created_by != user_id and not is_admin:
            raise PermissionDeniedError("You don't have permission to delete this metric")

        # Check if the metric is referenced by any evaluators
        referenced_evaluators_result = await self.db.execute(
            select(Evaluator).where(Evaluator.metric_ids.contains([metric_id]))
        )
        if referenced_evaluators_result.scalars().first():
            raise ResourceConflictError(
                "Metric is referenced by one or more evaluators and cannot be deleted"
            )

        await self.db.delete(metric)
        await self.db.commit()

        logger.info("Metric deleted", metric_id=str(metric_id), user_id=str(user_id))
