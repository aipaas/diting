from typing import Any, Dict, Tuple
from diting.cases.llm_case import LLMCase
from diting.metrics.base_metric import BaseMetric


class LengthRatioExampleMetric(BaseMetric):
    """
    A metric that computes the ratio of the length of the actual output
    to the length of the expected output for a given LLMCase.

    This metric is useful for evaluating the performance of language models
    by comparing the lengths of their generated outputs against expected outputs.
    A higher ratio indicates that the actual output is closer in length to the
    expected output, which may correlate with better performance in certain tasks.

    Note: This is an example metric only.

    Attributes:
        score (float): The computed length ratio score.
    """

    async def compute(
        self, test_case: LLMCase, *args: Tuple[Any], **kwargs: Dict[str, Any]
    ) -> float:
        """
        Compute the ratio of actual output length to expected output length.

        Args:
            test_case (LLMCase): The LLMCase to evaluate.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            float: The length ratio, or 0 if no expected output exists.
        """
        expected_length = (
            len(test_case.expected_output) if test_case.expected_output else 0
        )
        actual_length = len(test_case.actual_output)

        if expected_length > 0:
            self.score = actual_length / expected_length
            return self.score
        return 0.0
