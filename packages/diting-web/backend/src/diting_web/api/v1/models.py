"""Models API (模型管理 - Simplified)."""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from diting_web.auth import get_current_user
from diting_web.common.response import success_response
from diting_web.dependencies import PaginationParams
from diting_web.db.session import get_db
from diting_web.models.model import ModelTypeEnum
from diting_web.models.user import User
from diting_web.schemas.model import ModelCreate, ModelResponse, ModelUpdate
from diting_web.services import ModelService

router = APIRouter(prefix="/models")


def get_model_service(db: AsyncSession = Depends(get_db)) -> ModelService:
    """Get model service dependency."""
    return ModelService(db)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_model(
    model_data: ModelCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ModelService, Depends(get_model_service)],
) -> dict:
    """Create a new model (Simplified: user-level)."""
    model = await service.create_model(model_data, current_user.id)
    # Mask API key in response
    response_data = ModelResponse.model_validate(model).model_dump()
    response_data["api_key"] = model.mask_api_key()
    return success_response(
        data=response_data,
        code=201,
    )


@router.get("")
async def list_models(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ModelService, Depends(get_model_service)],
    pagination: Annotated[PaginationParams, Depends()],
    model_type: Optional[ModelTypeEnum] = None,
) -> dict:
    """Get models list (filtered by current user or all for admin)."""
    paginated_data = await service.get_models_list(
        user_id=current_user.id,
        is_admin=current_user.is_admin,
        model_type=model_type,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    return success_response(data=paginated_data.model_dump())


@router.get("/{model_id}")
async def get_model(
    model_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ModelService, Depends(get_model_service)],
) -> dict:
    """Get model details (verify user access)."""
    model = await service.get_model_by_id(model_id, user_id=current_user.id, is_admin=current_user.is_admin)
    response_data = ModelResponse.model_validate(model).model_dump()
    response_data["api_key"] = model.mask_api_key()
    return success_response(data=response_data)


@router.put("/{model_id}")
async def update_model(
    model_id: UUID,
    model_data: ModelUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ModelService, Depends(get_model_service)],
) -> dict:
    """Update model (require ownership or admin)."""
    model = await service.update_model(model_id, model_data, user_id=current_user.id, is_admin=current_user.is_admin)
    response_data = ModelResponse.model_validate(model).model_dump()
    response_data["api_key"] = model.mask_api_key()
    return success_response(data=response_data)


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    model_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ModelService, Depends(get_model_service)],
) -> None:
    """Delete model (require ownership or admin)."""
    await service.delete_model(model_id, user_id=current_user.id, is_admin=current_user.is_admin)


@router.post("/{model_id}/set-default")
async def set_default_model(
    model_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ModelService, Depends(get_model_service)],
) -> dict:
    """Set a model as default for its type."""
    model = await service.set_default_model(model_id, user_id=current_user.id, is_admin=current_user.is_admin)
    response_data = ModelResponse.model_validate(model).model_dump()
    response_data["api_key"] = model.mask_api_key()
    return success_response(data=response_data)


@router.post("/{model_id}/test-connection")
async def test_model_connection(
    model_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ModelService, Depends(get_model_service)],
) -> dict:
    """Test model connection by making a simple API call."""
    result = await service.test_model_connection(model_id, user_id=current_user.id, is_admin=current_user.is_admin)
    return success_response(data=result)
