"""
FastAPI application for LLM evaluation webapp.
Provides REST API endpoints for managing test cases and running evaluations.
"""

import io
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import uuid

from diting_inspect.models.case_model import (
    InMemoryCaseRepository as CaseRepository,
    LLMCase,
)
from diting_inspect.models.evaluation_model import (
    InMemoryEvaluationRepository as EvaluationRepository,
)
from diting_inspect.services.case_service import CaseService
from diting_inspect.services.evaluation_service import EvaluationService
from diting_inspect.services.file_import_service import FileImportService

# Initialize FastAPI app
app = FastAPI(title="LLM Evaluation API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize repositories and services
case_repository = CaseRepository()
evaluation_repository = EvaluationRepository()
case_service = CaseService(case_repository)
evaluation_service = EvaluationService(evaluation_repository, case_repository)
file_import_service = FileImportService()


# Request/Response models
class CaseCreateRequest(BaseModel):
    """Request model for creating a new test case."""

    input: str
    actual_output: str
    expected_output: Optional[str] = None
    context: Optional[List[str]] = None
    retrieval_context: Optional[List[str]] = None


class CaseUpdateRequest(BaseModel):
    """Request model for updating an existing test case."""

    input: Optional[str] = None
    actual_output: Optional[str] = None
    expected_output: Optional[str] = None
    context: Optional[List[str]] = None
    retrieval_context: Optional[List[str]] = None


class EvaluationRequest(BaseModel):
    """Request model for running evaluations."""

    case_ids: List[str]
    metric_configs: List[Dict[str, Any]]


# Case management endpoints
@app.get("/api/cases", response_model=List[LLMCase])
async def get_cases(skip: int = 0, limit: int = 100) -> List[LLMCase]:
    """
    Retrieve paginated list of test cases.

    Args:
        skip: Number of cases to skip for pagination
        limit: Maximum number of cases to return

    Returns:
        List of LLM test cases
    """
    try:
        return await case_service.get_cases(skip=skip, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cases/{case_id}", response_model=LLMCase)
async def get_case(case_id: str) -> LLMCase:
    """
    Retrieve a specific test case by ID.

    Args:
        case_id: Unique identifier for the test case

    Returns:
        The requested test case

    Raises:
        HTTPException: If case not found
    """
    try:
        case = await case_service.get_case(case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        return case
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cases", response_model=LLMCase)
async def create_case(case_data: CaseCreateRequest) -> LLMCase:
    """
    Create a new test case.

    Args:
        case_data: Test case data

    Returns:
        Created test case with generated ID
    """
    try:
        case = LLMCase(id=str(uuid.uuid4()), **case_data.model_dump())
        return await case_service.create_case(case)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/cases/{case_id}", response_model=LLMCase)
async def update_case(case_id: str, case_data: CaseUpdateRequest) -> LLMCase:
    """
    Update an existing test case.

    Args:
        case_id: Unique identifier for the test case
        case_data: Updated case data

    Returns:
        Updated test case

    Raises:
        HTTPException: If case not found
    """
    try:
        case = await case_service.update_case(case_id, case_data.model_dump())
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        return case
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/cases/{case_id}")
async def delete_case(case_id: str) -> Dict[str, str]:
    """
    Delete a test case.

    Args:
        case_id: Unique identifier for the test case

    Returns:
        Success message

    Raises:
        HTTPException: If case not found
    """
    try:
        success = await case_service.delete_case(case_id)
        if not success:
            raise HTTPException(status_code=404, detail="Case not found")
        return {"message": "Case deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# File import endpoints
@app.post("/api/cases/import")
async def import_cases(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Import test cases from CSV or XLSX file.

    Args:
        file: Uploaded file containing test cases

    Returns:
        Import summary with count of imported cases

    Raises:
        HTTPException: If file format is not supported
    """
    try:
        assert file.filename is not None
        if file.filename.endswith(".csv"):
            content = await file.read()
            df = pd.read_csv(io.StringIO(content.decode("utf-8")))  # type: ignore[misc]
        elif file.filename.endswith((".xlsx", ".xls")):
            content = await file.read()
            df = pd.read_excel(io.BytesIO(content))  # type: ignore[misc]
        else:
            raise HTTPException(
                status_code=400, detail="Unsupported file format. Use CSV or XLSX."
            )

        cases = await file_import_service.process_dataframe(df)
        imported_cases: list[LLMCase] = []

        for case_data in cases:
            case = LLMCase(id=str(uuid.uuid4()), **case_data)
            imported_case = await case_service.create_case(case)
            imported_cases.append(imported_case)

        return {
            "message": f"Successfully imported {len(imported_cases)} cases",
            "count": len(imported_cases),
            "cases": imported_cases,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Evaluation endpoints
@app.post("/api/evaluations")
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
        )

        return {"evaluation_id": evaluation_id, "message": "Evaluation started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/evaluations/{evaluation_id}")
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


@app.get("/api/evaluations")
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


@app.delete("/api/evaluations/{evaluation_id}")
async def delete_evaluation(evaluation_id: str) -> Dict[str, str]:
    success = await evaluation_service.delete_evaluation(evaluation_id)
    if success:
        return {"message": "Evaluation deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Evaluation not found")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
