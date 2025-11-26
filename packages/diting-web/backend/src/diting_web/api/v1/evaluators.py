"""Evaluators API (评估器管理 - Simplified)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from diting_web.auth import get_current_user
from diting_web.common.response import success_response
from diting_web.dependencies import PaginationParams, get_evaluator_service
from diting_web.models.user import User
from diting_web.schemas.evaluator import EvaluatorCreate, EvaluatorResponse, EvaluatorUpdate
from diting_web.services import EvaluatorService

router = APIRouter(prefix="/evaluators")


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_evaluator(
    evaluator_data: EvaluatorCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[EvaluatorService, Depends(get_evaluator_service)],
) -> dict:
    """Create a new evaluator (Simplified: user-level)."""
    evaluator = await service.create_evaluator(evaluator_data, current_user.id, is_admin=current_user.is_admin)
    evaluator_dict = EvaluatorResponse.model_validate(evaluator).model_dump(mode="json")
    evaluator_dict["created_by_username"] = current_user.username
    return success_response(
        data=evaluator_dict,
        code=201,
    )


@router.get("")
async def list_evaluators(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[EvaluatorService, Depends(get_evaluator_service)],
    pagination: Annotated[PaginationParams, Depends()],
) -> dict:
    """Get evaluators list (filtered by current user or all for admin)."""
    paginated_data = await service.get_evaluators_list(
        user_id=current_user.id,
        is_admin=current_user.is_admin,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    return success_response(data=paginated_data.model_dump())


@router.get("/{evaluator_id}")
async def get_evaluator(
    evaluator_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[EvaluatorService, Depends(get_evaluator_service)],
) -> dict:
    """Get evaluator details (verify user access)."""
    evaluator = await service.get_evaluator_by_id(evaluator_id, user_id=current_user.id, is_admin=current_user.is_admin)
    evaluator_dict = EvaluatorResponse.model_validate(evaluator).model_dump(mode="json")
    if evaluator.creator:
        evaluator_dict["created_by_username"] = evaluator.creator.username
    return success_response(data=evaluator_dict)


@router.put("/{evaluator_id}")
async def update_evaluator(
    evaluator_id: UUID,
    evaluator_data: EvaluatorUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[EvaluatorService, Depends(get_evaluator_service)],
) -> dict:
    """Update evaluator (require ownership or admin)."""
    evaluator = await service.update_evaluator(evaluator_id, evaluator_data, user_id=current_user.id, is_admin=current_user.is_admin)
    # Refresh to get creator relationship
    await service.db.refresh(evaluator, ["creator"])
    evaluator_dict = EvaluatorResponse.model_validate(evaluator).model_dump(mode="json")
    if evaluator.creator:
        evaluator_dict["created_by_username"] = evaluator.creator.username
    return success_response(data=evaluator_dict)


@router.delete("/{evaluator_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evaluator(
    evaluator_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[EvaluatorService, Depends(get_evaluator_service)],
) -> None:
    """Delete evaluator (require ownership or admin)."""
    await service.delete_evaluator(evaluator_id, user_id=current_user.id, is_admin=current_user.is_admin)
