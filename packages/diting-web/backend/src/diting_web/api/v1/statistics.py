"""Statistics API."""

from typing import Annotated

from fastapi import APIRouter, Depends

from diting_web.auth import get_current_user
from diting_web.common.response import success_response
from diting_web.dependencies import get_statistics_service
from diting_web.models.user import User
from diting_web.services import StatisticsService

router = APIRouter(prefix="/statistics")


@router.get("/dashboard")
async def get_dashboard_statistics(
    service: Annotated[StatisticsService, Depends(get_statistics_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Get dashboard statistics."""
    statistics = await service.get_dashboard_statistics(current_user.id)
    return success_response(data=statistics.model_dump())
