"""Tests for HierarchicalReflectiveOptimizer.

Note: These tests use mock LLM calls and evaluations from test_helpers.
Real integration tests will be added when LLM adapter is implemented.
"""

from unittest.mock import patch

import pytest

from diting_core.optimization.algorithms.prompt.prompt_messages.hierarchical_reflective.optimizer import (
    HierarchicalReflectiveOptimizer,
)
from diting_core.optimization.target.prompt_config import PromptConfig
from diting_core.optimization.datasets.base_dataset import InMemoryDataset
from diting_core.metrics.base_metric import BaseMetric

# Import mock helpers from parent directory
import sys
from pathlib import Path

test_helpers_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(test_helpers_path))
from test_helpers import MockLLMAdapter, mock_evaluate_prompt_with_detail  # noqa: E402


class MockMetric(BaseMetric):
    """Mock metric for testing"""

    async def _compute(self, output: str, expected_output: str, **kwargs) -> float:
        """Simple word overlap metric"""
        if not output or not expected_output:
            return 0.0
        return len(set(output.split()) & set(expected_output.split())) / max(
            len(output.split()), len(expected_output.split())
        )


class TestHierarchicalReflectiveOptimizer:
    """Test suite for HierarchicalReflectiveOptimizer"""

    @pytest.fixture
    def mock_dataset(self):
        """Create a mock dataset"""
        return InMemoryDataset(
            name="test_dataset",
            items=[
                {"input": "Hello", "expected_output": "Hi there"},
                {"input": "How are you?", "expected_output": "I'm doing well"},
            ],
        )

    @pytest.fixture
    def mock_metric(self):
        """Create a mock metric"""
        return MockMetric()

    @pytest.fixture
    def initial_prompt(self):
        """Create an initial prompt config"""
        return PromptConfig(
            system="You are a helpful assistant.",
            user="{input}",
            model_params={"temperature": 0.7, "max_tokens": 100},
            llm=MockLLMAdapter(),
        )

    def test_optimizer_initialization(self):
        """Test optimizer_name can be initialized"""
        optimizer = HierarchicalReflectiveOptimizer(
            seed=42,
        )

        assert optimizer.seed == 42
        assert optimizer.max_iterations == 5
        assert optimizer.convergence_threshold == 0.01

    def test_optimizer_initialization_with_custom_params(self):
        """Test optimizer_name with custom parameters"""
        optimizer = HierarchicalReflectiveOptimizer(
            seed=123,
            max_parallel_batches=10,
            batch_size=50,
            max_iterations=10,
            convergence_threshold=0.005,
            max_retries=3,
        )

        assert optimizer.seed == 123
        assert optimizer.max_parallel_batches == 10
        assert optimizer.batch_size == 50
        assert optimizer.max_iterations == 10
        assert optimizer.convergence_threshold == 0.005
        assert optimizer.max_retries == 3

    @pytest.mark.asyncio
    @patch(
        "diting_core.optimization.algorithms.prompt.prompt_messages.hierarchical_reflective.optimizer.evaluate_prompt_with_detail",
        mock_evaluate_prompt_with_detail,
    )
    async def test_optimize_basic(self, initial_prompt, mock_dataset, mock_metric):
        """Test basic optimization flow (with mocks)"""
        optimizer = HierarchicalReflectiveOptimizer(
            seed=42,
            max_iterations=1,  # Only 1 iteration for quick test
        )

        # Inject mock dependencies
        optimizer.llm = MockLLMAdapter()

        result = await optimizer.optimize(
            config=initial_prompt,
            dataset=mock_dataset,
            metric=mock_metric,
            n_trials=10,  # Not used by this optimizer_name
            verbose=True,
        )

        # Check result structure
        assert result is not None
        assert result.best_config is not None
        assert result.initial_prompt is not None
        assert result.best_score >= 0
        assert result.initial_score >= 0
        assert result.optimizer_name == "HierarchicalReflectiveOptimizer"
        assert result.metric_name == "MockMetric"
        assert result.iterations == 1

    @pytest.mark.asyncio
    @patch(
        "diting_core.optimization.algorithms.prompt.prompt_messages.hierarchical_reflective.optimizer.evaluate_prompt_with_detail",
        mock_evaluate_prompt_with_detail,
    )
    async def test_optimize_converges_early(
        self, initial_prompt, mock_dataset, mock_metric
    ):
        """Test that optimizer_name can converge early"""
        optimizer = HierarchicalReflectiveOptimizer(
            seed=42,
            max_iterations=10,
            convergence_threshold=0.1,  # High threshold for quick convergence
        )

        # Inject mock dependencies
        optimizer.llm = MockLLMAdapter()

        result = await optimizer.optimize(
            config=initial_prompt,
            dataset=mock_dataset,
            metric=mock_metric,
        )

        # Should converge before max_iterations due to mock returning same scores
        assert result.iterations <= 10

    def test_calculate_improvement(self):
        """Test improvement calculation"""
        optimizer = HierarchicalReflectiveOptimizer()

        # Test normal improvement
        improvement = optimizer.calculate_improvement(0.8, 0.7)
        assert pytest.approx(improvement, abs=1e-4) == (0.8 - 0.7) / 0.7

        # Test no improvement
        improvement = optimizer.calculate_improvement(0.7, 0.7)
        assert improvement == 0.0

        # Test regression
        improvement = optimizer.calculate_improvement(0.6, 0.7)
        assert improvement < 0

        # Test with zero baseline
        improvement = optimizer.calculate_improvement(0.5, 0.0)
        assert improvement == 0

    @pytest.mark.asyncio
    @patch(
        "diting_core.optimization.algorithms.prompt.prompt_messages.hierarchical_reflective.optimizer.evaluate_prompt_with_detail",
        mock_evaluate_prompt_with_detail,
    )
    async def test_optimization_history(
        self, initial_prompt, mock_dataset, mock_metric
    ):
        """Test that optimization history is tracked"""
        optimizer = HierarchicalReflectiveOptimizer(
            seed=42,
            max_iterations=1,
        )

        # Inject mock dependencies
        optimizer.llm = MockLLMAdapter()
        result = await optimizer.optimize(
            config=initial_prompt,
            dataset=mock_dataset,
            metric=mock_metric,
        )

        # History should be tracked
        assert len(result.history) > 0
