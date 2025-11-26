"""Dataset service for business logic."""

from io import BytesIO
from typing import Optional
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import func, select, or_, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from diting_web.common.exceptions import ResourceNotFoundError
from diting_web.common.logging import get_logger
from diting_web.common.response import PaginatedResponse
from diting_web.models.dataset import Dataset, DatasetRow
from diting_web.schemas.dataset import (
    AnnotationColumnCreate,
    AnnotationColumnDelete,
    DatasetDataUpdate,
    DatasetResponse,
)
from diting_web.utils.dataset_parser import DatasetParser
from diting_web.utils.minio_client import get_minio_client

logger = get_logger(__name__)


def _dataset_to_dict(dataset: Dataset) -> dict:
    """Convert Dataset ORM object to dict, avoiding SQLAlchemy relationship fields.
    
    Args:
        dataset: Dataset ORM object
        
    Returns:
        Dictionary representation of dataset
    """
    return {
        "id": dataset.id,
        "name": dataset.name,
        "description": dataset.description,
        "file_path": dataset.file_path,
        "file_size": dataset.file_size,
        "file_type": dataset.file_type,
        "row_count": dataset.row_count,
        "columns": dataset.columns,
        "metadata": dataset.metadata_,
        "created_at": dataset.created_at,
        "updated_at": dataset.updated_at,
    }


