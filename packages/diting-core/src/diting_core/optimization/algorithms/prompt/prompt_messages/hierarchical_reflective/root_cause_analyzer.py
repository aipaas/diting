"""Hierarchical root cause analyzer.

Adapted from Opik's hierarchical_root_cause_analyzer.py with minimal changes for Diting.
"""

import logging
import asyncio
from typing import Any, Callable, Optional

from diting_core.callbacks.base import Callbacks
from diting_core.cases.llm_case import LLMCaseParams
from diting_core.optimization.algorithms.prompt.prompt_messages.hierarchical_reflective.types import (
    RootCauseAnalysis,
    BatchAnalysis,
    HierarchicalRootCauseAnalysis,
)
from diting_core.optimization.algorithms.prompt.prompt_messages.hierarchical_reflective.prompts import (
    BATCH_ANALYSIS_PROMPT,
    SYNTHESIS_PROMPT,
)

logger = logging.getLogger(__name__)


class HierarchicalRootCauseAnalyzer:
    """
    Performs hierarchical root cause analysis on evaluation results.

    This analyzer splits large evaluation datasets into manageable batches,
    performs root cause analysis on each batch in parallel (up to 5 batches
    concurrently by default), then combines and summarizes the results to
    identify the most important failure patterns.

    Args:
        call_model_fn: Async function to call the LLM with structured output
        seed: Random seed for reproducibility
        max_parallel_batches: Maximum number of batches to process concurrently (default: 5)
        batch_size: Number of test cases per batch for analysis (default: 25)
    """

    def __init__(
        self,
        call_model_fn: Callable,
        seed: int = 42,
        max_parallel_batches: int = 5,
        batch_size: int = 25,
    ) -> None:
        """
        Initialize the hierarchical root cause analyzer.

        Args:
            call_model_fn: Async function to call the LLM (signature: async fn(messages, seed, response_model) -> T)
            seed: Random seed for reproducibility
            max_parallel_batches: Maximum number of batches to process concurrently (default: 5)
            batch_size: Number of test cases per batch for analysis (default: 25)
        """
        self.call_model_fn = call_model_fn
        self.seed = seed
        self.max_parallel_batches = max_parallel_batches
        self.batch_size = batch_size

    def _format_test_results_batch(
        self,
        test_results: list[dict[str, Any]],
        batch_start: int,
        batch_end: int,
    ) -> str:
        """
        Format a batch of test results for analysis.

        Args:
            test_results: Full list of test results (each is a dict with 'user_input', 'actual_output', 'expected_output', 'score', 'reason')
            batch_start: Starting index of the batch
            batch_end: Ending index of the batch (exclusive)

        Returns:
            Formatted string containing test result details
        """
        formatted_results = []

        for idx in range(batch_start, min(batch_end, len(test_results))):
            test_result = test_results[idx]

            # Format this test result
            result_text = f"""Test Case #{idx + 1}
Input: {test_result.get(LLMCaseParams.USER_INPUT.value, "N/A")}
Output: {test_result.get(LLMCaseParams.ACTUAL_OUTPUT.value, "N/A")}
Expected: {test_result.get(LLMCaseParams.EXPECTED_OUTPUT.value, "N/A")}
Score: {test_result.get("score", 0):.3f}
Reason: {test_result.get("reason", "N/A")}"""

            formatted_results.append(result_text)

        return "\n\n" + ("=" * 80 + "\n\n").join(formatted_results)

    async def _analyze_batch(
        self,
        test_results: list[dict[str, Any]],
        batch_number: int,
        batch_start: int,
        batch_end: int,
        callbacks: Optional[Callbacks] = None,
    ) -> BatchAnalysis:
        """
        Analyze a single batch of test results asynchronously.

        Args:
            test_results: The full list of test results
            batch_number: The batch number (1-indexed)
            batch_start: Starting index in test_results
            batch_end: Ending index in test_results (exclusive)

        Returns:
            BatchAnalysis containing failure modes for this batch
        """
        actual_end = min(batch_end, len(test_results))

        logger.debug(
            f"Analyzing batch {batch_number}: "
            f"test cases {batch_start + 1} to {actual_end}"
        )

        formatted_batch = self._format_test_results_batch(
            test_results, batch_start, batch_end
        )

        batch_analysis_prompt = BATCH_ANALYSIS_PROMPT.format(
            formatted_batch=formatted_batch,
        )

        root_cause_response = await self.call_model_fn(
            messages=[{"role": "user", "content": batch_analysis_prompt}],
            seed=self.seed,
            response_model=RootCauseAnalysis,
            callbacks=callbacks,
        )

        return BatchAnalysis(
            batch_number=batch_number,
            start_index=batch_start,
            end_index=actual_end,
            failure_modes=root_cause_response.failure_modes,
        )

    async def _synthesize_batch_analyses(
        self,
        test_results: list[dict[str, Any]],
        batch_analyses: list[BatchAnalysis],
        callbacks: Optional[Callbacks] = None,
    ) -> HierarchicalRootCauseAnalysis:
        """
        Synthesize multiple batch analyses into a unified root cause analysis asynchronously.

        Args:
            test_results: The full list of test results
            batch_analyses: List of batch analysis results

        Returns:
            HierarchicalRootCauseAnalysis with unified failure modes
        """
        logger.debug(
            f"Synthesizing {len(batch_analyses)} batch analyses "
            f"from {len(test_results)} total test cases"
        )

        # Format all batch analyses for synthesis
        batch_summaries = []
        for batch_analysis in batch_analyses:
            failure_list = []
            for fm in batch_analysis.failure_modes:
                failure_list.append(
                    f"  - {fm.name}\n"
                    f"    Description: {fm.description}\n"
                    f"    Root Cause: {fm.root_cause}"
                )

            summary = f"""Batch {batch_analysis.batch_number} (Test Cases {batch_analysis.start_index + 1}-{batch_analysis.end_index}):
{chr(10).join(failure_list)}"""
            batch_summaries.append(summary)

        synthesis_prompt = SYNTHESIS_PROMPT.format(
            batch_summaries=chr(10).join(batch_summaries),
        )

        synthesis_response = await self.call_model_fn(
            messages=[{"role": "user", "content": synthesis_prompt}],
            seed=self.seed,
            response_model=HierarchicalRootCauseAnalysis,
            callbacks=callbacks,
        )

        return synthesis_response

    def _validate_reasons_present(self, test_results: list[dict[str, Any]]) -> None:
        """
        Validate that test results include reasons for scoring.

        Args:
            test_results: List of test results to validate

        Raises:
            ValueError: If no test results have reasons
        """
        if not test_results:
            return

        has_reasons = False
        for test_result in test_results:
            if test_result.get("reason") and test_result["reason"].strip():
                has_reasons = True
                break

        if not has_reasons:
            raise ValueError(
                "Test results must include 'reason' fields for hierarchical "
                "root cause analysis to work effectively. Reasons are critical for identifying "
                "failure patterns and root causes. Please ensure your scoring metrics provide "
                "detailed reasons for their scores."
            )

    async def analyze(
        self,
        test_results: list[dict[str, Any]],
        callbacks: Optional[Callbacks] = None,
    ) -> HierarchicalRootCauseAnalysis:
        """
        Perform hierarchical root cause analysis on evaluation results asynchronously.

        This method:
        1. Validates that test results include reasons (critical for analysis)
        2. Splits test results into batches of batch_size
        3. Analyzes batches concurrently (up to max_parallel_batches at once)
        4. Synthesizes batch analyses into unified failure modes

        Args:
            test_results: List of test results (each is a dict with 'input', 'output', 'expected', 'score', 'reason')
            callbacks: callbacks for log and llm cost calc

        Returns:
            HierarchicalRootCauseAnalysis with unified failure modes and synthesis notes

        Raises:
            ValueError: If test results don't include reasons, which are critical for analysis
        """
        num_test_results = len(test_results)

        # Validate that reasons are present in test results
        self._validate_reasons_present(test_results)

        logger.info(
            f"Starting hierarchical root cause analysis on {num_test_results} test cases"
        )

        # Prepare batch tasks
        batch_tasks = []
        batch_number = 1
        for batch_start in range(0, num_test_results, self.batch_size):
            batch_end = min(batch_start + self.batch_size, num_test_results)
            task = self._analyze_batch(
                test_results=test_results,
                batch_number=batch_number,
                batch_start=batch_start,
                batch_end=batch_end,
                callbacks=callbacks,
            )
            batch_tasks.append((batch_number, task))
            batch_number += 1

        # Process batches with semaphore to limit concurrency
        logger.info(
            f"Processing {len(batch_tasks)} batches concurrently "
            f"(max {self.max_parallel_batches} at once)"
        )

        semaphore = asyncio.Semaphore(self.max_parallel_batches)

        async def run_with_semaphore(
            batch_num: int, task: Any
        ) -> tuple[int, BatchAnalysis]:
            async with semaphore:
                try:
                    result = await task
                    logger.debug(
                        f"Completed batch {batch_num}: "
                        f"identified {len(result.failure_modes)} failure modes"
                    )
                    return batch_num, result
                except Exception as exc:
                    logger.error(f"Batch {batch_num} failed: {exc}")
                    raise

        # Run all tasks with semaphore control
        results = await asyncio.gather(
            *[run_with_semaphore(num, task) for num, task in batch_tasks]
        )

        # Sort by batch number to maintain order
        batch_analyses = [result for _, result in sorted(results)]

        logger.info(
            f"Stage 1 complete: Analyzed {len(batch_analyses)} batches, "
            f"total {sum(len(ba.failure_modes) for ba in batch_analyses)} failure modes"
        )

        # Stage 2: Synthesize batch analyses
        logger.info("Stage 2: Synthesizing batch analyses...")

        hierarchical_analysis = await self._synthesize_batch_analyses(
            test_results=test_results,
            batch_analyses=batch_analyses,
            callbacks=callbacks,
        )

        logger.info(
            f"Synthesis complete: "
            f"identified {len(hierarchical_analysis.unified_failure_modes)} unified failure modes"
        )

        return hierarchical_analysis
