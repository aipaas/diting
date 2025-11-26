"""Monitoring and statistics API."""

from datetime import date, datetime, timedelta
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from diting_web.auth import get_current_user
from diting_web.common.response import success_response
from diting_web.db.session import get_db
from diting_web.models.user import User
from diting_web.models.task import Task, TaskStatus, TaskType

router = APIRouter(prefix="/monitoring")


@router.get("/token-usage")
async def get_token_usage_statistics(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    start_date: date = Query(..., description="Start date (inclusive)"),
    end_date: date = Query(..., description="End date (inclusive)"),
    task_type: Optional[TaskType] = Query(None, description="Filter by task type"),
) -> dict:
    """Get token usage statistics for a date range.
    
    Returns aggregated token usage and cost statistics grouped by date.
    
    Args:
        start_date: Start date for the statistics
        end_date: End date for the statistics
        task_type: Optional filter by task type
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        Token usage statistics grouped by date
    
    Example response:
        {
            "success": true,
            "data": {
                "total_tokens": 150000,
                "total_cost": 4.50,
                "daily_stats": [
                    {
                        "date": "2025-10-24",
                        "total_tokens": 50000,
                        "total_cost": 1.50,
                        "task_count": 45
                    },
                    ...
                ]
            }
        }
    """
    # Convert dates to datetime for comparison
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    # Build query
    query = (
        select(
            func.date(Task.created_at).label("date"),
            func.sum(Task.total_tokens).label("total_tokens"),
            func.sum(Task.total_cost).label("total_cost"),
            func.count(Task.id).label("task_count"),
        )
        .where(
            Task.created_at.between(start_datetime, end_datetime),
            Task.status == TaskStatus.COMPLETED,
        )
        .group_by(func.date(Task.created_at))
        .order_by(func.date(Task.created_at))
    )

    # Add task type filter if specified
    if task_type:
        query = query.where(Task.task_type == task_type)

    # Execute query
    result = await db.execute(query)
    daily_stats = result.all()

    # Calculate totals
    total_tokens = sum(row.total_tokens or 0 for row in daily_stats)
    total_cost = sum(float(row.total_cost or 0) for row in daily_stats)
    total_tasks = sum(row.task_count for row in daily_stats)

    # Format response
    return success_response(
        data={
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "total_tasks": total_tasks,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "daily_stats": [
                {
                    "date": str(row.date),
                    "total_tokens": row.total_tokens or 0,
                    "total_cost": float(row.total_cost or 0),
                    "task_count": row.task_count,
                }
                for row in daily_stats
            ],
        }
    )


@router.get("/cost-summary")
async def get_cost_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    days: int = Query(30, description="Number of days to look back"),
) -> dict:
    """Get cost summary for the last N days.
    
    Provides a quick overview of token usage and costs.
    
    Args:
        days: Number of days to include in the summary (default: 30)
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        Cost summary with breakdown by task type
    
    Example response:
        {
            "success": true,
            "data": {
                "period_days": 30,
                "total_tokens": 500000,
                "total_cost": 15.00,
                "total_tasks": 250,
                "by_task_type": {
                    "evaluation": {"tokens": 200000, "cost": 6.00, "count": 100},
                    "synthesis": {"tokens": 150000, "cost": 4.50, "count": 75},
                    "batch_evaluation": {"tokens": 150000, "cost": 4.50, "count": 75}
                },
                "average_cost_per_task": 0.06
            }
        }
    """
    # Calculate start date
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Query for totals
    totals_query = select(
        func.sum(Task.total_tokens).label("total_tokens"),
        func.sum(Task.total_cost).label("total_cost"),
        func.count(Task.id).label("total_tasks"),
    ).where(
        Task.created_at.between(start_date, end_date),
        Task.status == TaskStatus.COMPLETED,
    )

    totals_result = await db.execute(totals_query)
    totals = totals_result.one()

    # Query for breakdown by task type
    by_type_query = (
        select(
            Task.task_type,
            func.sum(Task.total_tokens).label("total_tokens"),
            func.sum(Task.total_cost).label("total_cost"),
            func.count(Task.id).label("task_count"),
        )
        .where(
            Task.created_at.between(start_date, end_date),
            Task.status == TaskStatus.COMPLETED,
        )
        .group_by(Task.task_type)
    )

    by_type_result = await db.execute(by_type_query)
    by_type_stats = by_type_result.all()

    # Calculate averages
    total_tasks = totals.total_tasks or 0
    total_cost = float(totals.total_cost or 0)
    avg_cost_per_task = total_cost / total_tasks if total_tasks > 0 else 0

    # Format breakdown
    by_task_type = {}
    for row in by_type_stats:
        by_task_type[row.task_type.value] = {
            "tokens": row.total_tokens or 0,
            "cost": float(row.total_cost or 0),
            "count": row.task_count,
        }

    return success_response(
        data={
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_tokens": totals.total_tokens or 0,
            "total_cost": total_cost,
            "total_tasks": total_tasks,
            "by_task_type": by_task_type,
            "average_cost_per_task": round(avg_cost_per_task, 4),
        }
    )


