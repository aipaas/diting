"""Prompts API (提示词仓库)."""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from diting_web.auth import get_current_user
from diting_web.common.response import success_response
from diting_web.dependencies import PaginationParams
from diting_web.db.session import get_db
from diting_web.models.user import User
from diting_web.models.prompt import PromptCategoryEnum
from diting_web.schemas.prompt import PromptCreate, PromptResponse, PromptUpdate
from diting_web.services import PromptService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/prompts")


def get_prompt_service(db: AsyncSession = Depends(get_db)) -> PromptService:
    """Get prompt service dependency."""
    return PromptService(db)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_prompt(
    prompt_data: PromptCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PromptService, Depends(get_prompt_service)],
) -> dict:
    """Create a new prompt."""
    prompt = await service.create_prompt(prompt_data)
    return success_response(
        data=PromptResponse.model_validate(prompt).model_dump(),
        code=201,
    )


@router.get("")
async def list_prompts(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PromptService, Depends(get_prompt_service)],
    pagination: Annotated[PaginationParams, Depends()],
    category: Optional[PromptCategoryEnum] = None,
    search: Optional[str] = Query(None, description="搜索关键词"),
    favorite_only: bool = Query(False, description="仅显示收藏"),
) -> dict:
    """Get prompts list."""
    paginated_data = await service.get_prompts_list(
        category=category,
        search=search,
        favorite_only=favorite_only,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    return success_response(data=paginated_data.model_dump())


@router.get("/statistics")
async def get_statistics(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PromptService, Depends(get_prompt_service)],
) -> dict:
    """Get prompt statistics."""
    stats = await service.get_statistics()
    return success_response(data=stats.model_dump())


@router.get("/{prompt_id}")
async def get_prompt(
    prompt_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PromptService, Depends(get_prompt_service)],
) -> dict:
    """Get prompt details."""
    prompt = await service.get_prompt_by_id(prompt_id)
    return success_response(data=PromptResponse.model_validate(prompt).model_dump())


@router.put("/{prompt_id}")
async def update_prompt(
    prompt_id: UUID,
    prompt_data: PromptUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PromptService, Depends(get_prompt_service)],
) -> dict:
    """Update prompt."""
    prompt = await service.update_prompt(prompt_id, prompt_data)
    return success_response(data=PromptResponse.model_validate(prompt).model_dump())


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    prompt_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PromptService, Depends(get_prompt_service)],
) -> None:
    """Delete prompt."""
    await service.delete_prompt(prompt_id)


@router.post("/{prompt_id}/toggle-favorite")
async def toggle_favorite(
    prompt_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PromptService, Depends(get_prompt_service)],
) -> dict:
    """Toggle favorite status of a prompt."""
    prompt = await service.toggle_favorite(prompt_id)
    return success_response(data=PromptResponse.model_validate(prompt).model_dump())


@router.post("/{prompt_id}/increment-usage")
async def increment_usage(
    prompt_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PromptService, Depends(get_prompt_service)],
) -> dict:
    """Increment usage count of a prompt."""
    prompt = await service.increment_usage_count(prompt_id)
    return success_response(data=PromptResponse.model_validate(prompt).model_dump())

