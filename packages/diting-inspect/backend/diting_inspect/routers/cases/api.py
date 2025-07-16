import io
from typing import List, Optional, Dict, Any
from diting_inspect.utils import dt_persistent_path
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
)
from pydantic import BaseModel
import pandas as pd
import uuid

from diting_inspect.models.case_model import (
    InMemoryCaseRepository as CaseRepository,
    LLMCaseData,
)
from diting_inspect.services.case_service import CaseService
from diting_inspect.services.file_import_service import FileImportService

router = APIRouter(prefix="/api/cases", tags=["cases"])

case_repository = CaseRepository(pickle_file=f"{dt_persistent_path}/cases.pkl")
case_service = CaseService(case_repository)
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


# Case management endpoints
@router.get("", response_model=List[LLMCaseData])
async def get_cases(skip: int = 0, limit: int = 100) -> List[LLMCaseData]:
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


@router.get("/{case_id}", response_model=LLMCaseData)
async def get_case(case_id: str) -> LLMCaseData:
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


@router.post("", response_model=LLMCaseData)
async def create_case(case_data: CaseCreateRequest) -> LLMCaseData:
    """
    Create a new test case.

    Args:
        case_data: Test case data

    Returns:
        Created test case with generated ID
    """
    try:
        case = LLMCaseData(id=str(uuid.uuid4()), **case_data.model_dump())
        return await case_service.create_case(case)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{case_id}", response_model=LLMCaseData)
async def update_case(case_id: str, case_data: CaseUpdateRequest) -> LLMCaseData:
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


@router.delete("/{case_id}")
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
@router.post("/api/cases/import")
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
        imported_cases: list[LLMCaseData] = []

        for case_data in cases:
            case = LLMCaseData(id=str(uuid.uuid4()), **case_data)
            imported_case = await case_service.create_case(case)
            imported_cases.append(imported_case)

        return {
            "message": f"Successfully imported {len(imported_cases)} cases",
            "count": len(imported_cases),
            "cases": imported_cases,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
