from fastapi import APIRouter
from diting_inspect.routers.cases.api import router as cases_router
from diting_inspect.routers.evaluations.api import router as evaluations_router
from diting_inspect.routers.models.api import router as models_router
from diting_inspect.routers.tools.api import router as tools_router

v1_router = APIRouter(
    prefix="",
)

v1_router.include_router(cases_router)
v1_router.include_router(evaluations_router)
v1_router.include_router(models_router)
v1_router.include_router(tools_router)
