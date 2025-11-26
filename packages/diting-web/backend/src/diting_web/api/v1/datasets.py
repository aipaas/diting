"""Datasets API (Simplified)."""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import Response

from diting_web.auth import get_current_user
from diting_web.common.response import success_response
from diting_web.dependencies import PaginationParams, get_dataset_service
from diting_web.models.user import User
from diting_web.schemas.dataset import (
    AnnotationColumnCreate,
    AnnotationColumnDelete,
    AnnotationColumnUpdate,
    DatasetDataUpdate,
    DatasetResponse,
    DatasetRowUpdate,
    DatasetRowDelete,
)
from diting_web.services import DatasetService
from diting_web.services.dataset.dataset_service import _dataset_to_dict

router = APIRouter(prefix="/datasets")


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    service: Annotated[DatasetService, Depends(get_dataset_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    name: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
) -> dict:
    """Upload a dataset (Simplified: user-level)."""
    dataset = await service.create_dataset(
        name=name,
        description=description,
        file=file,
        created_by=current_user.id,
    )
    return success_response(
        data=DatasetResponse.model_validate(_dataset_to_dict(dataset)).model_dump(),
        code=201,
    )


@router.get("")
async def list_datasets(
    service: Annotated[DatasetService, Depends(get_dataset_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    pagination: PaginationParams = Depends(),
) -> dict:
    """Get datasets list (filtered by current user or all for admin)."""
    paginated_data = await service.get_datasets_list(
        user_id=current_user.id,
        is_admin=current_user.is_admin,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    return success_response(data=paginated_data.model_dump())


@router.get("/{dataset_id}")
async def get_dataset(
    dataset_id: UUID,
    service: Annotated[DatasetService, Depends(get_dataset_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Get dataset details (verify user access)."""
    dataset = await service.get_dataset_by_id(dataset_id, user_id=current_user.id, is_admin=current_user.is_admin)
    return success_response(data=DatasetResponse.model_validate(_dataset_to_dict(dataset)).model_dump())


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    dataset_id: UUID,
    service: Annotated[DatasetService, Depends(get_dataset_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Delete dataset (verify user ownership or admin)."""
    await service.delete_dataset(dataset_id, user_id=current_user.id, is_admin=current_user.is_admin)


@router.get("/{dataset_id}/download")
async def get_dataset_download_url(
    dataset_id: UUID,
    service: Annotated[DatasetService, Depends(get_dataset_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Get presigned download URL for dataset file (verify user access)."""
    download_url = await service.get_dataset_download_url(dataset_id, user_id=current_user.id, is_admin=current_user.is_admin)
    return success_response(data={"download_url": download_url})


@router.get("/{dataset_id}/preview")
async def preview_dataset(
    dataset_id: UUID,
    service: Annotated[DatasetService, Depends(get_dataset_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    pagination: PaginationParams = Depends(),
    search: Optional[str] = None,
) -> dict:
    """Get dataset preview data with pagination support.
    
    Queries data from dataset_rows table directly, supporting database-level search.
    Returns paginated data for viewing and editing.
    
    Args:
        dataset_id: Dataset ID
        pagination: Pagination parameters
        search: Optional search keyword to filter data across all columns (database-level search)
    """
    # Load dataset without relationships for better performance
    dataset = await service.get_dataset_by_id(dataset_id, user_id=current_user.id, is_admin=current_user.is_admin, load_relationships=False)
    
    # Get original columns and data types
    original_columns = dataset.columns.get("columns", []) if dataset.columns else []
    data_types = dataset.metadata_.get("data_types", {})
    
    # Add annotation columns to the column list, deduplicated while preserving order
    annotation_columns = dataset.metadata_.get("annotation_columns", [])
    annotation_names = [col["column_name"] for col in annotation_columns]
    # Preserve original column order; append annotation columns; remove duplicates
    all_columns = list(dict.fromkeys(original_columns + annotation_names))
    
    # Add annotation column types to data_types
    for col in annotation_columns:
        data_types[col["column_name"]] = col.get("column_type", "text")
    
    # Get paginated data with optional search, pass dataset to avoid duplicate query
    paginated_data = await service.get_dataset_data_paginated(
        dataset_id,
        offset=pagination.offset,
        limit=pagination.limit,
        search=search,
        dataset=dataset,  # Pass pre-loaded dataset to avoid duplicate query
    )
    
    return success_response(
        data={
            "columns": all_columns,
            "data_types": data_types,
            "preview_data": paginated_data.items,
            "row_count": paginated_data.total,
            "column_count": len(all_columns),
            "offset": pagination.offset,
            "limit": pagination.limit,
        }
    )


@router.put("/{dataset_id}/data")
async def update_dataset_data(
    dataset_id: UUID,
    data_update: DatasetDataUpdate,
    service: Annotated[DatasetService, Depends(get_dataset_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Update dataset preview data (require ownership or admin).
    
    WARNING: This endpoint updates multiple rows and should only be used for
    bulk operations like delete. For single row updates, use /data/row endpoint.
    """
    dataset = await service.update_dataset_data(dataset_id, data_update, user_id=current_user.id, is_admin=current_user.is_admin)
    return success_response(data=DatasetResponse.model_validate(_dataset_to_dict(dataset)).model_dump())


@router.put("/{dataset_id}/data/row")
async def update_single_row(
    dataset_id: UUID,
    row_update: DatasetRowUpdate,
    service: Annotated[DatasetService, Depends(get_dataset_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Update a single row in dataset (require ownership or admin).
    
    This is the recommended way to update data as it only affects one row.
    """
    dataset = await service.update_single_row(
        dataset_id,
        row_update.row_index,
        row_update.data,
        user_id=current_user.id,
        is_admin=current_user.is_admin
    )
    return success_response(data=DatasetResponse.model_validate(_dataset_to_dict(dataset)).model_dump())


@router.delete("/{dataset_id}/data/row")
async def delete_single_row(
    dataset_id: UUID,
    row_delete: DatasetRowDelete,
    service: Annotated[DatasetService, Depends(get_dataset_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Delete a single row from dataset (require ownership or admin)."""
    dataset = await service.delete_single_row(
        dataset_id,
        row_delete.row_index,
        user_id=current_user.id,
        is_admin=current_user.is_admin
    )
    return success_response(data=DatasetResponse.model_validate(_dataset_to_dict(dataset)).model_dump())


@router.post("/{dataset_id}/annotations/columns")
async def add_annotation_column(
    dataset_id: UUID,
    column_data: AnnotationColumnCreate,
    service: Annotated[DatasetService, Depends(get_dataset_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Add annotation column to dataset (require ownership or admin)."""
    dataset = await service.add_annotation_column(dataset_id, column_data, user_id=current_user.id, is_admin=current_user.is_admin)
    return success_response(data=DatasetResponse.model_validate(_dataset_to_dict(dataset)).model_dump())


@router.put("/{dataset_id}/annotations/columns")
async def update_annotation_column(
    dataset_id: UUID,
    column_data: AnnotationColumnUpdate,
    service: Annotated[DatasetService, Depends(get_dataset_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Update (rename) annotation column in dataset (require ownership or admin)."""
    dataset = await service.update_annotation_column(dataset_id, column_data, user_id=current_user.id, is_admin=current_user.is_admin)
    return success_response(data=DatasetResponse.model_validate(_dataset_to_dict(dataset)).model_dump())


@router.delete("/{dataset_id}/annotations/columns")
async def delete_annotation_column(
    dataset_id: UUID,
    column_data: AnnotationColumnDelete,
    service: Annotated[DatasetService, Depends(get_dataset_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Delete annotation column from dataset (require ownership or admin)."""
    dataset = await service.delete_annotation_column(dataset_id, column_data, user_id=current_user.id, is_admin=current_user.is_admin)
    return success_response(data=DatasetResponse.model_validate(_dataset_to_dict(dataset)).model_dump())


@router.get("/{dataset_id}/download/original")
async def download_original_file(
    dataset_id: UUID,
    service: Annotated[DatasetService, Depends(get_dataset_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Get presigned URL to download original file from MinIO (verify user access)."""
    url = await service.get_dataset_download_url(dataset_id, user_id=current_user.id, is_admin=current_user.is_admin)
    return success_response(data={"download_url": url})


@router.get("/{dataset_id}/export")
async def export_dataset(
    dataset_id: UUID,
    service: Annotated[DatasetService, Depends(get_dataset_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    format: str = "csv",  # "csv" or "jsonl"
) -> Response:
    """Export dataset with current data (including annotations) from PostgreSQL.
    
    Args:
        dataset_id: Dataset ID
        format: Export format, "csv" or "jsonl" (default: "csv")
    """
    content, filename, content_type = await service.export_dataset(dataset_id, user_id=current_user.id, is_admin=current_user.is_admin, format=format)
    
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
