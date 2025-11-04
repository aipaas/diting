"""Evaluation task infrastructure for prompt optimization.

This module provides classes and functions for evaluating prompts on datasets
using specified metrics, supporting parallel execution and comprehensive result tracking.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


from diting_core.callbacks.base import Callbacks
from diting_core.cases.llm_case import LLMCase, LLMCaseParams
from diting_core.metrics import BaseMetric, MetricValue
from diting_optimizer.target.prompt_config import PromptConfig
from diting_optimizer.datasets.base_dataset import BaseDataset

logger = logging.getLogger(__name__)


class TestResult(BaseModel):
    """Result of evaluating a single test case.

    Attributes:
        test_case: The test case that was evaluated
        metric_value: The computed metric value for this test case
    """

    __test__ = False  # Critical: Prevent pytest from recognizing this as a test class
    test_case: LLMCase = Field(..., description="The test case that was evaluated")
    metric_value: MetricValue = Field(..., description="The computed metric value")


class ExperimentResult(BaseModel):
    """Results of evaluating a prompt on a dataset.

    Attributes:
        experiment_name: Optional name for the experiment
        test_results: List of individual test case results
    """

    experiment_name: Optional[str] = Field(
        default=None, description="Optional name for the experiment"
    )
    test_results: List[TestResult] = Field(
        default_factory=list, description="List of individual test case results"
    )

    @property
    def avg_score(self) -> float:
        """Calculate the average of valid scores across all MetricValue objects.

        Returns
        -------
        float
            Average score; raises ValueError if no valid scores are found

        Raises
        ------
        ValueError
            If no valid scores are found in the test results
        """
        # Collect all non-None scores
        scores: List[float] = []
        for test_result in self.test_results:
            if test_result.metric_value.score is not None:  # Only consider valid scores
                scores.append(test_result.metric_value.score)

        # Calculate average (handle empty list case)
        if not scores:
            logger.warning(
                f"Experiment '{self.experiment_name}' has no valid scores, returning 0.0"
            )
            return 0.0
        return sum(scores) / len(scores)


def sort_test_results_by_failure(
    test_results: list[TestResult], ascending: bool = True, in_place: bool = True
) -> list[TestResult]:
    """Sort a list of TestResult objects by failure severity based on metric scores.

    Sorts test results primarily by their `metric_value.score` (lower scores indicate
    more severe failures). Handles `None` scores by treating them as the most severe
    failures (equivalent to a score of 0.0).

    Args:
        test_results: List of TestResult objects to be sorted.
        ascending: If True, sort in ascending order (more severe failures first,
            lower scores first). If False, sort in descending order (less severe
            failures first, higher scores first). Defaults to True.
        in_place: If True, sorts the list in-place (modifies the original list and
            uses less memory). If False, returns a new sorted list without modifying
            the original. Defaults to True.

    Returns:
        The sorted list of TestResult objects. If `in_place=True`, this is the same
        list object passed in (modified). If `in_place=False`, this is a new list.

    Notes:
        - TestResult objects with `metric_value.score is None` are treated as having
          a score of 0.0 (most severe failure).
        - Uses Python's Timsort algorithm, which is stable (preserves relative order
          of elements with equal scores).
        - In-place sorting has O(1) additional memory complexity, while non-in-place
          sorting has O(n) memory complexity (where n is the length of `test_results`).
    """

    def _get_score_key(test_result: TestResult) -> float:
        """Helper to extract the sorting key (metric score, handling None)."""
        return (
            test_result.metric_value.score
            if test_result.metric_value.score is not None
            else 0.0
        )

    if in_place:
        test_results.sort(key=_get_score_key, reverse=not ascending)
        return test_results
    else:
        return sorted(test_results, key=_get_score_key, reverse=not ascending)


def evaluate_prompt_sync(
    prompt_config: PromptConfig,
    dataset: BaseDataset,
    metric: BaseMetric,
    max_concurrency: int = 5,
    n_samples: Optional[int] = None,
    callbacks: Optional[Callbacks] = None,
    **kwargs: Any,
) -> ExperimentResult:
    """Blocking wrapper around the async evaluator."""

    async def _runner() -> ExperimentResult:
        return await evaluate_prompt(
            prompt_config,
            dataset,
            metric,
            max_concurrency,
            n_samples=n_samples,
            callbacks=callbacks,
        )

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Running inside an event loop (e.g., pytest-asyncio); spawn a thread
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _runner())
                return future.result()
        return loop.run_until_complete(_runner())
    except RuntimeError:
        # No running loop
        return asyncio.run(_runner())


async def evaluate_prompt(
    prompt_config: PromptConfig,
    dataset: BaseDataset,
    metric: BaseMetric,
    max_concurrency: int = 5,
    n_samples: Optional[int] = None,
    callbacks: Optional[Callbacks] = None,
    **kwargs: Any,
) -> ExperimentResult:
    """Evaluate a prompt on a dataset.

    This method:
    1. Samples test cases from the dataset
    2. Generates LLM responses for each test case
    3. Computes metric scores and collects detailed reasons
    4. Returns average score and test results (including reasons)

    Parameters
    ----------
    prompt_config : PromptConfig
        The prompt configuration to evaluate
    dataset : BaseDataset
        Dataset for evaluation
    metric : BaseMetric
        Metric for evaluation
    max_concurrency : int
        Maximum concurrency for evaluation (default: 5)
    n_samples : Optional[int]
        Number of samples to draw from dataset (default: all)
    callbacks : Optional[Callbacks]
        Callback handlers to register for evaluation
    **kwargs : Any
        Additional keyword arguments

    Returns
    -------
    ExperimentResult
        Contains average score and detailed test results with reasons

    Raises
    ------
    ValueError
        If prompt configuration is invalid
    Exception
        Propagates any errors from LLM generation or metric computation
    """
    samples = dataset.get_items(n_samples=n_samples)
    if not samples:
        raise ValueError(f"Dataset '{dataset.name}' has no items")

    experiment_name = dataset.name + ">|" + metric.name + "|"
    semaphore = asyncio.Semaphore(max_concurrency)
    test_results: List[TestResult] = []

    async def _evaluate_single(
        sample: Dict[str, Any], final_results: List[TestResult]
    ) -> None:
        async with semaphore:
            user_input = sample.get(LLMCaseParams.USER_INPUT.value, "")
            expected_output = sample.get(LLMCaseParams.EXPECTED_OUTPUT.value, "")
            context = sample.get(LLMCaseParams.CONTEXT.value)
            actual_output = await prompt_config.execute(sample)

            test_case = LLMCase(
                user_input=user_input,
                actual_output=actual_output,
                expected_output=expected_output,
                context=context if isinstance(context, list) else None,
                metadata={"dataset_item_id": sample.get("id")},
            )
            metric_value = await metric.compute(test_case, callbacks=callbacks)
            final_results.append(
                TestResult(test_case=test_case, metric_value=metric_value)
            )

    await asyncio.gather(
        *(_evaluate_single(sample, test_results) for sample in samples)
    )
    # sort_test_results_by_failure(test_results)
    return ExperimentResult(experiment_name=experiment_name, test_results=test_results)
