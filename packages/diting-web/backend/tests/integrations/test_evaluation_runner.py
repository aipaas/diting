"""Tests for evaluation module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from diting_core.metrics.base_metric import MetricValue
from diting_web.workers.evaluation import EvaluationRunner


class TestLoadMetric:
    """Tests for EvaluationRunner._load_metric."""

    def test_load_metric_success(self):
        """Test loading a valid metric."""
        # Act
        metric_class = EvaluationRunner._load_metric("answer_correctness")

        # Assert
        assert metric_class is not None
        assert metric_class.__name__ == "AnswerCorrectness"

    def test_load_metric_unknown_raises_error(self):
        """Test that unknown metric name raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError):
            EvaluationRunner._load_metric("unknown_metric")


class TestRunEvaluation:
    """Tests for EvaluationRunner.run_evaluation."""

    @pytest.mark.asyncio
    @patch("diting_web.workers.evaluation.EvaluationRunner._load_metric")
    async def test_run_evaluation_success(self, mock_load_metric, mock_test_case_data):
        """Test successful evaluation run."""
        # Arrange
        mock_metric = MagicMock()
        mock_metric_value = MetricValue(
            metric_name="answer_correctness",
            score=0.85,
            reason="Good answer",
            run_logs={"details": "test"},
        )
        mock_metric.compute = AsyncMock(return_value=mock_metric_value)
        mock_load_metric.return_value = lambda: mock_metric

        llm_config = {"model_name": "gpt-4"}
        embedding_config = {"model_name": "bge-m3"}

        # Act
        result = await EvaluationRunner.run_evaluation(
            metric_name="answer_correctness",
            test_case_data=mock_test_case_data,
            llm_config=llm_config,
            embedding_config=embedding_config,
        )

        # Assert
        assert result["metric_name"] == "answer_correctness"
        assert result["score"] == 0.85
        assert result["reason"] == "Good answer"
        assert result["run_logs"] == {"details": "test"}
        assert "usages" in result
        mock_metric.compute.assert_called_once()

    @pytest.mark.asyncio
    @patch("diting_web.workers.evaluation.EvaluationRunner._load_metric")
    async def test_run_evaluation_with_none_score(self, mock_load_metric, mock_test_case_data):
        """Test evaluation with None score."""
        # Arrange
        mock_metric = MagicMock()
        mock_metric_value = MetricValue(
            metric_name="answer_correctness",
            score=None,
            reason="Could not evaluate",
            run_logs={},
        )
        mock_metric.compute = AsyncMock(return_value=mock_metric_value)
        mock_load_metric.return_value = lambda: mock_metric

        # Act
        result = await EvaluationRunner.run_evaluation(
            metric_name="answer_correctness",
            test_case_data=mock_test_case_data,
            llm_config={"model_name": "gpt-4"},
        )

        # Assert
        assert result["score"] is None
        assert result["reason"] == "Could not evaluate"

    @pytest.mark.asyncio
    @patch("diting_web.workers.evaluation.EvaluationRunner._load_metric")
    async def test_run_evaluation_handles_compute_error(
        self, mock_load_metric, mock_test_case_data
    ):
        """Test that compute errors are propagated."""
        # Arrange
        mock_metric = MagicMock()
        mock_metric.compute = AsyncMock(side_effect=Exception("Compute failed"))
        mock_load_metric.return_value = lambda: mock_metric

        # Act & Assert
        with pytest.raises(Exception, match="Compute failed"):
            await EvaluationRunner.run_evaluation(
                metric_name="answer_correctness",
                test_case_data=mock_test_case_data,
                llm_config={"model_name": "gpt-4"},
            )

    @pytest.mark.asyncio
    @patch("diting_web.workers.evaluation.EvaluationRunner._load_metric")
    async def test_run_evaluation_creates_llm_case(self, mock_load_metric, mock_test_case_data):
        """Test that LLMCase is created from test_case_data."""
        # Arrange
        mock_metric = MagicMock()
        mock_metric_value = MetricValue(metric_name="test", score=0.8)
        mock_metric.compute = AsyncMock(return_value=mock_metric_value)
        mock_load_metric.return_value = lambda: mock_metric

        # Act
        await EvaluationRunner.run_evaluation(
            metric_name="answer_correctness",
            test_case_data=mock_test_case_data,
            llm_config={"model_name": "gpt-4"},
        )

        # Assert
        # Check that compute was called with an LLMCase
        call_args = mock_metric.compute.call_args
        test_case = call_args[1]["test_case"]
        assert test_case.user_input == mock_test_case_data["user_input"]
        assert test_case.actual_output == mock_test_case_data["actual_output"]
        assert test_case.expected_output == mock_test_case_data["expected_output"]


# Note: _extract_usages method was removed, token tracking is now done via callbacks



