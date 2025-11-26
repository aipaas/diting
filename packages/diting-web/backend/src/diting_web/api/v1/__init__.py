"""API v1 module - Simplified."""

from fastapi import APIRouter

from . import (
    auth,
    datasets,
    evaluators,
    health,
    metrics,
    models,
    monitoring,
    prompts,
    statistics,
    tasks,
    users,
)

router = APIRouter(prefix="/api/v1")

# Include all routers
router.include_router(health.router, tags=["health"])
router.include_router(auth.router, tags=["auth"])

# Core routers
router.include_router(users.router, tags=["users"])

# Resource routers
router.include_router(datasets.router, tags=["datasets"])
router.include_router(metrics.router, tags=["metrics"])
router.include_router(models.router, tags=["models"])
router.include_router(evaluators.router, tags=["evaluators"])
router.include_router(tasks.router, tags=["tasks"])
router.include_router(statistics.router, tags=["statistics"])
router.include_router(monitoring.router, tags=["monitoring"])
router.include_router(prompts.router, tags=["prompts"])

__all__ = ["router"]

