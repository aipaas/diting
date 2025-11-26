"""Tasks API (Simplified)."""

from typing import Annotated, Optional
from uuid import UUID
import json
from io import BytesIO

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import StreamingResponse

from diting_web.auth import get_current_user
from diting_web.common.response import success_response
from diting_web.dependencies import PaginationParams, get_dataset_service, get_task_service
from diting_web.models.task import TaskStatus, TaskType
from diting_web.models.user import User
from diting_web.schemas.task import (
    CreateBatchEvaluationTaskRequest,
    CreateDatasetFromSynthesisRequest,
    CreateEvaluationTaskRequest,
    CreateNegativeMiningTaskRequest,
    CreateSynthesisTaskRequest,
    SynthesisResultResponse,
    TaskCreateResponse,
    TaskResponse,
)
from diting_web.services import DatasetService, TaskService

router = APIRouter(prefix="/tasks")


@router.post("/evaluations", status_code=status.HTTP_201_CREATED)
async def create_evaluation_task(
    task_data: CreateEvaluationTaskRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> dict:
    """Create an evaluation task (Simplified: user-level)."""
    task = await service.create_evaluation_task(task_data, current_user.id)

    response = TaskCreateResponse(
        task_id=task.id,
        status=task.status,
        created_at=task.created_at,
        estimated_time=30,  # seconds
    )

    return success_response(data=response.model_dump(), code=201)


@router.post("/synthesis", status_code=status.HTTP_201_CREATED)
async def create_synthesis_task(
    task_data: CreateSynthesisTaskRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> dict:
    """Create a synthesis task (Simplified: user-level)."""
    task = await service.create_synthesis_task(task_data, current_user.id)

    response = TaskCreateResponse(
        task_id=task.id,
        status=task.status,
        created_at=task.created_at,
        estimated_time=60,  # seconds
    )

    return success_response(data=response.model_dump(), code=201)


@router.post("/negative-mining", status_code=status.HTTP_201_CREATED)
async def create_negative_mining_task(
    task_data: CreateNegativeMiningTaskRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> dict:
    """Create a negative mining task (Simplified: user-level)."""
    task = await service.create_negative_mining_task(task_data, current_user.id)

    response = TaskCreateResponse(
        task_id=task.id,
        status=task.status,
        created_at=task.created_at,
        estimated_time=120,  # seconds (estimated)
    )

    return success_response(data=response.model_dump(), code=201)


@router.post("/batch-evaluations", status_code=status.HTTP_201_CREATED)
async def create_batch_evaluation_task(
    task_data: CreateBatchEvaluationTaskRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> dict:
    """Create a batch evaluation task (Simplified: user-level)."""
    task = await service.create_batch_evaluation_task(task_data, current_user.id)

    response = TaskCreateResponse(
        task_id=task.id,
        status=task.status,
        created_at=task.created_at,
        estimated_time=None,  # Varies based on dataset size
    )

    return success_response(data=response.model_dump(), code=201)


@router.get("/{task_id}")
async def get_task(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> dict:
    """Get task details (verify user access)."""
    task = await service.get_task_by_id(task_id, user_id=current_user.id, is_admin=current_user.is_admin)
    return success_response(data=TaskResponse.model_validate(task).model_dump())


@router.get("")
async def list_tasks(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TaskService, Depends(get_task_service)],
    pagination: Annotated[PaginationParams, Depends()],
    task_type: Optional[TaskType] = None,
    status_param: Optional[TaskStatus] = None,
) -> dict:
    """Get tasks list (filtered by current user or all for admin)."""
    paginated_data = await service.get_tasks_list(
        user_id=current_user.id,
        is_admin=current_user.is_admin,
        task_type=task_type,
        status=status_param,
        offset=pagination.offset,
        limit=pagination.limit,
    )

    return success_response(data=paginated_data.model_dump())


@router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> dict:
    """Cancel a task (verify user access)."""
    task = await service.cancel_task(task_id, user_id=current_user.id, is_admin=current_user.is_admin)
    return success_response(data=TaskResponse.model_validate(task).model_dump())


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> None:
    """Delete a task and its results (verify user access)."""
    await service.delete_task(task_id, user_id=current_user.id, is_admin=current_user.is_admin)


@router.post("/{task_id}/retry")
async def retry_task(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> dict:
    """Retry a failed task (verify user access)."""
    task = await service.retry_task(task_id, user_id=current_user.id, is_admin=current_user.is_admin)
    return success_response(data=TaskResponse.model_validate(task).model_dump())


@router.get("/{task_id}/evaluation-results")
async def get_evaluation_results(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TaskService, Depends(get_task_service)],
    pagination: Annotated[PaginationParams, Depends()],
    pivot: bool = False,  # When true, group by question and return multiple metric results per item
) -> dict:
    """Get evaluation results for a task.

    - flat (default): one row per metric result
    - pivot: one row per question with multiple metric scores
    """
    results = await service.get_evaluation_results(
        task_id,
        offset=pagination.offset,
        limit=pagination.limit,
        pivot=pivot,
        user_id=current_user.id,
        is_admin=current_user.is_admin,
    )
    return success_response(data=results.model_dump())


@router.get("/{task_id}/evaluation-results/summary")
async def get_evaluation_summary(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> dict:
    """Get evaluation summary statistics."""
    summary = await service.get_evaluation_summary(
        task_id,
        user_id=current_user.id,
        is_admin=current_user.is_admin,
    )
    return success_response(data=summary)


@router.get("/{task_id}/evaluation-results/export")
async def export_evaluation_results(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TaskService, Depends(get_task_service)],
    format: str = "csv",  # "csv", "excel", or "jsonl"
) -> Response:
    """Export evaluation results as CSV, Excel, or JSONL."""
    # Get all results (without pagination for export)
    results_paginated = await service.get_evaluation_results(
        task_id,
        offset=0,
        limit=10000,
        user_id=current_user.id,
        is_admin=current_user.is_admin,
    )
    results = results_paginated.items

    if format == "csv":
        import csv
        from io import StringIO
        # Write CSV to text buffer, then encode once at the end (Excel-friendly BOM)
        text_buffer = StringIO()
        writer = csv.writer(text_buffer)
        # Header
        writer.writerow([
            "metric_name", "score", "reason",
            "user_input", "actual_output", "expected_output",
            "created_at",
        ])
        # Rows
        for r in results:
            writer.writerow([
                r.get("metric_name", ""),
                r.get("score") if r.get("score") is not None else "",
                r.get("reason") or "",
                r.get("user_input") or "",
                r.get("actual_output") or "",
                r.get("expected_output") or "",
                r.get("created_at", ""),
            ])
        # Encode with BOM for Excel
        csv_bytes = ('\ufeff' + text_buffer.getvalue()).encode("utf-8")
        output = BytesIO(csv_bytes)
        filename = f"evaluation_results_{task_id}.csv"
        return StreamingResponse(
            output,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    elif format == "excel":
        try:
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "Evaluation Results"

            # Write header
            headers = [
                "Metric Name", "Score", "Reason",
                "User Input", "Actual Output", "Expected Output",
                "Created At"
            ]
            ws.append(headers)

            # Write data
            for r in results:
                ws.append([
                    r["metric_name"],
                    r["score"] if r["score"] is not None else "",
                    r["reason"] or "",
                    r["user_input"] or "",
                    r["actual_output"] or "",
                    r["expected_output"] or "",
                    r["created_at"],
                ])

            # Save to BytesIO
            output = BytesIO()
            wb.save(output)
            output.seek(0)

            filename = f"evaluation_results_{task_id}.xlsx"
            return StreamingResponse(
                output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'}
            )
        except ImportError:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail="Excel export requires openpyxl package"
            )
    elif format == "jsonl":
        output = BytesIO()
        for r in results:
            line = json.dumps(r, ensure_ascii=False) + "\n"
            output.write(line.encode("utf-8"))
        output.seek(0)
        filename = f"evaluation_results_{task_id}.jsonl"
        return StreamingResponse(
            output,
            media_type="application/x-ndjson",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    else:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format: {format}. Must be 'csv', 'excel', or 'jsonl'"
        )


@router.get("/{task_id}/synthesis-results")
async def get_synthesis_results(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> dict:
    """Get synthesis results for a task."""
    results = await service.get_synthesis_results(
        task_id,
        user_id=current_user.id,
        is_admin=current_user.is_admin,
    )
    return success_response(
        data=[SynthesisResultResponse.model_validate(r).model_dump() for r in results]
    )


@router.get("/{task_id}/synthesis-results/export")
async def export_synthesis_results(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TaskService, Depends(get_task_service)],
    format: str = "csv",  # "csv" or "jsonl"
) -> Response:
    """Export synthesis results as CSV or JSONL."""
    results = await service.get_synthesis_results(
        task_id,
        user_id=current_user.id,
        is_admin=current_user.is_admin,
    )
    
    if format == "csv":
        import csv
        from io import StringIO
        text_buffer = StringIO()
        writer = csv.writer(text_buffer)
        # Header - only question and answer
        writer.writerow(["question", "answer"])
        # Rows - only question and answer
        for r in results:
            writer.writerow([
                r.question,
                r.answer,
            ])
        csv_bytes = ('\ufeff' + text_buffer.getvalue()).encode("utf-8")
        output = BytesIO(csv_bytes)
        filename = f"synthesis_results_{task_id}.csv"
        return StreamingResponse(
            output,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    elif format == "jsonl":
        output = BytesIO()
        for r in results:
            # Only export question and answer
            line = json.dumps({
                "question": r.question,
                "answer": r.answer,
            }, ensure_ascii=False) + "\n"
            output.write(line.encode("utf-8"))
        output.seek(0)
        filename = f"synthesis_results_{task_id}.jsonl"
        return StreamingResponse(
            output,
            media_type="application/x-ndjson",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid format: {format}. Must be 'csv' or 'jsonl'")


@router.post("/{task_id}/synthesis-results/create-dataset")
async def create_dataset_from_synthesis_results(
    task_id: UUID,
    request: CreateDatasetFromSynthesisRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    task_service: Annotated[TaskService, Depends(get_task_service)],
    dataset_service: Annotated[DatasetService, Depends(get_dataset_service)],
) -> dict:
    """Create a dataset from synthesis results."""
    # Get synthesis results
    results = await task_service.get_synthesis_results(
        task_id,
        user_id=current_user.id,
        is_admin=current_user.is_admin,
    )
    
    if not results:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="No synthesis results found for this task")
    
    # Convert results to dataset rows format
    dataset_rows = []
    for idx, r in enumerate(results):
        row_data = {
            "question": r.question,
            "answer": r.answer,
        }
        if r.source_context:
            row_data["source_context"] = r.source_context
        if r.quality_score is not None:
            row_data["quality_score"] = float(r.quality_score)
        dataset_rows.append(row_data)
    
    # Create dataset from data (without file upload)
    dataset = await dataset_service.create_dataset_from_data(
        name=request.name,
        description=request.description,
        data=dataset_rows,
        created_by=current_user.id,
    )
    
    from diting_web.services.dataset.dataset_service import _dataset_to_dict
    return success_response(
        data=_dataset_to_dict(dataset),
        code=201
    )


@router.get("/{task_id}/negative-mining-results")
async def get_negative_mining_results(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> dict:
    """Get negative mining results for a task."""
    results = await service.get_negative_mining_results(
        task_id,
        user_id=current_user.id,
        is_admin=current_user.is_admin,
    )
    return success_response(data=results)


@router.get("/{task_id}/negative-mining-results/export")
async def export_negative_mining_results(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TaskService, Depends(get_task_service)],
    format: str = "json",  # "json" or "jsonl"
) -> Response:
    """Export negative mining results as JSON or JSONL."""
    results = await service.get_negative_mining_results(
        task_id,
        user_id=current_user.id,
        is_admin=current_user.is_admin,
    )
    
    if format == "json":
        output = BytesIO()
        json_str = json.dumps(results, ensure_ascii=False, indent=2)
        output.write(json_str.encode("utf-8"))
        output.seek(0)
        filename = f"negative_mining_results_{task_id}.json"
        return StreamingResponse(
            output,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    elif format == "jsonl":
        output = BytesIO()
        for r in results:
            line = json.dumps(r, ensure_ascii=False) + "\n"
            output.write(line.encode("utf-8"))
        output.seek(0)
        filename = f"negative_mining_results_{task_id}.jsonl"
        return StreamingResponse(
            output,
            media_type="application/x-ndjson",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid format: {format}. Must be 'json' or 'jsonl'")


@router.post("/{task_id}/negative-mining-results/create-dataset")
async def create_dataset_from_negative_mining_results(
    task_id: UUID,
    request: CreateDatasetFromSynthesisRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    task_service: Annotated[TaskService, Depends(get_task_service)],
    dataset_service: Annotated[DatasetService, Depends(get_dataset_service)],
) -> dict:
    """Create a dataset from negative mining results."""
    # Get negative mining results
    results = await task_service.get_negative_mining_results(
        task_id,
        user_id=current_user.id,
        is_admin=current_user.is_admin,
    )
    
    if not results:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="No negative mining results found for this task")
    
    # Convert results to dataset rows format
    # Each result contains: query, pos (list), neg (list)
    dataset_rows = []
    for idx, r in enumerate(results):
        row_data = {
            "query": r.get("query", ""),
            "positive_samples": r.get("pos", []),
            "negative_samples": r.get("neg", []),
        }
        dataset_rows.append(row_data)
    
    # Create dataset from data (without file upload)
    dataset = await dataset_service.create_dataset_from_data(
        name=request.name,
        description=request.description,
        data=dataset_rows,
        created_by=current_user.id,
    )
    
    from diting_web.services.dataset.dataset_service import _dataset_to_dict
    return success_response(
        data=_dataset_to_dict(dataset),
        code=201
    )
