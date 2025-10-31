"""Test helpers for optimization module tests.

This module provides mock implementations ONLY for testing purposes.
Production code should NOT import from this module.
"""

import typing as t
from typing import Any

from diting_core.cases.llm_case import LLMCase
from diting_core.metrics import MetricValue
from diting_core.models.llms.base_model import BaseLLM, PydanticClass
from diting_optimizer.infra.eval_task import ExperimentResult, TestResult
from diting_optimizer.target.prompt_config import PromptConfig
from diting_optimizer.datasets.base_dataset import BaseDataset
from diting_core.metrics.base_metric import BaseMetric
from diting_optimizer.algorithms.prompt.prompt_messages.hierarchical_reflective.types import (
    RootCauseAnalysis,
    FailureMode,
    HierarchicalRootCauseAnalysis,
    ImprovedPrompt,
    PromptMessage,
)


class MockLLMAdapter(BaseLLM):
    """Mock LLM adapter for testing purposes.

    This class simulates LLM behavior for testing optimization algorithms
    without requiring real LLM API calls.
    """

    async def generate(
        self,
        prompt: str,
        n: int = 1,
        temperature: t.Optional[float] = None,
        **kwargs: t.Any,
    ) -> str | t.List[str]:
        pass

    def __init__(self):
        self.call_count = 0

    async def generate_structured_output(
        self,
        prompt: str,
        schema: t.Optional[PydanticClass] = None,  # noqa: UP006
        **kwargs: t.Any,
    ) -> Any:
        """Mock structured output generation.

        Args:
            prompt: input for llm (ignored in mock)
            schema: Pydantic model to instantiate

        Returns:
            Instance of response_model with mock data
        """
        self.call_count += 1

        # Return appropriate mock based on response_model
        if schema.__name__ == "RootCauseAnalysis":
            return RootCauseAnalysis(
                failure_modes=[
                    FailureMode(
                        name="Mock Failure Pattern",
                        description="The system fails to handle edge cases correctly",
                        root_cause="Insufficient validation logic in the implementation",
                    )
                ]
            )
        elif schema.__name__ == "HierarchicalRootCauseAnalysis":
            return HierarchicalRootCauseAnalysis(
                total_test_cases=10,
                num_batches=1,
                unified_failure_modes=[
                    FailureMode(
                        name="Mock Unified Failure",
                        description="Consistent failure across multiple test cases",
                        root_cause="Core algorithm logic needs refinement",
                    )
                ],
                synthesis_notes="Mock synthesis: Identified 1 primary failure pattern affecting 60% of test cases",
            )
        elif schema.__name__ == "ImprovedPrompt":
            return ImprovedPrompt(
                reasoning="Added explicit edge case handling instructions to address the identified failure pattern",
                messages=[
                    PromptMessage(
                        role="system",
                        content="You are a helpful assistant. When processing requests, carefully validate all inputs and handle edge cases appropriately.",
                    ),
                    PromptMessage(
                        role="user",
                        content="{input}",
                    ),
                ],
            )
        else:
            raise ValueError(f"Unknown response model: {schema.__name__}")


async def mock_evaluate_prompt(
    prompt_config: PromptConfig,
    dataset: BaseDataset,
    metric: BaseMetric,
    max_concurrency: int,
    **kwargs: Any,
) -> ExperimentResult:
    """Mock synchronous prompt evaluation for testing.

    Returns a random score to simulate model_parameters optimization trials.

    Args:
        prompt_config: Prompt configuration (ignored in mock)
        dataset: Evaluation dataset (ignored in mock)
        metric: Evaluation metric (ignored in mock)
        max_concurrency: max concurrency for evaluation (ignored in mock)

    Returns:
        Random score between 0.5 and 0.9
    """
    test_results = [
        TestResult(
            test_case=LLMCase(
                **{
                    "input": f"Test input {i}",
                    "output": f"Test output {i}",
                    "expected": f"Expected output {i}",
                    "metadata": {},
                }
            ),
            metric_value=MetricValue(
                metric_name="test",
                score=0.7 + (i % 3) * 0.05,  # Varying scores
                reason=f"Mock evaluation reason for test case {i}",
            ),
        )
        for i in range(10)
    ]

    return ExperimentResult(experiment_name="mock", test_results=test_results)


def mock_evaluate_prompt_sync(
    prompt_config: PromptConfig,
    dataset: BaseDataset,
    metric: BaseMetric,
    max_concurrency: int,
    **kwargs: Any,
) -> ExperimentResult:
    """Mock synchronous prompt evaluation for testing.

    Returns a random score to simulate model_parameters optimization trials.

    Args:
        prompt_config: Prompt configuration (ignored in mock)
        dataset: Evaluation dataset (ignored in mock)
        metric: Evaluation metric (ignored in mock)
        max_concurrency: max concurrency for evaluation (ignored in mock)

    Returns:
        Random score between 0.5 and 0.9
    """
    test_results = [
        TestResult(
            test_case=LLMCase(
                **{
                    "input": f"Test input {i}",
                    "output": f"Test output {i}",
                    "expected": f"Expected output {i}",
                    "metadata": {},
                }
            ),
            metric_value=MetricValue(
                metric_name="test",
                score=0.7 + (i % 3) * 0.05,  # Varying scores
                reason=f"Mock evaluation reason for test case {i}",
            ),
        )
        for i in range(10)
    ]

    return ExperimentResult(experiment_name="mock", test_results=test_results)
