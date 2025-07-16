from typing import List, Dict, Any
from diting_inspect.utils import dt_persistent_path
from fastapi import (
    APIRouter,
    HTTPException,
)

from diting_inspect.models.model_management import ModelManagementData, ModelType
from diting_inspect.models.model_repository import InMemoryModelRepository
from diting_inspect.services.model_service import ModelService

model_repository = InMemoryModelRepository(
    pickle_file=f"{dt_persistent_path}/models.pkl"
)
model_service = ModelService(model_repository)
router = APIRouter(prefix="/api/models", tags=["models"])


# Model management endpoints
@router.post("", response_model=ModelManagementData)
async def create_model(model_data: ModelManagementData) -> ModelManagementData:
    return await model_service.create_model(model_data)


@router.get("", response_model=List[ModelManagementData])
async def get_models() -> List[ModelManagementData]:
    return await model_service.get_models()


@router.get("/{model_id}", response_model=ModelManagementData)
async def get_model(model_id: str) -> ModelManagementData:
    model = await model_service.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.put("/{model_id}", response_model=ModelManagementData)
async def update_model(
    model_id: str, model_data: ModelManagementData
) -> ModelManagementData:
    updated_model = await model_service.update_model(model_id, model_data.model_dump())
    if not updated_model:
        raise HTTPException(status_code=404, detail="Model not found")
    return updated_model


@router.delete("/{model_id}")
async def delete_model(model_id: str) -> Dict[str, str]:
    success = await model_service.delete_model(model_id)
    if not success:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"message": "Model deleted successfully"}


@router.post("/default/{model_type}/{model_id}")
async def set_default_model(model_type: ModelType, model_id: str) -> Dict[str, str]:
    success = await model_service.set_default_model(model_type, model_id)
    if not success:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"message": f"{model_type} model set as default"}


@router.get("/default")
async def get_default_model() -> Dict[str, Any]:
    default_modules = await model_service.get_default_model()
    if not default_modules:
        raise HTTPException(status_code=404, detail="Default model not found")
    return {"default_model": default_modules}
