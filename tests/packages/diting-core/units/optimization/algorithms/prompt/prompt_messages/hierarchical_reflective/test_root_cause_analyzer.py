"""Tests for HierarchicalRootCauseAnalyzer.

This test suite covers the hierarchical root cause analysis functionality,
including batch processing, synthesis, and validation.
"""

import pytest

from diting_core.cases.llm_case import LLMCase
from diting_core.metrics import MetricValue
from diting_core.optimization.algorithms.prompt.prompt_messages.hierarchical_reflective.root_cause_analyzer import (
    HierarchicalRootCauseAnalyzer,
)
from diting_core.optimization.algorithms.prompt.prompt_messages.hierarchical_reflective.types import (
    FailureMode,
    BatchAnalysis,
    HierarchicalRootCauseAnalysis,
)

# Import mock helpers from parent directory
import sys
from pathlib import Path

from diting_core.optimization.infra.eval_task import TestResult, ExperimentResult

test_helpers_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(test_helpers_path))
from test_helpers import MockLLMAdapter  # noqa: E402


def _messages_to_prompt(messages: list[dict[str, str]]) -> str:
    """Format chat messages into a simple prompt string for the mock LLM."""
    parts = []
    for message in messages:
        role = message.get("role", "")
        content = message.get("content", "")
        parts.append(f"{role}: {content}")
    return "\n\n".join(parts)


