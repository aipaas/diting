"""FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from diting_web.db.session import get_db


class PaginationParams(BaseModel):
    """Pagination parameters."""

    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Get limit for database query."""
        return self.page_size


# Service dependencies
def get_metric_service(db: Annotated[AsyncSession, Depends(get_db)]):
    """Get metric service instance.

    Args:
        db: Database session

    Returns:
        MetricService instance
    """
    from diting_web.services import MetricService

    return MetricService(db)


def get_evaluator_service(db: Annotated[AsyncSession, Depends(get_db)]):
    """Get evaluator service instance.

    Args:
        db: Database session

    Returns:
        EvaluatorService instance
    """
    from diting_web.services import EvaluatorService

    return EvaluatorService(db)


def get_dataset_service(db: Annotated[AsyncSession, Depends(get_db)]):
    """Get dataset service instance.

    Args:
        db: Database session

    Returns:
        DatasetService instance
    """
    from diting_web.services import DatasetService

    return DatasetService(db)


def get_statistics_service(db: Annotated[AsyncSession, Depends(get_db)]):
    """Get statistics service instance.

    Args:
        db: Database session

    Returns:
        StatisticsService instance
    """
    from diting_web.services import StatisticsService

    return StatisticsService(db)


def get_task_service(db: Annotated[AsyncSession, Depends(get_db)]):
    """Get task service instance.

    Args:
        db: Database session

    Returns:
        TaskService instance
    """
    from diting_web.services import TaskService

    return TaskService(db)

