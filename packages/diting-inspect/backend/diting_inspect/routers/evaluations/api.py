from typing import List, Optional, Dict, Any
from diting_inspect.metrics import MetricOptionSchema
from diting_inspect.models.synthesizer_model import (
    InMemorySynthesizerRepository,
)
from diting_inspect.services.synthesizer_service import SynthesizerService
from diting_inspect.synthesizers import SynthesizerSchema
from diting_inspect.utils import dt_persistent_path
from fastapi import (
    APIRouter,
    HTTPException,
    BackgroundTasks,
)
from pydantic import BaseModel
import uuid

from diting_inspect.models.case_model import (
    InMemoryCaseRepository as CaseRepository,
)
from diting_inspect.models.evaluation_model import (
    InMemoryEvaluationRepository as EvaluationRepository,
)
from diting_inspect.services.evaluation_service import EvaluationService
from diting_inspect.models.model_management import ModelManagementData


class EvaluationRequest(BaseModel):
    """Request model for running evaluations."""

    case_ids: List[str]
    metric_configs: List[Dict[str, Any]]
    model_configs: Optional[List[ModelManagementData]]


class SynthesizeRequest(BaseModel):
    """Request model for running synthesizers."""

    case_ids: List[str]
    synthesizer_configs: List[Dict[str, Any]]
    model_configs: Optional[List[ModelManagementData]]


case_repository = CaseRepository(pickle_file=f"{dt_persistent_path}/cases.pkl")
evaluation_repository = EvaluationRepository(
    pickle_file=f"{dt_persistent_path}/evaluations.pkl"
)
synthesizer_repository = InMemorySynthesizerRepository(
    pickle_file=f"{dt_persistent_path}/synthesizers.pkl"
)
evaluation_service = EvaluationService(evaluation_repository, case_repository)
synthesizer_service = SynthesizerService(synthesizer_repository, case_repository)

router = APIRouter(prefix="/api", tags=["evaluations"])


# Evaluation endpoints
@router.post("/evaluations")
async def run_evaluation(
    evaluation_request: EvaluationRequest, background_tasks: BackgroundTasks
) -> Dict[str, str]:
    """
    Run evaluation on specified test cases.

    Args:
        evaluation_request: Evaluation configuration
        background_tasks: FastAPI background tasks

    Returns:
        Evaluation job ID for tracking progress
    """
    try:
        evaluation_id = str(uuid.uuid4())

        # Start evaluation in background
        background_tasks.add_task(
            evaluation_service.run_evaluation,
            evaluation_id,
            evaluation_request.case_ids,
            evaluation_request.metric_configs,
            evaluation_request.model_configs,
        )

        return {"evaluation_id": evaluation_id, "message": "Evaluation started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/synthesizers")
async def run_synthesizer(
    synthesize_request: SynthesizeRequest, background_tasks: BackgroundTasks
) -> Dict[str, str]:
    """
    Run synthesizer on specified test cases.

    Args:
        synthesize_request: Synthesizer configuration
        background_tasks: FastAPI background tasks

    Returns:
        Synthesizer job ID for tracking progress
    """
    try:
        synthesizer_id = str(uuid.uuid4())

        # Start synthesizer in background
        background_tasks.add_task(
            synthesizer_service.run_synthesizer,
            synthesizer_id,
            synthesize_request.case_ids,
            synthesize_request.synthesizer_configs,
            synthesize_request.model_configs,
        )

        return {"synthesizer_id": synthesizer_id, "message": "Synthesizer started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evaluations/{evaluation_id}")
async def get_evaluation_status(evaluation_id: str) -> Dict[str, Any]:
    """
    Get evaluation status and results.

    Args:
        evaluation_id: Unique evaluation identifier

    Returns:
        Evaluation status and results if completed
    """
    try:
        result = await evaluation_service.get_evaluation_result(evaluation_id)
        if not result:
            raise HTTPException(status_code=404, detail="Evaluation not found")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evaluations")
async def get_evaluations(skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get list of evaluation results.

    Args:
        skip: Number of results to skip for pagination
        limit: Maximum number of results to return

    Returns:
        List of evaluation results
    """
    try:
        return await evaluation_service.get_evaluations(skip=skip, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/evaluations/{evaluation_id}")
async def delete_evaluation(evaluation_id: str) -> Dict[str, str]:
    success = await evaluation_service.delete_evaluation(evaluation_id)
    if success:
        return {"message": "Evaluation deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Evaluation not found")


@router.get("/metrics_schemas", response_model=list[MetricOptionSchema])
async def get_available_metrics() -> list[MetricOptionSchema]:
    try:
        return await evaluation_service.get_available_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/synthesizers_schemas", response_model=list[SynthesizerSchema])
async def get_available_synthesizers() -> list[SynthesizerSchema]:
    try:
        return await evaluation_service.get_available_synthesizers()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