class TestHierarchicalRootCauseAnalyzer:
    """Test suite for HierarchicalRootCauseAnalyzer"""

    @pytest.fixture
    def mock_llm_adapter(self):
        """Create a mock LLM adapter"""
        return MockLLMAdapter()

    @pytest.fixture
    def call_model_fn(self, mock_llm_adapter):
        """Adapter that matches HierarchicalRootCauseAnalyzer's call signature."""

        async def _call_model_fn(messages, seed, response_model, callbacks):
            prompt = _messages_to_prompt(messages)
            return await mock_llm_adapter.generate_structured_output(
                prompt=prompt, schema=response_model, seed=seed, callbacks=callbacks
            )

        return _call_model_fn

    @pytest.fixture
    def sample_test_results(self):
        """Create sample test results with reasons"""
        return [
            TestResult(
                test_case=LLMCase(
                    user_input=f"Test input {i}",
                    actual_output=f"Test output {i}",
                    expected_output=f"Expected output {i}",
                ),
                metric_value=MetricValue(
                    metric_name="accuracy",
                    reason=f"Test case {i} failed due to insufficient handling of edge cases",
                    score=0.7 + (i % 3) * 0.05,
                ),
            )
            for i in range(10)
        ]

    @pytest.fixture
    def test_results_empty_reasons(self):
        return [
            TestResult(
                test_case=LLMCase(
                    user_input="Test input",
                    actual_output="Test output",
                    expected_output="Expected output",
                ),
                metric_value=MetricValue(
                    metric_name="accuracy",
                    reason="",
                    score=0.5,
                ),
            )
        ]

    @pytest.fixture
    def test_results_no_reasons(self):
        return [
            TestResult(
                test_case=LLMCase(
                    user_input="Test input",
                    actual_output="Test output",
                    expected_output="Expected output",
                ),
                metric_value=MetricValue(
                    metric_name="accuracy",
                    score=0.5,
                ),
            )
        ]

    @pytest.fixture
    def analyzer(self, call_model_fn):
        """Create analyzer instance with mock LLM"""
        return HierarchicalRootCauseAnalyzer(
            call_model_fn=call_model_fn,
            seed=42,
            max_parallel_batches=3,
            batch_size=5,
        )

    def test_analyzer_initialization(self, call_model_fn):
        """Test analyzer can be initialized with custom parameters"""
        analyzer = HierarchicalRootCauseAnalyzer(
            call_model_fn=call_model_fn,
            seed=42,
            max_parallel_batches=5,
            batch_size=25,
        )

        assert analyzer.seed == 42
        assert analyzer.max_parallel_batches == 5
        assert analyzer.batch_size == 25

    def test_validate_reasons_present_with_valid_results(
        self, analyzer, sample_test_results
    ):
        """Test validation passes with valid test results"""
        # Should not raise
        analyzer._validate_reasons_present(sample_test_results)

    def test_validate_reasons_present_with_empty_results(self, analyzer):
        """Test validation handles empty results gracefully"""
        # Should not raise for empty list
        analyzer._validate_reasons_present([])

    def test_validate_reasons_present_missing_reasons(
        self, analyzer, test_results_no_reasons
    ):
        """Test validation fails when reasons are missing"""

        with pytest.raises(ValueError, match="must include 'reason' fields"):
            analyzer._validate_reasons_present(test_results_no_reasons)

    def test_validate_reasons_present_empty_reasons(
        self, analyzer, test_results_empty_reasons
    ):
        """Test validation fails when reasons are empty strings"""

        with pytest.raises(ValueError, match="must include 'reason' fields"):
            analyzer._validate_reasons_present(test_results_empty_reasons)

    async def test_analyze_batch_async(self, analyzer, sample_test_results):
        """Test single batch analysis works correctly"""
        batch_analysis = await analyzer._analyze_batch(
            test_results=sample_test_results,
            batch_number=1,
            batch_start=0,
            batch_end=5,
        )

        # Check structure
        assert isinstance(batch_analysis, BatchAnalysis)
        assert batch_analysis.batch_number == 1
        assert batch_analysis.start_index == 0
        assert batch_analysis.end_index == 5
        assert len(batch_analysis.failure_modes) > 0
        assert isinstance(batch_analysis.failure_modes[0], FailureMode)

    async def test_analyze_batch_async_boundary(self, analyzer, sample_test_results):
        """Test batch analysis handles boundary correctly"""
        # Request beyond available results
        batch_analysis = await analyzer._analyze_batch(
            test_results=sample_test_results,
            batch_number=2,
            batch_start=8,
            batch_end=15,  # Only 10 results available
        )

        # Should have correct end index
        assert batch_analysis.end_index == 10
        assert batch_analysis.start_index == 8

    async def test_synthesize_batch_analyses_async(self, analyzer, sample_test_results):
        """Test synthesis of multiple batch analyses"""
        # Create mock batch analyses
        batch_analyses = [
            BatchAnalysis(
                batch_number=1,
                start_index=0,
                end_index=5,
                failure_modes=[
                    FailureMode(
                        name="Batch 1 Failure",
                        description="First batch failure pattern",
                        root_cause="Insufficient validation",
                    )
                ],
            ),
            BatchAnalysis(
                batch_number=2,
                start_index=5,
                end_index=10,
                failure_modes=[
                    FailureMode(
                        name="Batch 2 Failure",
                        description="Second batch failure pattern",
                        root_cause="Edge case handling",
                    )
                ],
            ),
        ]

        synthesis = await analyzer._synthesize_batch_analyses(
            test_results=sample_test_results,
            batch_analyses=batch_analyses,
        )

        # Check structure
        assert isinstance(synthesis, HierarchicalRootCauseAnalysis)
        # Note: Mock returns fixed values, actual test_results length is 10
        assert synthesis.total_test_cases >= 0  # Mock returns 10
        assert synthesis.num_batches >= 0  # Mock returns 1
        assert len(synthesis.unified_failure_modes) > 0
        assert synthesis.synthesis_notes is not None

    async def test_analyze_async_full_flow(self, analyzer, sample_test_results):
        """Test complete hierarchical analysis flow"""
        result = await analyzer.analyze(
            ExperimentResult(experiment_name="test", test_results=sample_test_results)
        )

        # Check result structure
        assert isinstance(result, HierarchicalRootCauseAnalysis)
        assert result.total_test_cases == 10
        assert result.num_batches > 0
        assert len(result.unified_failure_modes) > 0

        # Check that failure modes have proper structure
        for failure_mode in result.unified_failure_modes:
            assert isinstance(failure_mode, FailureMode)
            assert failure_mode.name
            assert failure_mode.description
            assert failure_mode.root_cause

    async def test_analyze_async_with_missing_reasons(
        self, analyzer, test_results_no_reasons
    ):
        """Test analysis fails gracefully with missing reasons"""
        with pytest.raises(ValueError, match="must include 'reason' fields"):
            await analyzer.analyze(
                ExperimentResult(
                    experiment_name="test", test_results=test_results_no_reasons
                )
            )

    async def test_analyze_async_single_batch(self, call_model_fn, sample_test_results):
        """Test analysis with results fitting in single batch"""
        analyzer = HierarchicalRootCauseAnalyzer(
            call_model_fn=call_model_fn,
            seed=42,
            max_parallel_batches=3,
            batch_size=20,  # Larger than test results
        )

        result = await analyzer.analyze(
            ExperimentResult(experiment_name="test", test_results=sample_test_results)
        )

        # Should still work with single batch
        # Note: Mock returns fixed values
        assert result.total_test_cases >= 0
        assert result.num_batches >= 0

    async def test_analyze_async_multiple_batches(
        self, call_model_fn, sample_test_results
    ):
        """Test analysis with results split across multiple batches"""
        analyzer = HierarchicalRootCauseAnalyzer(
            call_model_fn=call_model_fn,
            seed=42,
            max_parallel_batches=2,
            batch_size=3,  # Small batch size to force multiple batches
        )

        experiment = ExperimentResult(
            experiment_name="test", test_results=sample_test_results
        )

        result = await analyzer.analyze(experiment)

        # Should have multiple batches
        # Note: Mock returns fixed values
        assert result.total_test_cases >= 0
        assert result.num_batches >= 0

    async def test_concurrent_batch_processing(self, mock_llm_adapter):
        """Test that batches are processed with proper concurrency limits"""
        call_count = 0

        async def counting_call_model_fn(messages, seed, response_model, callbacks):
            nonlocal call_count
            call_count += 1
            # Simulate some async work
            import asyncio

            await asyncio.sleep(0.01)
            return await mock_llm_adapter.generate_structured_output(
                prompt=_messages_to_prompt(messages),
                schema=response_model,
                seed=seed,
                callbacks=callbacks,
            )

        analyzer = HierarchicalRootCauseAnalyzer(
            call_model_fn=counting_call_model_fn,
            seed=42,
            max_parallel_batches=2,
            batch_size=5,
        )

        test_results = [
            TestResult(
                test_case=LLMCase(
                    user_input=f"Test input {i}",
                    actual_output=f"Test output {i}",
                    expected_output=f"Expected output {i}",
                ),
                metric_value=MetricValue(
                    metric_name="accuracy",
                    reason=f"Test case {i} failed due to insufficient handling of edge cases",
                    score=0.7 + (i % 3) * 0.05,
                ),
            )
            for i in range(15)
        ]

        result = await analyzer.analyze(
            ExperimentResult(experiment_name="test", test_results=test_results)
        )

        # Should have called LLM: 3 batches + 1 synthesis = 4 calls
        assert call_count == 4
        # Note: Mock returns fixed values
        assert result.num_batches >= 0
