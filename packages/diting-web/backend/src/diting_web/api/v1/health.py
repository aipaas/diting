"""Health check API."""

from datetime import datetime

from fastapi import APIRouter

from diting_web.common.response import success_response
from diting_web.config import settings

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict:
    """Health check endpoint."""
    return success_response(
        data={
            "version": settings.app_version,
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )

