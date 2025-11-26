"""Prompt service for business logic."""

from typing import Optional
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from diting_web.common.exceptions import ResourceConflictError, ResourceNotFoundError
from diting_web.common.logging import get_logger
from diting_web.common.response import PaginatedResponse
from diting_web.models.prompt import Prompt, PromptCategoryEnum
from diting_web.schemas.prompt import (
    PromptCreate,
    PromptResponse,
    PromptStatistics,
    PromptUpdate,
)

logger = get_logger(__name__)


class PromptService:
    """Prompt service for business logic."""

    def __init__(self, db: AsyncSession):
        """Initialize prompt service.

        Args:
            db: Database session
        """
        self.db = db

    async def create_prompt(self, prompt_data: PromptCreate) -> Prompt:
        """Create a new prompt.

        Args:
            prompt_data: Prompt creation data

        Returns:
            Created prompt

        Raises:
            ResourceConflictError: If prompt with same name exists
        """
        # Check if a prompt with same name already exists
        existing_prompt = await self.db.execute(
            select(Prompt).where(Prompt.name == prompt_data.name)
        )
        if existing_prompt.scalar_one_or_none():
            raise ResourceConflictError(
                f"Prompt with name '{prompt_data.name}' already exists"
            )

        # Create prompt
        prompt = Prompt(
            name=prompt_data.name,
            description=prompt_data.description,
            category=prompt_data.category,
            content=prompt_data.content,
            variables=prompt_data.variables or [],
            version=prompt_data.version or "v1.0",
            is_favorite=prompt_data.is_favorite or False,
        )
        self.db.add(prompt)
        await self.db.commit()
        await self.db.refresh(prompt)

        logger.info("Prompt created", prompt_id=str(prompt.id), name=prompt.name)
        return prompt

    async def get_prompts_list(
        self,
        offset: int,
        limit: int,
        category: Optional[PromptCategoryEnum] = None,
        search: Optional[str] = None,
        favorite_only: bool = False,
    ) -> PaginatedResponse[PromptResponse]:
        """Get prompts list with pagination and filters.

        Args:
            offset: Pagination offset
            limit: Pagination limit
            category: Filter by category
            search: Search in name, description, or content
            favorite_only: Filter by favorite status

        Returns:
            Paginated response with prompts
        """
        query = select(Prompt)

        # Apply filters
        if category:
            query = query.where(Prompt.category == category)

        if favorite_only:
            query = query.where(Prompt.is_favorite == True)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Prompt.name.ilike(search_pattern),
                    Prompt.description.ilike(search_pattern),
                    Prompt.content.ilike(search_pattern),
                )
            )

        query = query.order_by(Prompt.is_favorite.desc(), Prompt.usage_count.desc(), Prompt.created_at.desc())

        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar() or 0

        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        items = result.scalars().all()

        response_items = [
            PromptResponse.model_validate(item) for item in items
        ]

        return PaginatedResponse.create(
            items=response_items,
            total=total,
            page=offset // limit + 1,
            page_size=limit,
        )

    async def get_prompt_by_id(self, prompt_id: UUID) -> Prompt:
        """Get prompt details by ID.

        Args:
            prompt_id: Prompt ID

        Returns:
            Prompt

        Raises:
            ResourceNotFoundError: If prompt not found
        """
        result = await self.db.execute(select(Prompt).where(Prompt.id == prompt_id))
        prompt = result.scalar_one_or_none()
        if prompt is None:
            raise ResourceNotFoundError("Prompt", str(prompt_id))
        return prompt

    async def update_prompt(
        self, prompt_id: UUID, prompt_data: PromptUpdate
    ) -> Prompt:
        """Update prompt.

        Args:
            prompt_id: Prompt ID
            prompt_data: Update data

        Returns:
            Updated prompt

        Raises:
            ResourceNotFoundError: If prompt not found
            ResourceConflictError: If new name conflicts with existing prompt
        """
        prompt = await self.get_prompt_by_id(prompt_id)

        # Check name conflict if name is being updated
        if prompt_data.name and prompt_data.name != prompt.name:
            existing_prompt = await self.db.execute(
                select(Prompt).where(
                    Prompt.name == prompt_data.name,
                    Prompt.id != prompt.id,
                )
            )
            if existing_prompt.scalar_one_or_none():
                raise ResourceConflictError(
                    f"Prompt with name '{prompt_data.name}' already exists"
                )

        update_data = prompt_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(prompt, field, value)

        await self.db.commit()
        await self.db.refresh(prompt)

        logger.info("Prompt updated", prompt_id=str(prompt.id), name=prompt.name)
        return prompt

    async def delete_prompt(self, prompt_id: UUID) -> None:
        """Delete prompt.

        Args:
            prompt_id: Prompt ID

        Raises:
            ResourceNotFoundError: If prompt not found
        """
        prompt = await self.get_prompt_by_id(prompt_id)

        await self.db.delete(prompt)
        await self.db.commit()

        logger.info("Prompt deleted", prompt_id=str(prompt_id), name=prompt.name)

    async def toggle_favorite(self, prompt_id: UUID) -> Prompt:
        """Toggle favorite status of a prompt.

        Args:
            prompt_id: Prompt ID

        Returns:
            Updated prompt

        Raises:
            ResourceNotFoundError: If prompt not found
        """
        prompt = await self.get_prompt_by_id(prompt_id)

        prompt.is_favorite = not prompt.is_favorite
        await self.db.commit()
        await self.db.refresh(prompt)

        logger.info(
            "Prompt favorite toggled",
            prompt_id=str(prompt.id),
            is_favorite=prompt.is_favorite,
        )
        return prompt

    async def increment_usage_count(self, prompt_id: UUID) -> Prompt:
        """Increment usage count of a prompt.

        Args:
            prompt_id: Prompt ID

        Returns:
            Updated prompt

        Raises:
            ResourceNotFoundError: If prompt not found
        """
        prompt = await self.get_prompt_by_id(prompt_id)

        prompt.usage_count += 1
        await self.db.commit()
        await self.db.refresh(prompt)

        logger.info(
            "Prompt usage count incremented",
            prompt_id=str(prompt.id),
            usage_count=prompt.usage_count,
        )
        return prompt

    async def get_statistics(self) -> PromptStatistics:
        """Get prompt statistics.

        Returns:
            Prompt statistics
        """
        # Total prompts
        total_result = await self.db.execute(select(func.count()).select_from(Prompt))
        total_prompts = total_result.scalar() or 0

        # Favorite count
        favorite_result = await self.db.execute(
            select(func.count()).where(Prompt.is_favorite == True)
        )
        favorite_count = favorite_result.scalar() or 0

        # Total usage count
        usage_result = await self.db.execute(select(func.sum(Prompt.usage_count)))
        total_usage_count = usage_result.scalar() or 0

        # Category count (distinct categories)
        category_result = await self.db.execute(
            select(func.count(func.distinct(Prompt.category)))
        )
        category_count = category_result.scalar() or 0

        return PromptStatistics(
            total_prompts=total_prompts,
            favorite_count=favorite_count,
            total_usage_count=total_usage_count,
            category_count=category_count,
        )

