"""Dataset file parser utilities.

Support formats: CSV, Excel (xls/xlsx), JSONL
"""

import json
from io import BytesIO
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import UploadFile

from diting_web.common.exceptions import ValidationError
from diting_web.common.logging import get_logger

logger = get_logger(__name__)


class DatasetParser:
    """Dataset file parser."""

    SUPPORTED_EXTENSIONS = {".csv", ".xls", ".xlsx", ".jsonl"}
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    MAX_PREVIEW_ROWS = 100

    @classmethod
    async def parse_file(
        cls,
        file: UploadFile,
    ) -> Dict[str, Any]:
        """Parse dataset file and extract metadata.

        Args:
            file: Uploaded file

        Returns:
            Dictionary containing:
            - row_count: Number of rows
            - column_count: Number of columns
            - columns: List of column names
            - preview_data: First N rows for preview
            - file_size: File size in bytes
            - data_types: Column data types

        Raises:
            ValidationError: If file format unsupported or parsing fails
        """
        # Validate file extension
        file_ext = cls._get_file_extension(file.filename or "")
        if file_ext not in cls.SUPPORTED_EXTENSIONS:
            raise ValidationError(
                f"Unsupported file format: {file_ext}. "
                f"Supported formats: {', '.join(cls.SUPPORTED_EXTENSIONS)}"
            )

        # Read file content
        content = await file.read()
        file_size = len(content)

        # Validate file size
        if file_size > cls.MAX_FILE_SIZE:
            raise ValidationError(
                f"File size ({file_size / 1024 / 1024:.2f}MB) exceeds "
                f"maximum allowed size ({cls.MAX_FILE_SIZE / 1024 / 1024}MB)"
            )

        try:
            # Parse file based on extension
            if file_ext == ".csv":
                df = cls._read_csv_with_encoding(content)
            elif file_ext in {".xls", ".xlsx"}:
                df = pd.read_excel(BytesIO(content), engine="openpyxl")
            elif file_ext == ".jsonl":
                df = cls._read_jsonl(content)
            else:
                raise ValidationError(f"Unsupported file extension: {file_ext}")

            # Extract metadata
            metadata = {
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": df.columns.tolist(),
                "preview_data": cls._generate_preview(df),
                "file_size": file_size,
                "data_types": cls._get_data_types(df),
            }

            logger.info(
                "Dataset parsed successfully",
                filename=file.filename,
                rows=metadata["row_count"],
                columns=metadata["column_count"],
            )

            return metadata

        except pd.errors.EmptyDataError:
            raise ValidationError("File is empty")
        except pd.errors.ParserError as e:
            raise ValidationError(f"Failed to parse file: {str(e)}")
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON format: {str(e)}")
        except ValidationError:
            # Re-raise ValidationError as-is
            raise
        except Exception as e:
            logger.error("Dataset parsing failed", filename=file.filename, error=str(e))
            raise ValidationError(f"Failed to parse file: {str(e)}")

    @classmethod
    def _read_csv_with_encoding(cls, content: bytes) -> pd.DataFrame:
        """Read CSV file with automatic encoding detection.
        
        Args:
            content: File content in bytes
            
        Returns:
            Pandas DataFrame
            
        Raises:
            ValidationError: If file cannot be parsed with any encoding
        """
        # Try common encodings in order
        encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'latin1', 'iso-8859-1']
        
        last_error = None
        for encoding in encodings:
            try:
                df = pd.read_csv(BytesIO(content), encoding=encoding)
                logger.info(f"Successfully parsed CSV with encoding: {encoding}")
                return df
            except (UnicodeDecodeError, Exception) as e:
                last_error = e
                continue
        
        # If all encodings fail, raise the last error
        raise ValidationError(
            f"Failed to parse CSV file with common encodings. Last error: {str(last_error)}"
        )
    
    @classmethod
    def _read_jsonl(cls, content: bytes) -> pd.DataFrame:
        """Read JSONL file (JSON Lines format).
        
        Each line is a JSON object. The file is parsed line by line
        and converted to a pandas DataFrame.
        
        Args:
            content: File content in bytes
            
        Returns:
            Pandas DataFrame
            
        Raises:
            ValidationError: If file cannot be parsed
        """
        # Try common encodings in order
        encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'latin1', 'iso-8859-1']
        
        last_error = None
        for encoding in encodings:
            try:
                # Decode content to string
                text = content.decode(encoding)
                
                # Parse JSONL line by line
                records = []
                for line_num, line in enumerate(text.splitlines(), 1):
                    line = line.strip()
                    if not line:  # Skip empty lines
                        continue
                    try:
                        record = json.loads(line)
                        if isinstance(record, dict):
                            records.append(record)
                        else:
                            raise ValidationError(
                                f"Line {line_num}: Each JSONL line must be a JSON object, "
                                f"got {type(record).__name__}"
                            )
                    except json.JSONDecodeError as e:
                        raise ValidationError(
                            f"Line {line_num}: Invalid JSON - {str(e)}"
                        )
                
                if not records:
                    raise ValidationError("JSONL file is empty or contains no valid JSON objects")
                
                # Convert to DataFrame
                df = pd.DataFrame(records)
                logger.info(f"Successfully parsed JSONL with encoding: {encoding}, rows: {len(df)}")
                return df
                
            except UnicodeDecodeError as e:
                last_error = e
                continue
            except ValidationError:
                # Re-raise ValidationError as-is
                raise
            except Exception as e:
                last_error = e
                continue
        
        # If all encodings fail, raise the last error
        raise ValidationError(
            f"Failed to parse JSONL file with common encodings. Last error: {str(last_error)}"
        )
    
    @classmethod
    def _get_file_extension(cls, filename: str) -> str:
        """Get file extension from filename.

        Args:
            filename: Filename with extension

        Returns:
            File extension (lowercase with dot)
        """
        if "." not in filename:
            return ""
        return "." + filename.rsplit(".", 1)[-1].lower()

    @classmethod
    def _generate_preview(cls, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Generate preview data from DataFrame.

        Args:
            df: Pandas DataFrame

        Returns:
            List of dictionaries representing rows
        """
        preview_df = df.head(cls.MAX_PREVIEW_ROWS)
        # Replace NaN with None for JSON serialization
        preview_df = preview_df.where(pd.notnull(preview_df), None)
        return preview_df.to_dict(orient="records")

    @classmethod
    def _get_data_types(cls, df: pd.DataFrame) -> Dict[str, str]:
        """Get data types for each column.

        Args:
            df: Pandas DataFrame

        Returns:
            Dictionary mapping column name to data type
        """
        return {col: str(dtype) for col, dtype in df.dtypes.items()}

    @classmethod
    async def validate_dataset_format(
        cls,
        file: UploadFile,
        required_columns: Optional[List[str]] = None,
    ) -> None:
        """Validate dataset format and required columns.

        Args:
            file: Uploaded file
            required_columns: List of required column names

        Raises:
            ValidationError: If validation fails
        """
        metadata = await cls.parse_file(file)

        if required_columns:
            missing_columns = set(required_columns) - set(metadata["columns"])
            if missing_columns:
                raise ValidationError(
                    f"Missing required columns: {', '.join(missing_columns)}"
                )

        # Validate minimum row count
        if metadata["row_count"] == 0:
            raise ValidationError("Dataset must contain at least one row")

        logger.info(
            "Dataset validation passed",
            filename=file.filename,
            rows=metadata["row_count"],
        )


# Convenience function
async def parse_dataset_file(file: UploadFile) -> Dict[str, Any]:
    """Parse dataset file.

    Args:
        file: Uploaded file

    Returns:
        Dataset metadata dictionary
    """
    return await DatasetParser.parse_file(file)

