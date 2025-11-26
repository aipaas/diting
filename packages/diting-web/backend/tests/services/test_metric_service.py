"""Tests for MetricService."""

import pytest
from uuid import UUID, uuid4

from diting_web.common.exceptions import ResourceConflictError, ResourceNotFoundError
from diting_web.models.metric import Metric, MetricTypeEnum
from diting_web.schemas.metric import MetricCreate, MetricUpdate
from diting_web.services.metric_service import MetricService


class TestMetricService:
    """Tests for MetricService methods."""

    @pytest.mark.asyncio
    async def test_create_metric(self, db_session):
        """Test creating a new custom metric - 只需三要素."""
        # Arrange
        service = MetricService(db_session)
        metric_data = MetricCreate(
            name="custom_accuracy",
            description="A custom accuracy metric",
            prompt="Please evaluate the accuracy of the answer",
        )

        # Act
        metric = await service.create_metric(metric_data)

        # Assert
        assert metric.id is not None
        assert metric.name == "custom_accuracy"
        assert metric.description == "A custom accuracy metric"
        assert metric.prompt == "Please evaluate the accuracy of the answer"
        assert metric.type == MetricTypeEnum.CUSTOM  # 自动设置为 CUSTOM
        # 其他字段使用数据库默认值
        assert metric.actual_output_required is True  # 默认值
        assert metric.user_input_required is False  # 默认值

    @pytest.mark.asyncio
    async def test_get_metric_by_id(self, db_session):
        """Test getting a metric by ID."""
        # Arrange
        service = MetricService(db_session)
        metric_data = MetricCreate(
            name="test_metric",
            description="Test metric description",
        )
        created_metric = await service.create_metric(metric_data)

        # Act
        metric = await service.get_metric_by_id(created_metric.id)

        # Assert
        assert metric.id == created_metric.id
        assert metric.name == "test_metric"

    @pytest.mark.asyncio
    async def test_get_metric_by_id_not_found(self, db_session):
        """Test getting non-existent metric raises error."""
        # Arrange
        service = MetricService(db_session)
        fake_id = uuid4()

        # Act & Assert
        with pytest.raises(ResourceNotFoundError):
            await service.get_metric_by_id(fake_id)

    @pytest.mark.asyncio
    async def test_list_metrics(self, db_session):
        """Test listing metrics with pagination."""
        # Arrange
        service = MetricService(db_session)
        
        # Create multiple custom metrics
        for i in range(5):
            metric_data = MetricCreate(
                name=f"metric_{i}",
                description=f"Metric {i} description",
            )
            await service.create_metric(metric_data)

        # Act
        result = await service.get_metrics_list(offset=0, limit=3)

        # Assert
        assert result.total >= 5
        assert len(result.items) == 3
        assert result.page == 1
        assert result.page_size == 3

    @pytest.mark.asyncio
    async def test_delete_builtin_metric_raises_error(self, db_session):
        """Test that deleting builtin metric raises error."""
        # Arrange
        service = MetricService(db_session)
        # 直接创建一个内置维度（模拟系统预置）
        from diting_web.models.metric import Metric
        builtin_metric = Metric(
            name="answer_correctness",
            description="Answer Correctness metric",
            type=MetricTypeEnum.BUILTIN,
        )
        db_session.add(builtin_metric)
        await db_session.commit()
        await db_session.refresh(builtin_metric)

        # Act & Assert
        with pytest.raises(ResourceConflictError, match="Built-in metrics cannot be deleted"):
            await service.delete_metric(builtin_metric.id)



