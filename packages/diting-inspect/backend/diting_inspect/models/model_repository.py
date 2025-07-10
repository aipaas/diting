import asyncio
from typing import List, Optional, Dict, Any
from uuid import uuid4

from diting_inspect.models.model_pickle_persistence import PicklePersistentMixin
from .model_management import ModelType, ModelManagementData


class InMemoryModelRepository(PicklePersistentMixin):
    def __init__(self, pickle_file: str = "data/models.pkl"):
        """Initialize empty in-memory storage."""
        super().__init__(pickle_file)
        saved_data = self.load_from_pickle({})
        self.models: Dict[str, Any] = saved_data.get("models", {})
        self.default_models: Dict[str, Optional[str]] = saved_data.get(
            "default_models", {}
        )
        self._models_lock = asyncio.Lock()
        self._default_models_lock = asyncio.Lock()

    def _save_all_data(self) -> None:
        """Save both models and default_models to pickle"""
        data = {"models": self.models, "default_models": self.default_models}
        self.save_to_pickle(data)

    async def create(self, model: ModelManagementData) -> ModelManagementData:
        async with self._models_lock:
            model_id = str(uuid4())
            model.id = model_id  # Assuming ModelManagementData has an 'id' field
            self.models[model_id] = model
            if model.is_default:
                self.default_models[model.model_type] = model_id
            self._save_all_data()
            return model

    async def get_all(self) -> List[ModelManagementData]:
        async with self._models_lock:
            return list(self.models.values())

    async def get_by_id(self, model_id: str) -> Optional[ModelManagementData]:
        async with self._models_lock:
            return self.models.get(model_id)

    async def update(
        self, model_id: str, updates: Dict[str, Any]
    ) -> Optional[ModelManagementData]:
        async with self._models_lock:
            model = self.models.get(model_id)
            if model:
                for key, value in updates.items():
                    setattr(model, key, value)
                self._save_all_data()
                return model
            return None

    async def delete(self, model_id: str) -> bool:
        async with self._models_lock:
            if model_id in self.models:
                del self.models[model_id]
                self._save_all_data()
                return True
            return False

    async def set_default(self, model_type: ModelType, model_id: str) -> bool:
        async with self._default_models_lock:
            if model_id in self.models:
                self.default_models[model_type] = model_id
                self._save_all_data()
                return True
            return False

    async def get_default(self) -> Dict[str, Optional[str]]:
        async with self._default_models_lock:
            return self.default_models