class DatasetService:
    """Dataset service for business logic."""

    def __init__(self, db: AsyncSession):
        """Initialize dataset service.

        Args:
            db: Database session
        """
        self.db = db

    @staticmethod
    def _get_mime_type_from_extension(file_ext: str) -> Optional[str]:
        """Get MIME type from file extension.
        
        Args:
            file_ext: File extension with dot (e.g., '.jsonl', '.csv')
            
        Returns:
            MIME type string or None if not recognized
        """
        mime_types = {
            ".csv": "text/csv",
            ".jsonl": "application/x-ndjson",  # JSONL/NDJSON standard MIME type
            ".json": "application/json",
            ".xls": "application/vnd.ms-excel",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".txt": "text/plain",
        }
        return mime_types.get(file_ext.lower())

    async def create_dataset(
        self,
        name: str,
        description: Optional[str],
        file: UploadFile,
    ) -> Dataset:
        """Create a new dataset.

        Args:
            name: Dataset name
            description: Dataset description
            file: Uploaded file

        Returns:
            Created dataset with parsed metadata and file uploaded to MinIO
        """
        # Parse file to extract metadata and full data
        metadata = await DatasetParser.parse_file(file)
        
        # Parse full file for storing in PostgreSQL
        await file.seek(0)  # Reset file position
        import pandas as pd
        file_ext = DatasetParser._get_file_extension(file.filename or "")
        content = await file.read()
        
        # Parse full dataset
        if file_ext == ".csv":
            df = DatasetParser._read_csv_with_encoding(content)
        elif file_ext in {".xls", ".xlsx"}:
            df = pd.read_excel(BytesIO(content), engine="openpyxl")
        elif file_ext == ".jsonl":
            df = DatasetParser._read_jsonl(content)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
        
        # Convert to list of dicts
        df = df.where(pd.notnull(df), None)
        full_data = df.to_dict(orient="records")

        # Upload file to MinIO (for backup/download)
        await file.seek(0)  # Reset file position again
        minio_client = get_minio_client()
        object_name = await minio_client.upload_file(file)

        # Determine file type based on extension (more reliable than content_type)
        file_type = DatasetService._get_mime_type_from_extension(file_ext)
        if not file_type:
            # Fallback to content_type or default
            file_type = file.content_type or "application/octet-stream"

        # Create dataset with parsed information (without full_data in metadata)
        dataset = Dataset(
            name=name,
            description=description,
            file_path=object_name,  # MinIO object name (for backup/download)
            file_size=metadata["file_size"],
            file_type=file_type,
            row_count=len(full_data),
            columns={"columns": metadata["columns"]},  # Store column names
            metadata_={
                "column_count": metadata["column_count"],
                "data_types": metadata["data_types"],
                "preview_data": metadata["preview_data"],
                # Note: full_data is NOT stored in metadata anymore
                # Instead, each row is stored as a separate record in dataset_rows table
            },
        )
        self.db.add(dataset)
        await self.db.flush()  # Flush to get dataset.id
        
        # Insert each row into dataset_rows table
        rows = [
            DatasetRow(
                dataset_id=dataset.id,
                row_index=idx,
                data=row_data,
            )
            for idx, row_data in enumerate(full_data)
        ]
        self.db.add_all(rows)
        await self.db.commit()
        await self.db.refresh(dataset)

        logger.info(
            "Dataset created, parsed, and uploaded to MinIO",
            dataset_id=str(dataset.id),
            name=name,
            rows=len(full_data),
            columns=metadata["column_count"],
            object_name=object_name,
        )
        return dataset

    async def create_dataset_from_data(
        self,
        name: str,
        description: Optional[str],
        data: list[dict],
    ) -> Dataset:
        """Create a dataset from a list of data dictionaries (without file upload).

        Args:
            name: Dataset name
            description: Dataset description
            data: List of data dictionaries

        Returns:
            Created dataset

        Raises:
            ValueError: If data is empty
        """
        if not data:
            raise ValueError("Data cannot be empty")

        # Extract metadata from data
        import pandas as pd
        df = pd.DataFrame(data)
        
        # Get column names and types
        columns = list(df.columns)
        column_count = len(columns)
        row_count = len(data)
        
        data_types = {}
        for col in columns:
            dtype = str(df[col].dtype)
            if dtype == "object":
                data_types[col] = "string"
            elif dtype.startswith("int"):
                data_types[col] = "integer"
            elif dtype.startswith("float"):
                data_types[col] = "float"
            else:
                data_types[col] = dtype

        # Get preview data (first 100 rows)
        preview_data = df.head(100).to_dict(orient="records")

        # Create dataset
        dataset = Dataset(
            name=name,
            description=description,
            file_path=None,  # No file for data-created datasets
            file_size=None,
            file_type=None,
            row_count=row_count,
            columns={"columns": columns},
            metadata_={
                "column_count": column_count,
                "data_types": data_types,
                "preview_data": preview_data,
                "source": "synthesis_results",  # Mark as created from synthesis
            },
        )
        self.db.add(dataset)
        await self.db.flush()  # Flush to get dataset.id
        
        # Insert each row into dataset_rows table
        rows = [
            DatasetRow(
                dataset_id=dataset.id,
                row_index=idx,
                data=row_data,
            )
            for idx, row_data in enumerate(data)
        ]
        self.db.add_all(rows)
        await self.db.commit()
        await self.db.refresh(dataset)

        logger.info(
            "Dataset created from data",
            dataset_id=str(dataset.id),
            name=name,
            rows=row_count,
            columns=column_count,
        )
        return dataset

    async def get_datasets_list(
        self,
        offset: int = 0,
        limit: int = 20,
    ) -> PaginatedResponse[DatasetResponse]:
        """Get paginated list of datasets.

        Args:
            offset: Pagination offset
            limit: Pagination limit

        Returns:
            Paginated response with datasets
        """
        # Build query with noload to avoid loading relationships
        # This significantly improves performance when datasets have many rows or tasks
        query = select(Dataset).options(
            noload(Dataset.rows),
            noload(Dataset.tasks)
        ).order_by(Dataset.created_at.desc())

        # Get total count (optimized: count directly from table, not subquery)
        count_query = select(func.count(Dataset.id))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Get paginated items
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        items = result.scalars().all()

        # Calculate pagination info
        page = (offset // limit) + 1 if limit > 0 else 1
        page_size = limit

        # Create response
        return PaginatedResponse.create(
            items=[DatasetResponse.model_validate(_dataset_to_dict(item)).model_dump() for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_dataset_by_id(
        self,
        dataset_id: UUID,
        load_relationships: bool = False,
    ) -> Dataset:
        """Get dataset by ID.

        Args:
            dataset_id: Dataset ID
            load_relationships: Whether to load relationships (rows, tasks). Default False for performance.

        Returns:
            Dataset

        Raises:
            ResourceNotFoundError: If dataset not found
        """
        query = select(Dataset).where(Dataset.id == dataset_id)
        
        # Only load relationships if explicitly requested (for performance)
        if not load_relationships:
            query = query.options(
                noload(Dataset.rows),
                noload(Dataset.tasks)
            )
        
        result = await self.db.execute(query)
        dataset = result.scalar_one_or_none()

        if dataset is None:
            raise ResourceNotFoundError(
                "Dataset", str(dataset_id)
            )

        return dataset

    async def delete_dataset(
        self,
        dataset_id: UUID,
    ) -> None:
        """Delete dataset and associated file from MinIO.

        Args:
            dataset_id: Dataset ID

        Raises:
            ResourceNotFoundError: If dataset not found
        """
        # Get dataset
        dataset = await self.get_dataset_by_id(dataset_id)

        # Delete file from MinIO if exists
        if dataset.file_path:
            try:
                minio_client = get_minio_client()
                minio_client.delete_file(dataset.file_path)
                logger.info("File deleted from MinIO", object_name=dataset.file_path)
            except Exception as e:
                logger.warning(
                    "Failed to delete file from MinIO, continuing with dataset deletion",
                    error=str(e),
                )

        # TODO: Check if dataset is being used by running tasks

        # Delete dataset record
        await self.db.delete(dataset)
        await self.db.commit()

        logger.info("Dataset deleted", dataset_id=str(dataset_id))

    async def get_dataset_download_url(
        self,
        dataset_id: UUID,
    ) -> str:
        """Get presigned download URL for dataset file.

        Args:
            dataset_id: Dataset ID

        Returns:
            Presigned download URL

        Raises:
            ResourceNotFoundError: If dataset not found or file not exists
        """
        dataset = await self.get_dataset_by_id(dataset_id)

        if not dataset.file_path:
            raise ResourceNotFoundError("Dataset file", str(dataset_id))

        minio_client = get_minio_client()
        url = minio_client.get_presigned_url(dataset.file_path)

        logger.info(
            "Generated download URL",
            dataset_id=str(dataset_id),
            object_name=dataset.file_path,
        )
        return url

    async def update_dataset_data(
        self,
        dataset_id: UUID,
        data_update: DatasetDataUpdate,
    ) -> Dataset:
        """Update dataset data in dataset_rows table.
        
        Updates the data in dataset_rows table directly.

        Args:
            dataset_id: Dataset ID
            data_update: Updated data and row count

        Returns:
            Updated dataset

        Raises:
            ResourceNotFoundError: If dataset not found
        """
        dataset = await self.get_dataset_by_id(dataset_id)

        # Update rows in dataset_rows table
        # The preview_data contains the updated rows with their data
        if data_update.preview_data:
            # Get original columns for matching (if needed)
            original_columns = dataset.columns.get("columns", []) if dataset.columns else []
            
            for preview_row in data_update.preview_data:
                # Try to find matching row in dataset_rows using row_index or content matching
                # For now, we'll use a simple approach: match by row_index if available
                # or use content matching
                
                # Try to find by matching content (using original columns)
                best_match_row = None
                best_match_score = 0
                
                query = select(DatasetRow).where(DatasetRow.dataset_id == dataset_id)
                result = await self.db.execute(query)
                all_rows = result.scalars().all()
                
                for row in all_rows:
                    match_score = self._calculate_row_match_score(
                        row.data, preview_row, original_columns
                    )
                    if match_score > best_match_score and match_score >= 0.8:
                        best_match_score = match_score
                        best_match_row = row
                
                # Update the matched row
                if best_match_row:
                    best_match_row.data = preview_row.copy()
                else:
                    # Fallback: if can't match, try to update by index in preview_data
                    preview_idx = data_update.preview_data.index(preview_row)
                    query = select(DatasetRow).where(
                        DatasetRow.dataset_id == dataset_id,
                        DatasetRow.row_index == preview_idx
                    )
                    result = await self.db.execute(query)
                    row = result.scalar_one_or_none()
                    if row:
                        row.data = preview_row.copy()
        
        # Update row count if provided
        if data_update.row_count is not None:
            dataset.row_count = data_update.row_count
        else:
            # Count rows from dataset_rows table
            count_query = select(func.count()).select_from(
                select(DatasetRow).where(DatasetRow.dataset_id == dataset_id).subquery()
            )
            dataset.row_count = await self.db.scalar(count_query) or 0

        await self.db.commit()
        await self.db.refresh(dataset)

        logger.info(
            "Dataset data updated in dataset_rows table",
            dataset_id=str(dataset_id),
            updated_rows=len(data_update.preview_data) if data_update.preview_data else 0,
        )
        return dataset

    def _calculate_row_match_score(self, row1: dict, row2: dict, key_columns: list[str]) -> float:
        """Calculate match score between two rows using key columns.
        
        Args:
            row1: First row
            row2: Second row
            key_columns: List of column names to use for matching
            
        Returns:
            Match score between 0.0 and 1.0
        """
        if not row1 or not row2 or not key_columns:
            return 0.0
        
        matches = 0
        total = 0
        
        for col in key_columns:
            if col in row1 and col in row2:
                total += 1
                # Compare values (handle lists/arrays)
                val1 = row1[col]
                val2 = row2[col]
                
                if isinstance(val1, list) and isinstance(val2, list):
                    # For lists, compare sorted versions
                    if sorted(val1) == sorted(val2):
                        matches += 1
                elif val1 == val2:
                    matches += 1
        
        return matches / total if total > 0 else 0.0

    def _rows_match(self, row1: dict, row2: dict, threshold: float = 0.5) -> bool:
        """Check if two rows match (for updating purposes).
        
        Args:
            row1: First row
            row2: Second row
            threshold: Minimum match ratio (default 0.5)
            
        Returns:
            True if rows match
        """
        if not row1 or not row2:
            return False
        
        # Get common keys
        keys1 = set(row1.keys())
        keys2 = set(row2.keys())
        common_keys = keys1 & keys2
        
        if not common_keys:
            return False
        
        # Compare values
        matches = 0
        for key in common_keys:
            if row1[key] == row2[key]:
                matches += 1
        
        match_ratio = matches / len(common_keys) if common_keys else 0
        return match_ratio >= threshold

    async def add_annotation_column(
        self,
        dataset_id: UUID,
        column_data: AnnotationColumnCreate,
    ) -> Dataset:
        """Add annotation column to dataset.

        Args:
            dataset_id: Dataset ID
            column_data: Annotation column data

        Returns:
            Updated dataset

        Raises:
            ResourceNotFoundError: If dataset not found
            ResourceConflictError: If column already exists
        """
        dataset = await self.get_dataset_by_id(dataset_id)

        # Initialize metadata if needed
        if dataset.metadata_ is None:
            dataset.metadata_ = {}

        # Initialize annotation_columns if not exists
        if "annotation_columns" not in dataset.metadata_:
            dataset.metadata_["annotation_columns"] = []

        # Check if column already exists
        existing_columns = dataset.metadata_["annotation_columns"]
        if any(col["column_name"] == column_data.column_name for col in existing_columns):
            from diting_web.common.exceptions import ResourceConflictError
            raise ResourceConflictError(
                f"Annotation column '{column_data.column_name}' already exists"
            )

        # Add new annotation column
        new_column = {
            "column_name": column_data.column_name,
            "column_type": column_data.column_type,
            "description": column_data.description,
            "options": column_data.options,
        }
        dataset.metadata_["annotation_columns"].append(new_column)

        # Add empty annotation data to all existing rows in dataset_rows table
        # Use PostgreSQL JSONB function to update all rows efficiently
        from sqlalchemy import text
        update_query = text(
            "UPDATE dataset_rows SET data = jsonb_set(data, :column_path, '""', false) "
            "WHERE dataset_id = :dataset_id"
        ).bindparams(
            column_path=f'{{{column_data.column_name}}}',
            dataset_id=str(dataset_id)
        )
        await self.db.execute(update_query)

        await self.db.commit()
        await self.db.refresh(dataset)

        logger.info(
            "Annotation column added",
            dataset_id=str(dataset_id),
            column_name=column_data.column_name,
        )
        return dataset

    async def delete_annotation_column(
        self,
        dataset_id: UUID,
        column_data: AnnotationColumnDelete,
    ) -> Dataset:
        """Delete annotation column from dataset.

        Args:
            dataset_id: Dataset ID
            column_data: Column to delete

        Returns:
            Updated dataset

        Raises:
            ResourceNotFoundError: If dataset or column not found
        """
        dataset = await self.get_dataset_by_id(dataset_id)

        if dataset.metadata_ is None or "annotation_columns" not in dataset.metadata_:
            from diting_web.common.exceptions import ResourceNotFoundError
            raise ResourceNotFoundError(
                "Annotation columns",
                f"No annotation columns in dataset {dataset_id}"
            )

        # Find and remove the column
        annotation_columns = dataset.metadata_["annotation_columns"]
        column_index = next(
            (i for i, col in enumerate(annotation_columns) 
             if col["column_name"] == column_data.column_name),
            None
        )

        if column_index is None:
            from diting_web.common.exceptions import ResourceNotFoundError
            raise ResourceNotFoundError(
                "Annotation column",
                column_data.column_name
            )

        # Remove column metadata
        dataset.metadata_["annotation_columns"].pop(column_index)

        # Remove column data from all rows in dataset_rows table using JSONB operation
        from sqlalchemy import text
        update_query = text(
            "UPDATE dataset_rows SET data = data - :column_name "
            "WHERE dataset_id = :dataset_id"
        ).bindparams(
            column_name=column_data.column_name,
            dataset_id=str(dataset_id)
        )
        await self.db.execute(update_query)

        await self.db.commit()
        await self.db.refresh(dataset)

        logger.info(
            "Annotation column deleted",
            dataset_id=str(dataset_id),
            column_name=column_data.column_name,
        )
        return dataset

    async def export_dataset(
        self,
        dataset_id: UUID,
        format: str = "csv",
    ) -> tuple[bytes, str, str]:
        """Export dataset with current data (including annotations) from dataset_rows table.
        
        Exports data from dataset_rows table, which includes all edits and annotations.
        This is different from downloading the original file from MinIO.

        Args:
            dataset_id: Dataset ID
            format: Export format, "csv" or "jsonl" (default: "csv")

        Returns:
            Tuple of (file_content, filename, content_type)

        Raises:
            ResourceNotFoundError: If dataset not found
            ValueError: If format is invalid or no data to export
        """
        dataset = await self.get_dataset_by_id(dataset_id)

        # Query all rows from dataset_rows table
        query = select(DatasetRow).where(
            DatasetRow.dataset_id == dataset_id
        ).order_by(DatasetRow.row_index)
        
        result = await self.db.execute(query)
        rows = result.scalars().all()
        
        # Extract data from rows
        full_data = [row.data for row in rows]
        
        if not full_data:
            raise ValueError("No data to export")

        # Validate format
        if format not in ["csv", "jsonl"]:
            raise ValueError(f"Invalid format: {format}. Must be 'csv' or 'jsonl'")

        if format == "jsonl":
            # Export as JSONL
            import json
            lines = [json.dumps(row, ensure_ascii=False) for row in full_data]
            content = "\n".join(lines).encode("utf-8")
            filename = f"{dataset.name}_exported.jsonl"
            content_type = "application/jsonl"
        else:
            # Export as CSV
            import csv
            import io
            
            # Get all columns (including annotation columns)
            columns = list(full_data[0].keys()) if full_data else []
            
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=columns)
            writer.writeheader()
            writer.writerows(full_data)
            
            content = output.getvalue().encode("utf-8")
            filename = f"{dataset.name}_exported.csv"
            content_type = "text/csv"

        logger.info(
            "Dataset exported from dataset_rows table",
            dataset_id=str(dataset_id),
            rows=len(full_data),
            format=format,
        )
        
        return content, filename, content_type

    async def get_dataset_data_paginated(
        self,
        dataset_id: UUID,
        offset: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        dataset: Optional[Dataset] = None,
    ) -> PaginatedResponse[dict]:
        """Get paginated dataset data from dataset_rows table.
        
        This method queries data directly from dataset_rows table,
        supporting database-level search and pagination for better performance.
        
        Args:
            dataset_id: Dataset ID
            offset: Number of records to skip
            limit: Maximum number of records to return
            search: Optional search keyword to filter data across all columns
            dataset: Optional pre-loaded Dataset object to avoid duplicate query
            
        Returns:
            Paginated response with dataset rows
            
        Raises:
            ResourceNotFoundError: If dataset not found
        """
        # Only query dataset if not provided (avoid duplicate query)
        if dataset is None:
            dataset = await self.get_dataset_by_id(dataset_id, load_relationships=False)
        
        # Build base query
        query = select(DatasetRow).where(DatasetRow.dataset_id == dataset_id)
        
        # Apply search filter if provided (database-level search)
        if search:
            search_lower = search.lower().strip()
            # Use PostgreSQL JSONB query to search across all column values and keys
            # jsonb_each_text expands the JSONB object into key-value pairs
            # We search in both keys (column names) and values (cell content)
            # This handles nested structures by converting them to text
            from sqlalchemy import text
            search_condition = text(
                "EXISTS ("
                "SELECT 1 FROM jsonb_each_text(dataset_rows.data) AS kv "
                "WHERE LOWER(kv.key) LIKE :search_pattern OR LOWER(kv.value) LIKE :search_pattern"
                ")"
            ).bindparams(search_pattern=f"%{search_lower}%")
            query = query.where(search_condition)
            
            logger.info(
                "Search filter applied (database-level, searches keys and values)",
                dataset_id=str(dataset_id),
                search_term=search,
            )
        
        # Order by row_index to maintain original order
        query = query.order_by(DatasetRow.row_index)
        
        # Get total count (optimized: use count() directly instead of subquery when no search)
        if search:
            # When searching, need to use subquery for accurate count
            count_query = select(func.count()).select_from(query.subquery())
        else:
            # When not searching, count directly from table (much faster)
            count_query = select(func.count(DatasetRow.id)).where(DatasetRow.dataset_id == dataset_id)
        total_count = await self.db.scalar(count_query) or 0
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        # Execute query
        result = await self.db.execute(query)
        rows = result.scalars().all()
        
        # Extract data from rows
        items = [row.data for row in rows]
        
        # Calculate page and pages
        page = (offset // limit) + 1 if limit > 0 else 1
        pages = (total_count + limit - 1) // limit if limit > 0 else 0
        
        logger.info(
            "Dataset data queried from dataset_rows table",
            dataset_id=str(dataset_id),
            total_rows=total_count,
            returned_rows=len(items),
            offset=offset,
            limit=limit,
        )
        
        return PaginatedResponse(
            items=items,
            total=total_count,
            page=page,
            page_size=limit,
            pages=pages,
        )
