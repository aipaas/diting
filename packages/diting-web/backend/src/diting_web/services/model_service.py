"""Model service for business logic."""

from typing import Optional, Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from diting_web.common.exceptions import ResourceConflictError, ResourceNotFoundError, BusinessError
from diting_web.common.logging import get_logger
from diting_web.common.response import PaginatedResponse
from diting_web.models.model import Model, ModelTypeEnum
from diting_web.schemas.model import ModelCreate, ModelResponse, ModelUpdate
from diting_web.integrations.core_adapter.config_mapper import (
    create_llm_from_config,
    create_embedding_from_config,
    get_default_llm_config,
    get_default_embedding_config,
)

logger = get_logger(__name__)


class ModelService:
    """Model service for business logic."""

    def __init__(self, db: AsyncSession):
        """Initialize model service.

        Args:
            db: Database session
        """
        self.db = db

    async def create_model(self, model_data: ModelCreate) -> Model:
        """Create a new model.

        Args:
            model_data: Model creation data

        Returns:
            Created model

        Raises:
            ResourceConflictError: If model with same name and type exists
        """
        # Check if a model with same name and type already exists
        existing_model = await self.db.execute(
            select(Model).where(
                Model.name == model_data.name,
                Model.model_type == model_data.model_type
            )
        )
        if existing_model.scalar_one_or_none():
            raise ResourceConflictError(
                f"Model with name '{model_data.name}' and type '{model_data.model_type}' already exists"
            )

        # If setting as default, unset other defaults of the same type
        if model_data.is_default:
            await self._unset_default_models(model_data.model_type)

        # Create model
        model = Model(
            name=model_data.name,
            model_type=model_data.model_type,
            provider=model_data.provider,
            model_name=model_data.model_name,
            description=model_data.description,
            api_key=model_data.api_key,
            base_url=model_data.base_url,
            parameters=model_data.parameters or {},
            timeout=model_data.timeout or 60,
            is_default=model_data.is_default or False,
        )
        self.db.add(model)
        await self.db.commit()
        await self.db.refresh(model)

        logger.info("Model created", model_id=str(model.id), name=model.name, type=model.model_type)
        return model

    async def get_models_list(
        self,
        offset: int,
        limit: int,
        model_type: Optional[ModelTypeEnum] = None,
    ) -> PaginatedResponse[ModelResponse]:
        """Get models list with pagination and filters.

        Args:
            offset: Pagination offset
            limit: Pagination limit
            model_type: Filter by model type (llm/embedding)

        Returns:
            Paginated response with models
        """
        query = select(Model)

        if model_type:
            query = query.where(Model.model_type == model_type)

        query = query.order_by(Model.is_default.desc(), Model.created_at.desc())

        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar() or 0

        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        items = result.scalars().all()

        # Mask API keys for all models
        masked_items = []
        for item in items:
            item_dict = ModelResponse.model_validate(item).model_dump()
            item_dict["api_key"] = item.mask_api_key()
            masked_items.append(ModelResponse(**item_dict))

        return PaginatedResponse.create(
            items=masked_items,
            total=total,
            page=offset // limit + 1,
            page_size=limit,
        )

    async def get_model_by_id(self, model_id: UUID, mask_api_key: bool = True) -> Model:
        """Get model details by ID.

        Args:
            model_id: Model ID
            mask_api_key: Whether to mask API key in response

        Returns:
            Model

        Raises:
            ResourceNotFoundError: If model not found
        """
        result = await self.db.execute(select(Model).where(Model.id == model_id))
        model = result.scalar_one_or_none()
        if model is None:
            raise ResourceNotFoundError("Model", str(model_id))
        return model

    async def update_model(
        self, model_id: UUID, model_data: ModelUpdate
    ) -> Model:
        """Update model.

        Args:
            model_id: Model ID
            model_data: Update data

        Returns:
            Updated model

        Raises:
            ResourceNotFoundError: If model not found
        """
        model = await self.get_model_by_id(model_id, mask_api_key=False)

        # If setting as default, unset other defaults of the same type
        if model_data.is_default is True and not model.is_default:
            await self._unset_default_models(model.model_type, exclude_id=model_id)

        update_data = model_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(model, field, value)

        await self.db.commit()
        await self.db.refresh(model)

        logger.info("Model updated", model_id=str(model.id), name=model.name)
        return model

    async def delete_model(self, model_id: UUID) -> None:
        """Delete model.

        Args:
            model_id: Model ID

        Raises:
            ResourceNotFoundError: If model not found
            BusinessError: If trying to delete the only default model
        """
        model = await self.get_model_by_id(model_id, mask_api_key=False)

        # Check if this is the only default model of its type
        if model.is_default:
            count_result = await self.db.execute(
                select(func.count()).where(
                    Model.model_type == model.model_type,
                    Model.id != model_id
                )
            )
            count = count_result.scalar() or 0
            if count == 0:
                raise BusinessError("Cannot delete the only model of this type")

        await self.db.delete(model)
        await self.db.commit()

        logger.info("Model deleted", model_id=str(model_id), name=model.name)

    async def set_default_model(self, model_id: UUID) -> Model:
        """Set a model as default for its type.

        Args:
            model_id: Model ID

        Returns:
            Updated model

        Raises:
            ResourceNotFoundError: If model not found
        """
        model = await self.get_model_by_id(model_id, mask_api_key=False)

        if model.is_default:
            return model  # Already default

        # Unset other defaults of the same type
        await self._unset_default_models(model.model_type, exclude_id=model_id)

        model.is_default = True
        await self.db.commit()
        await self.db.refresh(model)

        logger.info("Default model set", model_id=str(model.id), name=model.name, type=model.model_type)
        return model

    async def _unset_default_models(
        self, model_type: ModelTypeEnum, exclude_id: Optional[UUID] = None
    ) -> None:
        """Unset default flag for all models of a specific type.

        Args:
            model_type: Model type to unset defaults for
            exclude_id: Optionally exclude a specific model ID
        """
        query = select(Model).where(
            Model.model_type == model_type,
            Model.is_default == True
        )
        if exclude_id:
            query = query.where(Model.id != exclude_id)

        result = await self.db.execute(query)
        models = result.scalars().all()

        for model in models:
            model.is_default = False

        await self.db.commit()

    async def test_model_connection(self, model_id: UUID) -> dict[str, Any]:
        """Test model connection by making a simple API call.
        
        Args:
            model_id: Model ID to test
            
        Returns:
            dict: Test result with success status and message
            
        Raises:
            ResourceNotFoundError: If model not found
        """
        model = await self.get_model_by_id(model_id, mask_api_key=False)
        
        # Build config dict from model
        config = {
            "model_name": model.model_name,
            "base_url": model.base_url,
            "api_key": model.api_key,
            "timeout": float(model.timeout),
        }
        
        # Merge with parameters if available
        if model.parameters:
            config.update(model.parameters)
        
        # Apply defaults if api_key or base_url is not set
        if model.model_type == ModelTypeEnum.LLM:
            default_config = get_default_llm_config()
            if not config.get("model_name") and default_config.get("model_name"):
                config["model_name"] = default_config["model_name"]
            if not config.get("api_key") and default_config.get("api_key"):
                config["api_key"] = default_config["api_key"]
            if not config.get("base_url") and default_config.get("base_url"):
                config["base_url"] = default_config["base_url"]
        elif model.model_type == ModelTypeEnum.EMBEDDING:
            default_config = get_default_embedding_config()
            if not config.get("model_name") and default_config.get("model_name"):
                config["model_name"] = default_config["model_name"]
            if not config.get("api_key") and default_config.get("api_key"):
                config["api_key"] = default_config["api_key"]
            if not config.get("base_url") and default_config.get("base_url"):
                config["base_url"] = default_config["base_url"]
        
        # Check if model_name is still missing
        if not config.get("model_name"):
            return {
                "success": False,
                "message": "连接测试失败：模型标识未设置，无法进行测试。请填写模型标识或配置系统默认模型。",
            }
        
        try:
            if model.model_type == ModelTypeEnum.LLM:
                # Test LLM connection with a simple prompt
                llm = create_llm_from_config(config)
                test_prompt = "Hello"
                response = await llm.generate(test_prompt, n=1)
                if response:
                    logger.info(
                        "Model connection test successful",
                        model_id=str(model_id),
                        model_name=model.name,
                        model_type=model.model_type,
                    )
                    return {
                        "success": True,
                        "message": f"连接测试成功！模型响应正常。",
                        "response_preview": (
                            str(response)[:100] + "..." if len(str(response)) > 100 
                            else str(response)
                        ) if response else None,
                    }
            elif model.model_type == ModelTypeEnum.EMBEDDING:
                # Test embedding connection with a simple text
                embedding = create_embedding_from_config(config)
                test_text = "test"
                response = await embedding.aembed_query(test_text)
                if response and len(response) > 0:
                    logger.info(
                        "Model connection test successful",
                        model_id=str(model_id),
                        model_name=model.name,
                        model_type=model.model_type,
                    )
                    return {
                        "success": True,
                        "message": f"连接测试成功！模型响应正常，向量维度：{len(response)}。",
                        "response_preview": None,
                    }
            
            return {
                "success": False,
                "message": "连接测试失败：模型未返回有效响应。",
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(
                "Model connection test failed",
                model_id=str(model_id),
                model_name=model.name,
                error=error_msg,
                exc_info=True,
            )
            return {
                "success": False,
                "message": f"连接测试失败：{error_msg}",
            }

