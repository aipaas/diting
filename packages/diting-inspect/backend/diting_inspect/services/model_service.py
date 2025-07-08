from typing import Any, Dict
from diting_inspect.models.model_repository import InMemoryModelRepository
from diting_inspect.models.model_management import ModelManagementData, ModelType


class ModelService:
    def __init__(self, repository: InMemoryModelRepository):
        self.repository = repository

    async def create_model(
        self, model_data: ModelManagementData
    ) -> ModelManagementData:
        return await self.repository.create(model_data)

    async def get_models(self):
        return await self.repository.get_all()

    async def get_model(self, model_id: str):
        return await self.repository.get_by_id(model_id)

    async def update_model(self, model_id: str, updates: Dict[str, Any]):
        return await self.repository.update(model_id, updates)

    async def delete_model(self, model_id: str):
        return await self.repository.delete(model_id)

    async def set_default_model(self, model_type: ModelType, model_id: str):
        return await self.repository.set_default(model_type, model_id)

    async def get_default_model(self):
        return await self.repository.get_default()
