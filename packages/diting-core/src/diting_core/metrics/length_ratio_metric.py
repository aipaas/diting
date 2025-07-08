from typing import Any, List
from diting_core.cases.llm_case import LLMCase, LLMCaseParams
from diting_core.metrics.base_metric import BaseMetric, MetricValue


class LengthRatioExampleMetric(BaseMetric):
    """
    A metric that computes the ratio of the length of the actual output
    to the length of the expected output for a given LLMCase.

    This metric is useful for evaluating the performance of language models
    by comparing the lengths of their generated outputs against expected outputs.
    A higher ratio indicates that the actual output is closer in length to the
    expected output, which may correlate with better performance in certain tasks.

    Note: This is an example metric only.

    Constraints:
        To use the LengthRatioExampleMetric, you'll have to provide the following arguments when creating an LLMTestCase:
            - expected_output
            - actual_output
        The expected_output and actual_output are required to create an LLMCase (and hence required by all metrics)
        even though they might not be used for metric calculation.
    """

    _required_params: List[LLMCaseParams] = [
        LLMCaseParams.EXPECTED_OUTPUT,
        LLMCaseParams.ACTUAL_OUTPUT,
    ]
    debug: bool = False
    threshold: float = 1.0

    async def _compute(
        self, test_case: LLMCase, *args: Any, **kwargs: Any
    ) -> MetricValue:
        """
        Compute the ratio of actual output length to expected output length.

        Args:
            test_case (LLMCase): The LLMCase to evaluate.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            MetricValue: whose score calculate by the length ratio, or 0 if no expected output exists.
        """

        assert test_case.expected_output is not None
        assert test_case.actual_output is not None

        expected_length = (
            len(test_case.expected_output) if test_case.expected_output else 0
        )
        actual_length = len(test_case.actual_output)

        score = 0.0
        if expected_length > 0:
            score = actual_length / expected_length
        return MetricValue(score=score)
