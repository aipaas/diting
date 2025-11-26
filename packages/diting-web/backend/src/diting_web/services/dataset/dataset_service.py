"""Dataset service for business logic."""

from io import BytesIO
from typing import Optional
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import func, select, or_, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload, selectinload
from sqlalchemy.orm.attributes import flag_modified

from diting_web.common.exceptions import ResourceNotFoundError
from diting_web.common.logging import get_logger
from diting_web.common.response import PaginatedResponse
from diting_web.models.dataset import Dataset, DatasetRow
from diting_web.schemas.dataset import (
    AnnotationColumnCreate,
    AnnotationColumnDelete,
    AnnotationColumnUpdate,
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
    from sqlalchemy import inspect as sa_inspect
    
    result = {
        "id": dataset.id,
        "name": dataset.name,
        "description": dataset.description,
        "created_by": dataset.created_by,
        "file_path": dataset.file_path,
        "file_size": dataset.file_size,
        "file_type": dataset.file_type,
        "row_count": dataset.row_count,
        "columns": dataset.columns,
        "metadata": dataset.metadata_,
        "created_at": dataset.created_at,
        "updated_at": dataset.updated_at,
    }
    
    # Include creator info if loaded (check without triggering lazy load)
    insp = sa_inspect(dataset)
    if 'creator' in insp.unloaded:
        # Creator not loaded, skip it
        pass
    else:
        # Creator is loaded, safe to access
        creator = dataset.creator
        if creator:
            result["creator"] = {
                "id": str(creator.id),
                "username": creator.username,
                "email": creator.email,
            }
    
    return result


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
        created_by: UUID,
    ) -> Dataset:
        """Create a new dataset (user-level).

        Args:
            name: Dataset name
            description: Dataset description
            file: Uploaded file
            project_id: Project ID
            created_by: Creator user ID

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

        # Create dataset with parsed information (Multi-tenancy)
        dataset = Dataset(
            name=name,
            description=description,
            created_by=created_by,  # Simplified
            file_path=object_name,  # MinIO object name (for backup/download)
            file_size=metadata["file_size"],
            file_type=file_type,
            row_count=len(full_data),
            columns={"columns": metadata["columns"]},  # Store column names
            metadata_={
                "column_count": metadata["column_count"],
                "data_types": metadata["data_types"],
                # Note: preview_data removed - all data queried from dataset_rows table
                # No need to duplicate data in metadata
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
        created_by: UUID,
    ) -> Dataset:
        """Create a dataset from a list of data dictionaries (without file upload).

        Args:
            name: Dataset name
            description: Dataset description
            data: List of data dictionaries
            created_by: Creator user ID

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

        # Create dataset (Multi-tenancy)
        dataset = Dataset(
            name=name,
            description=description,
            created_by=created_by,  # Simplified
            file_path=None,  # No file for data-created datasets
            file_size=None,
            file_type=None,
            row_count=row_count,
            columns={"columns": columns},
            metadata_={
                "column_count": column_count,
                "data_types": data_types,
                "source": "synthesis_results",  # Mark as created from synthesis
                # Note: preview_data removed - all data queried from dataset_rows table
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
        user_id: UUID,
        is_admin: bool,
        offset: int = 0,
        limit: int = 20,
    ) -> PaginatedResponse[DatasetResponse]:
        """Get paginated list of datasets (filtered by user access).

        Args:
            user_id: User ID for filtering (non-admin users see only their datasets)
            is_admin: Whether user is admin (admins see all datasets)
            offset: Pagination offset
            limit: Pagination limit

        Returns:
            Paginated response with datasets
        """
        # Build query with noload to avoid loading relationships
        # This significantly improves performance when datasets have many rows or tasks
        # Load creator info for display purposes
        query = select(Dataset).options(
            noload(Dataset.rows),
            noload(Dataset.tasks),
            selectinload(Dataset.creator)
        )
        
        # Apply user-based filtering: non-admin users only see their own datasets
        if not is_admin:
            query = query.where(Dataset.created_by == user_id)
        
        query = query.order_by(Dataset.created_at.desc())

        # Get total count (optimized: count directly from table, not subquery)
        count_query = select(func.count(Dataset.id))
        if not is_admin:
            count_query = count_query.where(Dataset.created_by == user_id)
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
        user_id: Optional[UUID] = None,
        is_admin: Optional[bool] = None,
        load_relationships: bool = False,
    ) -> Dataset:
        """Get dataset by ID (with user-level access control).

        Args:
            dataset_id: Dataset ID
            user_id: User ID for access control (optional, if None no access check)
            is_admin: Whether user is admin (optional, if None no access check)
            load_relationships: Whether to load relationships (rows, tasks). Default False for performance.

        Returns:
            Dataset

        Raises:
            ResourceNotFoundError: If dataset not found or no access
        """
        query = select(Dataset).where(Dataset.id == dataset_id)
        
        # Apply user-based access control if user_id is provided
        if user_id is not None and not is_admin:
            query = query.where(Dataset.created_by == user_id)
        
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
        user_id: UUID,
        is_admin: bool,
    ) -> None:
        """Delete dataset and associated file from MinIO.

        Args:
            dataset_id: Dataset ID
            user_id: User ID for access control
            is_admin: Whether user is admin

        Raises:
            ResourceNotFoundError: If dataset not found or no access
        """
        # Get dataset (with access control)
        dataset = await self.get_dataset_by_id(dataset_id, user_id=user_id, is_admin=is_admin)

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
        user_id: UUID,
        is_admin: bool,
    ) -> str:
        """Get presigned download URL for dataset file.

        Args:
            dataset_id: Dataset ID
            user_id: User ID for access control
            is_admin: Whether user is admin

        Returns:
            Presigned download URL

        Raises:
            ResourceNotFoundError: If dataset not found or file not exists
        """
        dataset = await self.get_dataset_by_id(dataset_id, user_id=user_id, is_admin=is_admin)

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
        user_id: UUID,
        is_admin: bool,
    ) -> Dataset:
        """Update dataset data in dataset_rows table.
        
        Updates the data in dataset_rows table directly.

        Args:
            dataset_id: Dataset ID
            data_update: Updated data and row count
            user_id: User ID for access control
            is_admin: Whether user is admin

        Returns:
            Updated dataset

        Raises:
            ResourceNotFoundError: If dataset not found or no access
        """
        dataset = await self.get_dataset_by_id(dataset_id, user_id=user_id, is_admin=is_admin)

        # Update rows in dataset_rows table
        # The preview_data contains the updated rows with their data
        if data_update.preview_data:
            # PERFORMANCE FIX: Query all rows once instead of N times (避免 O(n²) 查询)
            # Build index of all existing rows by row_index for fast lookup
            query = select(DatasetRow).where(DatasetRow.dataset_id == dataset_id)
            result = await self.db.execute(query)
            all_rows_list = result.scalars().all()
            
            # Create multiple indexes for different matching strategies
            rows_by_index: dict[int, DatasetRow] = {}
            rows_by_content_hash: dict[str, DatasetRow] = {}
            
            # Get original columns for content-based matching
            original_columns = dataset.columns.get("columns", []) if dataset.columns else []
            
            for row in all_rows_list:
                # Index by row_index (primary strategy)
                rows_by_index[row.row_index] = row
                
                # Index by content hash (fallback strategy for reordered data)
                if original_columns:
                    # Create a stable hash from key columns
                    key_values = []
                    for col in original_columns[:3]:  # Use first 3 columns as key
                        if col in row.data:
                            val = row.data[col]
                            # Handle lists by converting to sorted tuple
                            if isinstance(val, list):
                                key_values.append(str(tuple(sorted(str(v) for v in val))))
                            else:
                                key_values.append(str(val))
                    if key_values:
                        content_hash = "|".join(key_values)
                        rows_by_content_hash[content_hash] = row
            
            logger.info(
                "Dataset rows loaded for update",
                dataset_id=str(dataset_id),
                total_rows=len(all_rows_list),
                preview_data_count=len(data_update.preview_data),
            )
            
            # Now update each preview_row using the pre-built indexes
            for preview_idx, preview_row in enumerate(data_update.preview_data):
                target_row = None
                
                # Strategy 1: Match by row_index (most reliable)
                if preview_idx in rows_by_index:
                    target_row = rows_by_index[preview_idx]
                    logger.debug(
                        "Matched by row_index",
                        preview_idx=preview_idx,
                        row_id=str(target_row.id),
                    )
                
                # Strategy 2: Match by content hash (for reordered data)
                elif original_columns:
                    key_values = []
                    for col in original_columns[:3]:
                        if col in preview_row:
                            val = preview_row[col]
                            if isinstance(val, list):
                                key_values.append(str(tuple(sorted(str(v) for v in val))))
                            else:
                                key_values.append(str(val))
                    if key_values:
                        content_hash = "|".join(key_values)
                        if content_hash in rows_by_content_hash:
                            target_row = rows_by_content_hash[content_hash]
                            logger.debug(
                                "Matched by content hash",
                                preview_idx=preview_idx,
                                content_hash=content_hash[:50],
                                row_id=str(target_row.id),
                            )
                
                # Strategy 3: Fallback to similarity matching (expensive but rare)
                if not target_row and original_columns:
                    best_match_row = None
                    best_match_score = 0
                    
                    for row in all_rows_list:
                        match_score = self._calculate_row_match_score(
                            row.data, preview_row, original_columns
                        )
                        if match_score > best_match_score and match_score >= 0.8:
                            best_match_score = match_score
                            best_match_row = row
                    
                    if best_match_row:
                        target_row = best_match_row
                        logger.debug(
                            "Matched by similarity",
                            preview_idx=preview_idx,
                            match_score=best_match_score,
                            row_id=str(target_row.id),
                        )
                
                # Update the matched row
                if target_row:
                    target_row.data = preview_row.copy()
                    target_row.row_index = preview_idx  # Update row_index to maintain order
                else:
                    logger.warning(
                        "No matching row found for preview data",
                        preview_idx=preview_idx,
                        dataset_id=str(dataset_id),
                    )
        
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

    async def update_single_row(
        self,
        dataset_id: UUID,
        row_index: int,
        row_data: dict,
        user_id: UUID,
        is_admin: bool,
    ) -> Dataset:
        """Update a single row in dataset_rows table.
        
        This is safer than update_dataset_data as it only updates one row.
        
        Args:
            dataset_id: Dataset ID
            row_index: Row index to update (0-based)
            row_data: Updated row data
            user_id: User ID for access control
            is_admin: Whether user is admin
            
        Returns:
            Updated dataset
            
        Raises:
            ResourceNotFoundError: If dataset or row not found
        """
        dataset = await self.get_dataset_by_id(dataset_id, user_id=user_id, is_admin=is_admin)
        
        # Find the row by row_index
        query = select(DatasetRow).where(
            DatasetRow.dataset_id == dataset_id,
            DatasetRow.row_index == row_index
        )
        result = await self.db.execute(query)
        row = result.scalar_one_or_none()
        
        if not row:
            raise ResourceNotFoundError("Dataset row", f"{dataset_id}[{row_index}]")
        
        # Update the row
        row.data = row_data
        
        await self.db.commit()
        await self.db.refresh(dataset)
        
        logger.info(
            "Single dataset row updated",
            dataset_id=str(dataset_id),
            row_index=row_index,
        )
        return dataset

    async def delete_single_row(
        self,
        dataset_id: UUID,
        row_index: int,
        user_id: UUID,
        is_admin: bool,
    ) -> Dataset:
        """Delete a single row from dataset_rows table.
        
        Args:
            dataset_id: Dataset ID
            row_index: Row index to delete (0-based)
            user_id: User ID for access control
            is_admin: Whether user is admin
            
        Returns:
            Updated dataset
            
        Raises:
            ResourceNotFoundError: If dataset or row not found
        """
        dataset = await self.get_dataset_by_id(dataset_id, user_id=user_id, is_admin=is_admin)
        
        # Find the row by row_index
        query = select(DatasetRow).where(
            DatasetRow.dataset_id == dataset_id,
            DatasetRow.row_index == row_index
        )
        result = await self.db.execute(query)
        row = result.scalar_one_or_none()
        
        if not row:
            raise ResourceNotFoundError("Dataset row", f"{dataset_id}[{row_index}]")
        
        # Delete the row
        await self.db.delete(row)
        await self.db.commit()
        
        # Update row_index for all rows after this one
        # Use two-step update to avoid unique constraint violations:
        # Step 1: Move affected rows to negative indices (guaranteed unique)
        # Step 2: Move them back to correct positive indices
        from sqlalchemy import text
        
        # Step 1: Update to negative indices temporarily
        temp_update_stmt = text(
            "UPDATE dataset_rows "
            "SET row_index = -row_index "
            "WHERE dataset_id = CAST(:dataset_id AS UUID) AND row_index > :row_index"
        ).bindparams(
            dataset_id=str(dataset_id),
            row_index=row_index
        )
        await self.db.execute(temp_update_stmt)
        
        # Step 2: Update negative indices to correct positive values
        final_update_stmt = text(
            "UPDATE dataset_rows "
            "SET row_index = -row_index - 1 "
            "WHERE dataset_id = CAST(:dataset_id AS UUID) AND row_index < 0"
        ).bindparams(
            dataset_id=str(dataset_id)
        )
        await self.db.execute(final_update_stmt)
        
        # Update dataset row count
        dataset.row_count = dataset.row_count - 1 if dataset.row_count > 0 else 0
        
        await self.db.commit()
        await self.db.refresh(dataset)
        
        logger.info(
            "Single dataset row deleted",
            dataset_id=str(dataset_id),
            row_index=row_index,
            new_row_count=dataset.row_count,
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
        user_id: UUID,
        is_admin: bool,
    ) -> Dataset:
        """Add annotation column to dataset.

        Args:
            dataset_id: Dataset ID
            column_data: Annotation column data
            user_id: User ID for access control
            is_admin: Whether user is admin

        Returns:
            Updated dataset

        Raises:
            ResourceNotFoundError: If dataset not found or no access
            ResourceConflictError: If column already exists
        """
        dataset = await self.get_dataset_by_id(dataset_id, user_id=user_id, is_admin=is_admin)

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
        # Also prevent conflict with original columns
        original_columns = dataset.columns.get("columns", []) if dataset.columns else []
        if column_data.column_name in original_columns:
            from diting_web.common.exceptions import ResourceConflictError
            raise ResourceConflictError(
                f"Column '{column_data.column_name}' already exists in original columns"
            )

        # Add new annotation column
        new_column = {
            "column_name": column_data.column_name,
            "column_type": column_data.column_type,
            "description": column_data.description,
            "options": column_data.options,
        }
        dataset.metadata_["annotation_columns"].append(new_column)
        # Ensure SQLAlchemy persists JSONB in-place mutations
        flag_modified(dataset, "metadata_")

        # Recompute and store column_count (original + annotations)
        dataset.metadata_["column_count"] = len(original_columns) + len(dataset.metadata_["annotation_columns"])
        flag_modified(dataset, "metadata_")

        # Add empty annotation data to all existing rows in dataset_rows table
        # Use PostgreSQL JSONB function to update all rows efficiently
        from sqlalchemy import text
        update_query = text(
            "UPDATE dataset_rows SET data = jsonb_set(data, CAST(:column_path AS text[]), '\"\"'::jsonb, true) "
            "WHERE dataset_id = CAST(:dataset_id AS UUID)"
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

    async def update_annotation_column(
        self,
        dataset_id: UUID,
        column_data: AnnotationColumnUpdate,
        user_id: UUID,
        is_admin: bool,
    ) -> Dataset:
        """Update (rename) column in dataset (supports both original and annotation columns).

        Args:
            dataset_id: Dataset ID
            column_data: Column update data
            user_id: User ID for access control
            is_admin: Whether user is admin

        Returns:
            Updated dataset

        Raises:
            ResourceNotFoundError: If dataset or column not found or no access
            ResourceConflictError: If new column name already exists
        """
        dataset = await self.get_dataset_by_id(dataset_id, user_id=user_id, is_admin=is_admin)

        # Build current column sets from original and annotations
        original_columns = dataset.columns.get("columns", []) if dataset.columns else []
        annotation_columns = dataset.metadata_.get("annotation_columns", [])
        annotation_names = [col["column_name"] for col in annotation_columns]
        all_columns = set(original_columns + annotation_names)
        
        # Check if column exists
        if column_data.old_column_name not in all_columns:
            from diting_web.common.exceptions import ResourceNotFoundError
            raise ResourceNotFoundError(
                "Column",
                column_data.old_column_name
            )

        # Check if new column name already exists (if renaming)
        if column_data.old_column_name != column_data.new_column_name:
            if column_data.new_column_name in all_columns:
                from diting_web.common.exceptions import ResourceConflictError
                raise ResourceConflictError(
                    f"Column '{column_data.new_column_name}' already exists"
                )

        # Initialize metadata if needed
        if dataset.metadata_ is None:
            dataset.metadata_ = {}
        if "annotation_columns" not in dataset.metadata_:
            dataset.metadata_["annotation_columns"] = []

        # Determine if this is an annotation column
        annotation_columns = dataset.metadata_["annotation_columns"]
        column_index = next(
            (i for i, col in enumerate(annotation_columns) 
             if col["column_name"] == column_data.old_column_name),
            None
        )
        is_annotation_column = column_index is not None

        # Update column metadata (only for annotation columns)
        if is_annotation_column:
            existing_column = annotation_columns[column_index]
            annotation_columns[column_index] = {
                "column_name": column_data.new_column_name,
                "column_type": column_data.column_type if column_data.column_type is not None else existing_column.get("column_type", "text"),
                "description": column_data.description if column_data.description is not None else existing_column.get("description"),
                "options": column_data.options if column_data.options is not None else existing_column.get("options"),
            }
            # Persist metadata JSONB changes
            flag_modified(dataset, "metadata_")
            logger.info(
                "Updating annotation column metadata",
                old_name=column_data.old_column_name,
                new_name=column_data.new_column_name,
            )

        # If column name changed, rename the key in all rows using PostgreSQL JSONB operation
        if column_data.old_column_name != column_data.new_column_name:
            from sqlalchemy import text
            # PostgreSQL JSONB operation to rename a key:
            # 1. Add new key with value from old key
            # 2. Remove old key
            update_query = text(
                "UPDATE dataset_rows "
                "SET data = (data - :old_name) || jsonb_build_object(:new_name, data->:old_name) "
                "WHERE dataset_id = CAST(:dataset_id AS UUID) AND data ? :old_name"
            ).bindparams(
                old_name=column_data.old_column_name,
                new_name=column_data.new_column_name,
                dataset_id=str(dataset_id)
            )
            await self.db.execute(update_query)

            # If this is an original column, update in columns array
            if not is_annotation_column and dataset.columns and "columns" in dataset.columns:
                columns_list = dataset.columns["columns"]
                if column_data.old_column_name in columns_list:
                    idx = columns_list.index(column_data.old_column_name)
                    columns_list[idx] = column_data.new_column_name
                    dataset.columns = {"columns": columns_list}
                    flag_modified(dataset, "columns")

        # Recompute and store column_count
        dataset.metadata_["column_count"] = len(original_columns) + len(dataset.metadata_["annotation_columns"])
        flag_modified(dataset, "metadata_")

        await self.db.commit()
        await self.db.refresh(dataset)

        logger.info(
            "Column updated",
            dataset_id=str(dataset_id),
            old_column_name=column_data.old_column_name,
            new_column_name=column_data.new_column_name,
            is_annotation=is_annotation_column,
        )
        return dataset

    async def delete_annotation_column(
        self,
        dataset_id: UUID,
        column_data: AnnotationColumnDelete,
        user_id: UUID,
        is_admin: bool,
    ) -> Dataset:
        """Delete a column from dataset (supports original and annotation columns).

        Args:
            dataset_id: Dataset ID
            column_data: Column to delete
            user_id: User ID for access control
            is_admin: Whether user is admin

        Returns:
            Updated dataset

        Raises:
            ResourceNotFoundError: If dataset or column not found or no access
        """
        dataset = await self.get_dataset_by_id(dataset_id, user_id=user_id, is_admin=is_admin)

        # Ensure metadata structure
        if dataset.metadata_ is None:
            dataset.metadata_ = {}
        if "annotation_columns" not in dataset.metadata_:
            dataset.metadata_["annotation_columns"] = []

        # Determine if the target is an annotation column
        annotation_columns = dataset.metadata_["annotation_columns"]
        column_index = next(
            (i for i, col in enumerate(annotation_columns)
             if col["column_name"] == column_data.column_name),
            None
        )
        is_annotation_column = column_index is not None

        if is_annotation_column:
            # Remove metadata for annotation column
            dataset.metadata_["annotation_columns"].pop(column_index)
            flag_modified(dataset, "metadata_")
        else:
            # Remove from original columns list
            if not dataset.columns or "columns" not in dataset.columns:
                from diting_web.common.exceptions import ResourceNotFoundError
                raise ResourceNotFoundError("Column", column_data.column_name)
            columns_list = dataset.columns["columns"]
            if column_data.column_name not in columns_list:
                from diting_web.common.exceptions import ResourceNotFoundError
                raise ResourceNotFoundError("Column", column_data.column_name)
            columns_list.remove(column_data.column_name)
            dataset.columns = {"columns": columns_list}
            flag_modified(dataset, "columns")
            # Also drop data_types entry if present
            data_types = dataset.metadata_.get("data_types")
            if isinstance(data_types, dict) and column_data.column_name in data_types:
                data_types.pop(column_data.column_name, None)
                dataset.metadata_["data_types"] = data_types
                flag_modified(dataset, "metadata_")

        # Safety: ensure the column is not left over in columns list (e.g., historical data)
        if dataset.columns and "columns" in dataset.columns:
            columns_list = dataset.columns["columns"]
            if column_data.column_name in columns_list:
                columns_list.remove(column_data.column_name)
                dataset.columns = {"columns": columns_list}
                flag_modified(dataset, "columns")

        # Remove column data from all rows in dataset_rows table using JSONB operation
        from sqlalchemy import text
        update_query = text(
            "UPDATE dataset_rows SET data = data - :column_name "
            "WHERE dataset_id = CAST(:dataset_id AS UUID)"
        ).bindparams(
            column_name=column_data.column_name,
            dataset_id=str(dataset_id)
        )
        await self.db.execute(update_query)

        # Recompute and store column_count after deletion
        original_columns = dataset.columns.get("columns", []) if dataset.columns else []
        dataset.metadata_["column_count"] = len(original_columns) + len(dataset.metadata_["annotation_columns"])
        flag_modified(dataset, "metadata_")

        await self.db.commit()
        await self.db.refresh(dataset)

        logger.info(
            "Column deleted",
            dataset_id=str(dataset_id),
            column_name=column_data.column_name,
        )
        return dataset

    async def export_dataset(
        self,
        dataset_id: UUID,
        user_id: UUID,
        is_admin: bool,
        format: str = "csv",
    ) -> tuple[bytes, str, str]:
        """Export dataset with current data (including annotations) from dataset_rows table.
        
        Exports data from dataset_rows table, which includes all edits and annotations.
        This is different from downloading the original file from MinIO.

        Args:
            dataset_id: Dataset ID
            user_id: User ID for access control
            is_admin: Whether user is admin
            format: Export format, "csv" or "jsonl" (default: "csv")

        Returns:
            Tuple of (file_content, filename, content_type)

        Raises:
            ResourceNotFoundError: If dataset not found
            ValueError: If format is invalid or no data to export
        """
        dataset = await self.get_dataset_by_id(dataset_id, user_id=user_id, is_admin=is_admin)

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
        user_id: Optional[UUID] = None,
        is_admin: Optional[bool] = None,
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
            user_id: User ID for access control (optional if dataset already provided)
            is_admin: Whether user is admin (optional if dataset already provided)
            
        Returns:
            Paginated response with dataset rows
            
        Raises:
            ResourceNotFoundError: If dataset not found
        """
        # Only query dataset if not provided (avoid duplicate query)
        if dataset is None:
            dataset = await self.get_dataset_by_id(dataset_id, user_id=user_id, is_admin=is_admin, load_relationships=False)
        
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
        
        # Extract data from rows, include row_index for frontend to track actual position
        items = [{"__row_index__": row.row_index, **row.data} for row in rows]
        
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

