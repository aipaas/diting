"""Tests for TaskService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from diting_web.common.exceptions import ResourceNotFoundError
from diting_web.models.dataset import Dataset
from diting_web.models.evaluator import Evaluator
from diting_web.schemas.task import CreateBatchEvaluationTaskRequest
from diting_web.services.task.task_service import TaskService


class TestTaskService:
    """Tests for TaskService methods."""

    @pytest.mark.asyncio
    async def test_create_batch_evaluation_task_dataset_not_found(self, db_session):
        """Test creating batch evaluation task with non-existent dataset raises ResourceNotFoundError.
        
        This test verifies the fix for:
        - Issue: Dataset existence was not validated before task creation, causing FK constraint error
        - Fix: Validate dataset exists and raise ResourceNotFoundError (404) instead of DB error (500)
        """
        # Arrange
        service = TaskService(db_session)
        fake_dataset_id = uuid4()
        created_by = uuid4()
        
        # Mock ARQ client to avoid Redis dependency
        mock_arq_client = MagicMock()
        service.arq_client = mock_arq_client

        task_data = CreateBatchEvaluationTaskRequest(
            dataset_id=fake_dataset_id,
            name="Test Batch Evaluation",
        )

        # Act & Assert
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service.create_batch_evaluation_task(task_data, created_by)
        
        # Verify the exception is about Dataset
        assert "Dataset" in str(exc_info.value)
        assert str(fake_dataset_id) in str(exc_info.value)
        assert exc_info.value.code == 404

    @pytest.mark.asyncio
    async def test_create_batch_evaluation_task_evaluator_not_found(self, db_session):
        """Test creating batch evaluation task with non-existent evaluator raises error."""
        # Arrange
        service = TaskService(db_session)
        
        # Create a real dataset first
        dataset = Dataset(
            name="Test Dataset",
            description="Test dataset for evaluation",
            row_count=10,
        )
        db_session.add(dataset)
        await db_session.commit()
        await db_session.refresh(dataset)
        
        fake_evaluator_id = uuid4()
        created_by = uuid4()
        
        # Mock ARQ client
        mock_arq_client = MagicMock()
        service.arq_client = mock_arq_client

        task_data = CreateBatchEvaluationTaskRequest(
            dataset_id=dataset.id,
            evaluator_id=fake_evaluator_id,  # Non-existent evaluator
            name="Test Batch Evaluation",
        )

        # Act & Assert
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service.create_batch_evaluation_task(task_data, created_by)
        
        # Verify the exception is about Evaluator
        assert "Evaluator" in str(exc_info.value)
        assert str(fake_evaluator_id) in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("diting_web.services.task.task_service.get_arq_client")
    async def test_create_batch_evaluation_task_success(self, mock_get_arq_client, db_session):
        """Test successfully creating a batch evaluation task with valid dataset and evaluator."""
        # Arrange
        # Create dataset
        dataset = Dataset(
            name="Test Dataset",
            description="Test dataset",
            row_count=5,
        )
        db_session.add(dataset)
        
        # Create evaluator
        evaluator = Evaluator(
            name="Test Evaluator",
            description="Test evaluator",
            metric_ids=[],
            created_by=uuid4(),
        )
        db_session.add(evaluator)
        await db_session.commit()
        await db_session.refresh(dataset)
        await db_session.refresh(evaluator)
        
        # Mock ARQ client
        mock_arq_client = AsyncMock()
        mock_arq_client.enqueue_batch_evaluation = AsyncMock(return_value="job_123")
        mock_get_arq_client.return_value = mock_arq_client
        
        service = TaskService(db_session)
        service.arq_client = mock_arq_client
        
        task_data = CreateBatchEvaluationTaskRequest(
            dataset_id=dataset.id,
            evaluator_id=evaluator.id,
            name="Test Batch Evaluation",
        )
        created_by = uuid4()

        # Act
        task = await service.create_batch_evaluation_task(task_data, created_by)

        # Assert
        assert task.id is not None
        assert task.name == "Test Batch Evaluation"
        assert task.dataset_id == dataset.id
        assert task.created_by == created_by
        
        # Verify evaluator usage stats updated
        await db_session.refresh(evaluator)
        assert evaluator.usage_count == 1
        assert evaluator.last_used_at is not None
        
        # Verify ARQ enqueue was called
        mock_arq_client.enqueue_batch_evaluation.assert_called_once()

    @pytest.mark.asyncio
    @patch("diting_web.services.task.task_service.get_arq_client")
    async def test_create_batch_evaluation_task_auto_generate_name(self, mock_get_arq_client, db_session):
        """Test that task name is auto-generated from dataset when not provided."""
        # Arrange
        dataset = Dataset(
            name="My Dataset",
            description="Test dataset",
            row_count=3,
        )
        db_session.add(dataset)
        await db_session.commit()
        await db_session.refresh(dataset)
        
        # Mock ARQ client
        mock_arq_client = AsyncMock()
        mock_arq_client.enqueue_batch_evaluation = AsyncMock(return_value="job_123")
        mock_get_arq_client.return_value = mock_arq_client
        
        service = TaskService(db_session)
        service.arq_client = mock_arq_client
        
        # No name provided
        task_data = CreateBatchEvaluationTaskRequest(
            dataset_id=dataset.id,
        )
        created_by = uuid4()

        # Act
        task = await service.create_batch_evaluation_task(task_data, created_by)

        # Assert
        assert task.name == "批量评估 - My Dataset"