@router.get("/task-metrics")
async def get_task_metrics(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    hours: int = Query(24, description="Number of hours to look back"),
) -> dict:
    """Get task execution metrics.
    
    Provides metrics about task execution including success rate,
    average duration, and status breakdown.
    
    Args:
        hours: Number of hours to include in metrics (default: 24)
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        Task execution metrics
    
    Example response:
        {
            "success": true,
            "data": {
                "period_hours": 24,
                "total_tasks": 100,
                "completed": 85,
                "failed": 10,
                "running": 3,
                "pending": 2,
                "success_rate": 0.85,
                "average_tokens_per_task": 2000,
                "average_cost_per_task": 0.06
            }
        }
    """
    # Calculate start time
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)

    # Query for status breakdown
    status_query = (
        select(
            Task.status,
            func.count(Task.id).label("count"),
        )
        .where(Task.created_at.between(start_time, end_time))
        .group_by(Task.status)
    )

    status_result = await db.execute(status_query)
    status_breakdown = {row.status.value: row.count for row in status_result.all()}

    # Query for averages (completed tasks only)
    averages_query = select(
        func.avg(Task.total_tokens).label("avg_tokens"),
        func.avg(Task.total_cost).label("avg_cost"),
        func.count(Task.id).label("completed_count"),
    ).where(
        Task.created_at.between(start_time, end_time),
        Task.status == TaskStatus.COMPLETED,
    )

    averages_result = await db.execute(averages_query)
    averages = averages_result.one()

    # Calculate metrics
    total_tasks = sum(status_breakdown.values())
    completed = status_breakdown.get("completed", 0)
    success_rate = completed / total_tasks if total_tasks > 0 else 0

    return success_response(
        data={
            "period_hours": hours,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "total_tasks": total_tasks,
            "completed": status_breakdown.get("completed", 0),
            "failed": status_breakdown.get("failed", 0),
            "running": status_breakdown.get("running", 0),
            "pending": status_breakdown.get("pending", 0),
            "cancelled": status_breakdown.get("cancelled", 0),
            "success_rate": round(success_rate, 4),
            "average_tokens_per_task": int(averages.avg_tokens or 0),
            "average_cost_per_task": round(float(averages.avg_cost or 0), 4),
        }
    )


@router.get("/real-time-stats")
async def get_real_time_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Get real-time system statistics.
    
    Provides current system status including running tasks,
    today's statistics, and recent activity.
    
    Args:
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        Real-time system statistics
    """
    # Get current running tasks
    running_query = select(func.count(Task.id)).where(
        Task.status == TaskStatus.RUNNING
    )
    running_result = await db.execute(running_query)
    running_tasks = running_result.scalar() or 0

    # Get today's stats
    today_start = datetime.combine(date.today(), datetime.min.time())
    
    today_query = select(
        func.count(Task.id).label("task_count"),
        func.sum(Task.total_tokens).label("total_tokens"),
        func.sum(Task.total_cost).label("total_cost"),
    ).where(
        Task.created_at >= today_start,
        Task.status == TaskStatus.COMPLETED,
    )

    today_result = await db.execute(today_query)
    today_stats = today_result.one()

    return success_response(
        data={
            "current_time": datetime.utcnow().isoformat(),
            "running_tasks": running_tasks,
            "today": {
                "tasks_completed": today_stats.task_count or 0,
                "tokens_used": today_stats.total_tokens or 0,
                "cost": float(today_stats.total_cost or 0),
            },
        }
    )



