"""Metric service for business logic."""

from typing import Optional
from uuid import UUID

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from diting_web.common.exceptions import ResourceConflictError, ResourceNotFoundError
from diting_web.common.logging import get_logger
from diting_web.common.response import PaginatedResponse
from diting_web.models.evaluator import Evaluator
from diting_web.models.metric import Metric, MetricTypeEnum
from diting_web.schemas.metric import MetricCreate, MetricResponse, MetricUpdate

logger = get_logger(__name__)


class MetricService:
    """Metric service for business logic."""

    def __init__(self, db: AsyncSession):
        """Initialize metric service.

        Args:
            db: Database session
        """
        self.db = db

    async def create_metric(self, metric_data: MetricCreate) -> Metric:
        """Create a new custom metric (自定义维度).

        Args:
            metric_data: Metric creation data (仅需三要素：name, description, prompt)

        Returns:
            Created metric

        Raises:
            ResourceConflictError: If metric name already exists
        """
        # Check if metric name already exists
        existing_metric = await self.db.execute(
            select(Metric).where(Metric.name == metric_data.name)
        )
        if existing_metric.scalar_one_or_none():
            raise ResourceConflictError(
                f"Metric with name '{metric_data.name}' already exists"
            )

        # 创建自定义维度，type 自动设置为 CUSTOM
        # 自定义维度需要 LLM 来执行评估提示词，因此 llm_required=True
        metric = Metric(
            name=metric_data.name,
            description=metric_data.description,
            prompt=metric_data.prompt,
            type=MetricTypeEnum.CUSTOM,  # 用户创建的都是自定义维度
            llm_required=True,  # 自定义维度需要 LLM 模型
            # 其他布尔字段使用数据库默认值
        )
        self.db.add(metric)
        await self.db.commit()
        await self.db.refresh(metric)

        logger.info("Custom metric created", metric_id=str(metric.id), name=metric.name)
        return metric

    async def get_metrics_list(
        self,
        offset: int,
        limit: int,
        metric_type: Optional[MetricTypeEnum] = None,
    ) -> PaginatedResponse[MetricResponse]:
        """Get metrics list with pagination and filters.

        Args:
            offset: Pagination offset
            limit: Pagination limit
            metric_type: Filter by metric type (builtin/custom)

        Returns:
            Paginated response with metrics
        """
        query = select(Metric)

        if metric_type:
            query = query.where(Metric.type == metric_type)

        query = query.order_by(Metric.created_at.desc())

        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar() or 0

        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return PaginatedResponse.create(
            items=[MetricResponse.model_validate(item) for item in items],
            total=total,
            page=offset // limit + 1,
            page_size=limit,
        )

    async def get_metric_by_id(self, metric_id: UUID) -> Metric:
        """Get metric details by ID.

        Args:
            metric_id: Metric ID

        Returns:
            Metric

        Raises:
            ResourceNotFoundError: If metric not found
        """
        result = await self.db.execute(select(Metric).where(Metric.id == metric_id))
        metric = result.scalar_one_or_none()
        if metric is None:
            raise ResourceNotFoundError("Metric", str(metric_id))
        return metric

    async def update_metric(
        self, metric_id: UUID, metric_data: MetricUpdate
    ) -> Metric:
        """Update metric.

        Args:
            metric_id: Metric ID
            metric_data: Update data

        Returns:
            Updated metric

        Raises:
            ResourceNotFoundError: If metric not found
            ResourceConflictError: If trying to update builtin metric
        """
        metric = await self.get_metric_by_id(metric_id)

        if metric.type == MetricTypeEnum.BUILTIN:
            raise ResourceConflictError("Built-in metrics cannot be modified")

        update_data = metric_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(metric, field, value)

        await self.db.commit()
        await self.db.refresh(metric)

        logger.info("Metric updated", metric_id=str(metric.id))
        return metric

    async def delete_metric(self, metric_id: UUID) -> None:
        """Delete metric.

        Args:
            metric_id: Metric ID

        Raises:
            ResourceNotFoundError: If metric not found
            ResourceConflictError: If metric is builtin or referenced by evaluators
        """
        metric = await self.get_metric_by_id(metric_id)

        if metric.type == MetricTypeEnum.BUILTIN:
            raise ResourceConflictError("Built-in metrics cannot be deleted")

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

        logger.info("Metric deleted", metric_id=str(metric_id))
