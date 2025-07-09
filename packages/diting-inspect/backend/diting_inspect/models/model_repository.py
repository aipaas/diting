from typing import List, Optional, Dict, Any
from uuid import uuid4
from .model_management import ModelType, ModelManagementData


class InMemoryModelRepository:
    def __init__(self):
        self.models: Dict[str, Any] = {}
        self.default_models: Dict[str, Optional[str]] = {
            ModelType.INFERENCE: None,
            ModelType.EMBEDDING: None,
            ModelType.EVALUATION: None,
        }

    async def create(self, model: ModelManagementData) -> ModelManagementData:
        model_id = str(uuid4())
        model.id = model_id  # Assuming ModelManagementData has an 'id' field
        self.models[model_id] = model
        if model.is_default:
            self.default_models[model.model_type] = model_id
        return model

    async def get_all(self) -> List[ModelManagementData]:
        return list(self.models.values())

    async def get_by_id(self, model_id: str) -> Optional[ModelManagementData]:
        return self.models.get(model_id)

    async def update(
        self, model_id: str, updates: Dict[str, Any]
    ) -> Optional[ModelManagementData]:
        model = self.models.get(model_id)
        if model:
            for key, value in updates.items():
                setattr(model, key, value)
            return model
        return None

    async def delete(self, model_id: str) -> bool:
        if model_id in self.models:
            del self.models[model_id]
            return True
        return False

    async def set_default(self, model_type: ModelType, model_id: str) -> bool:
        if model_id in self.models:
            self.default_models[model_type] = model_id
            return True
        return False

    async def get_default(self) -> Dict[str, Optional[str]]:
        return self.default_models
