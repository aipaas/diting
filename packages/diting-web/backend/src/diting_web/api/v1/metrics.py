"""Metrics API (评估维度管理 - Simplified)."""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status

from diting_web.auth import get_current_user
from diting_web.common.response import success_response
from diting_web.dependencies import PaginationParams, get_metric_service
from diting_web.models.metric import MetricTypeEnum
from diting_web.models.user import User
from diting_web.schemas.metric import MetricCreate, MetricResponse, MetricUpdate
from diting_web.services import MetricService

router = APIRouter(prefix="/metrics")


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_metric(
    metric_data: MetricCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MetricService, Depends(get_metric_service)],
) -> dict:
    """Create a new custom metric (Simplified: user-level with is_global support)."""
    metric = await service.create_metric(metric_data, created_by=current_user.id)
    return success_response(
        data=MetricResponse.model_validate(metric).model_dump(),
        code=201,
    )


@router.get("")
async def list_metrics(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MetricService, Depends(get_metric_service)],
    pagination: Annotated[PaginationParams, Depends()],
    metric_type: Optional[MetricTypeEnum] = None,
) -> dict:
    """Get metrics list (global metrics + user custom metrics)."""
    paginated_data = await service.get_metrics_list(
        user_id=current_user.id,
        is_admin=current_user.is_admin,
        metric_type=metric_type,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    return success_response(data=paginated_data.model_dump())


@router.get("/{metric_id}")
async def get_metric(
    metric_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MetricService, Depends(get_metric_service)],
) -> dict:
    """Get metric details (verify access for custom metrics)."""
    metric = await service.get_metric_by_id(
        metric_id,
        user_id=current_user.id,
        is_admin=current_user.is_admin,
    )
    return success_response(data=MetricResponse.model_validate(metric).model_dump())


@router.put("/{metric_id}")
async def update_metric(
    metric_id: UUID,
    metric_data: MetricUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MetricService, Depends(get_metric_service)],
) -> dict:
    """Update metric (only custom metrics owned by user or global metrics for admin)."""
    metric = await service.update_metric(
        metric_id,
        metric_data,
        user_id=current_user.id,
        is_admin=current_user.is_admin,
    )
    return success_response(data=MetricResponse.model_validate(metric).model_dump())


@router.delete("/{metric_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_metric(
    metric_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MetricService, Depends(get_metric_service)],
) -> None:
    """Delete metric (only custom metrics owned by user, global metrics cannot be deleted)."""
    await service.delete_metric(
        metric_id,
        user_id=current_user.id,
        is_admin=current_user.is_admin,
    )
