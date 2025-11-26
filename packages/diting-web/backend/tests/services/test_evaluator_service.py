"""Tests for EvaluatorService."""

import pytest
from uuid import uuid4

from diting_web.common.exceptions import ResourceNotFoundError
from diting_web.models.evaluator import Evaluator
from diting_web.models.metric import Metric, MetricTypeEnum
from diting_web.schemas.evaluator import EvaluatorCreate
from diting_web.services.evaluator.evaluator_service import EvaluatorService


class TestEvaluatorService:
    """Tests for EvaluatorService methods."""

    @pytest.mark.asyncio
    async def test_get_evaluator_by_id_not_found(self, db_session):
        """Test getting non-existent evaluator raises ResourceNotFoundError with correct parameters.
        
        This test verifies the fix for: 
        - Issue: ResourceNotFoundError was called with extra 'status_code' parameter
        - Fix: Remove the extra parameter to match exception signature
        """
        # Arrange
        service = EvaluatorService(db_session)
        fake_id = uuid4()

        # Act & Assert
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service.get_evaluator_by_id(fake_id)
        
        # Verify the exception message format
        assert "Evaluator" in str(exc_info.value)
        assert str(fake_id) in str(exc_info.value)
        # Verify it's a proper 404 error (from exception's code attribute)
        assert exc_info.value.code == 404

    @pytest.mark.asyncio
    async def test_create_evaluator_success(self, db_session):
        """Test creating an evaluator with valid metrics."""
        # Arrange
        service = EvaluatorService(db_session)
        
        # Create a test metric first
        metric = Metric(
            name="test_metric",
            description="Test metric",
            type=MetricTypeEnum.BUILTIN,
        )
        db_session.add(metric)
        await db_session.commit()
        await db_session.refresh(metric)
        
        # Create evaluator data
        evaluator_data = EvaluatorCreate(
            name="Test Evaluator",
            description="Test evaluator description",
            metric_ids=[metric.id],
        )
        created_by = uuid4()

        # Act
        evaluator = await service.create_evaluator(evaluator_data, created_by)

        # Assert
        assert evaluator.id is not None
        assert evaluator.name == "Test Evaluator"
        assert evaluator.description == "Test evaluator description"
        assert metric.id in evaluator.metric_ids
        assert evaluator.created_by == created_by

    @pytest.mark.asyncio
    async def test_update_evaluator_not_found(self, db_session):
        """Test updating non-existent evaluator raises error."""
        # Arrange
        service = EvaluatorService(db_session)
        fake_id = uuid4()

        # Act & Assert
        with pytest.raises(ResourceNotFoundError):
            from diting_web.schemas.evaluator import EvaluatorUpdate
            await service.update_evaluator(
                fake_id, 
                EvaluatorUpdate(name="Updated Name")
            )

    @pytest.mark.asyncio
    async def test_delete_evaluator_not_found(self, db_session):
        """Test deleting non-existent evaluator raises error."""
        # Arrange
        service = EvaluatorService(db_session)
        fake_id = uuid4()

        # Act & Assert
        with pytest.raises(ResourceNotFoundError):
            await service.delete_evaluator(fake_id)

