"""Statistics service for business logic."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from diting_web.common.logging import get_logger
from diting_web.models.task import Task, TaskStatus
from diting_web.schemas.task import DashboardStatisticsResponse, TaskResponse

logger = get_logger(__name__)


class StatisticsService:
    """Statistics service for business logic."""

    def __init__(self, db: AsyncSession):
        """Initialize statistics service.

        Args:
            db: Database session
        """
        self.db = db

    async def get_dashboard_statistics(
        self,
        user_id: UUID,
    ) -> DashboardStatisticsResponse:
        """Get dashboard statistics for a user.

        Args:
            user_id: User ID

        Returns:
            Dashboard statistics
        """
        # Total tasks
        total_tasks_result = await self.db.execute(
            select(func.count()).select_from(Task).where(Task.created_by == user_id)
        )
        total_tasks = total_tasks_result.scalar() or 0

        # Completed tasks
        completed_tasks_result = await self.db.execute(
            select(func.count())
            .select_from(Task)
            .where(
                Task.created_by == user_id,
                Task.status == TaskStatus.COMPLETED,
            )
        )
        completed_tasks = completed_tasks_result.scalar() or 0

        # Failed tasks
        failed_tasks_result = await self.db.execute(
            select(func.count())
            .select_from(Task)
            .where(
                Task.created_by == user_id,
                Task.status == TaskStatus.FAILED,
            )
        )
        failed_tasks = failed_tasks_result.scalar() or 0

        # Success rate
        success_rate = completed_tasks / total_tasks if total_tasks > 0 else 0.0

        # Total tokens and cost
        tokens_result = await self.db.execute(
            select(func.sum(Task.total_tokens))
            .select_from(Task)
            .where(Task.created_by == user_id)
        )
        total_tokens = tokens_result.scalar() or 0

        cost_result = await self.db.execute(
            select(func.sum(Task.total_cost)).select_from(Task).where(Task.created_by == user_id)
        )
        total_cost = cost_result.scalar() or Decimal("0.00")

        # Recent tasks
        recent_tasks_result = await self.db.execute(
            select(Task)
            .where(Task.created_by == user_id)
            .order_by(Task.created_at.desc())
            .limit(10)
        )
        recent_tasks = recent_tasks_result.scalars().all()

        # Create response
        statistics = DashboardStatisticsResponse(
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            success_rate=success_rate,
            total_tokens=total_tokens,
            total_cost=total_cost,
            recent_tasks=[TaskResponse.model_validate(task) for task in recent_tasks],
        )

        logger.info("Dashboard statistics retrieved", user_id=str(user_id))
        return statistics
