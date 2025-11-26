"""Tests for dataset_parser module."""

import io
import json
import pytest
from fastapi import UploadFile

from diting_web.common.exceptions import ValidationError
from diting_web.utils.dataset_parser import DatasetParser


class TestDatasetParser:
    """Tests for DatasetParser.parse_file."""

    @pytest.mark.asyncio
    async def test_parse_csv_file(self):
        """Test parsing a CSV file."""
        # Arrange
        csv_content = b"question,answer,ground_truth\nWhat is Python?,A language,Python is a programming language\nWhat is AI?,Artificial Intelligence,AI is machine intelligence"
        
        file = UploadFile(
            filename="test.csv",
            file=io.BytesIO(csv_content),
        )
        file.content_type = "text/csv"

        # Act
        metadata = await DatasetParser.parse_file(file)

        # Assert
        assert metadata["row_count"] == 2
        assert metadata["column_count"] == 3
        assert "question" in metadata["columns"]
        assert "answer" in metadata["columns"]
        assert "ground_truth" in metadata["columns"]
        assert len(metadata["preview_data"]) == 2

    @pytest.mark.asyncio
    async def test_parse_file_unsupported_type(self):
        """Test parsing unsupported file type raises error."""
        # Arrange
        file = UploadFile(
            filename="test.txt",
            file=io.BytesIO(b"some text"),
        )
        file.content_type = "text/plain"

        # Act & Assert
        with pytest.raises(ValidationError, match="Unsupported file type"):
            await DatasetParser.parse_file(file)

    @pytest.mark.asyncio
    async def test_parse_empty_file(self):
        """Test parsing empty file raises error."""
        # Arrange
        file = UploadFile(
            filename="empty.csv",
            file=io.BytesIO(b""),
        )
        file.content_type = "text/csv"

        # Act & Assert
        with pytest.raises(ValidationError):
            await DatasetParser.parse_file(file)

    @pytest.mark.asyncio
    async def test_parse_jsonl_file(self):
        """Test parsing a JSONL file."""
        # Arrange
        jsonl_content = b'\n'.join([
            json.dumps({"question": "What is Python?", "answer": "A language", "ground_truth": "Python is a programming language"}).encode('utf-8'),
            json.dumps({"question": "What is AI?", "answer": "Artificial Intelligence", "ground_truth": "AI is machine intelligence"}).encode('utf-8'),
        ])
        
        file = UploadFile(
            filename="test.jsonl",
            file=io.BytesIO(jsonl_content),
        )
        file.content_type = "application/x-ndjson"

        # Act
        metadata = await DatasetParser.parse_file(file)

        # Assert
        assert metadata["row_count"] == 2
        assert metadata["column_count"] == 3
        assert "question" in metadata["columns"]
        assert "answer" in metadata["columns"]
        assert "ground_truth" in metadata["columns"]
        assert len(metadata["preview_data"]) == 2
        assert metadata["preview_data"][0]["question"] == "What is Python?"
        assert metadata["preview_data"][1]["question"] == "What is AI?"

    @pytest.mark.asyncio
    async def test_parse_jsonl_file_with_empty_lines(self):
        """Test parsing a JSONL file with empty lines."""
        # Arrange
        jsonl_content = b'\n'.join([
            json.dumps({"field1": "value1", "field2": "value2"}).encode('utf-8'),
            b"",  # Empty line
            json.dumps({"field1": "value3", "field2": "value4"}).encode('utf-8'),
            b"   ",  # Line with only whitespace
            json.dumps({"field1": "value5", "field2": "value6"}).encode('utf-8'),
        ])
        
        file = UploadFile(
            filename="test.jsonl",
            file=io.BytesIO(jsonl_content),
        )
        file.content_type = "application/x-ndjson"

        # Act
        metadata = await DatasetParser.parse_file(file)

        # Assert
        assert metadata["row_count"] == 3  # Empty lines should be skipped
        assert metadata["column_count"] == 2

    @pytest.mark.asyncio
    async def test_parse_jsonl_file_invalid_json(self):
        """Test parsing JSONL file with invalid JSON raises error."""
        # Arrange
        jsonl_content = b'\n'.join([
            json.dumps({"field1": "value1"}).encode('utf-8'),
            b"{invalid json}",  # Invalid JSON
            json.dumps({"field2": "value2"}).encode('utf-8'),
        ])
        
        file = UploadFile(
            filename="test.jsonl",
            file=io.BytesIO(jsonl_content),
        )
        file.content_type = "application/x-ndjson"

        # Act & Assert
        with pytest.raises(ValidationError, match="Invalid JSON"):
            await DatasetParser.parse_file(file)

    @pytest.mark.asyncio
    async def test_parse_jsonl_file_empty(self):
        """Test parsing empty JSONL file raises error."""
        # Arrange
        file = UploadFile(
            filename="empty.jsonl",
            file=io.BytesIO(b""),
        )
        file.content_type = "application/x-ndjson"

        # Act & Assert
        with pytest.raises(ValidationError, match="empty"):
            await DatasetParser.parse_file(file)

    @pytest.mark.asyncio
    async def test_parse_jsonl_file_with_array_column(self):
        """Test parsing JSONL file with array column preserves arrays."""
        # Arrange - JSONL with array column
        jsonl_content = b'\n'.join([
            json.dumps({
                "id": 1,
                "tags": ["python", "programming", "ai"],
                "scores": [0.9, 0.8, 0.7],
                "context": ["context1", "context2"]
            }).encode('utf-8'),
            json.dumps({
                "id": 2,
                "tags": ["ml", "deep-learning"],
                "scores": [0.95, 0.85],
                "context": ["context3"]
            }).encode('utf-8'),
        ])
        
        file = UploadFile(
            filename="test.jsonl",
            file=io.BytesIO(jsonl_content),
        )
        file.content_type = "application/x-ndjson"

        # Act
        metadata = await DatasetParser.parse_file(file)

        # Assert
        assert metadata["row_count"] == 2
        assert metadata["column_count"] == 4
        assert "tags" in metadata["columns"]
        assert "scores" in metadata["columns"]
        assert "context" in metadata["columns"]
        
        # Verify arrays are preserved as lists
        preview_data = metadata["preview_data"]
        assert isinstance(preview_data[0]["tags"], list)
        assert preview_data[0]["tags"] == ["python", "programming", "ai"]
        assert isinstance(preview_data[0]["scores"], list)
        assert preview_data[0]["scores"] == [0.9, 0.8, 0.7]
        assert isinstance(preview_data[0]["context"], list)
        assert preview_data[0]["context"] == ["context1", "context2"]
        
        # Verify second row arrays
        assert isinstance(preview_data[1]["tags"], list)
        assert preview_data[1]["tags"] == ["ml", "deep-learning"]
        assert len(preview_data[1]["scores"]) == 2
        assert len(preview_data[1]["context"]) == 1



