"""
Text similarity metrics for evaluating LLM outputs.
Implements various similarity measures for comparing expected vs actual outputs.
"""

from typing import Dict, Any, Tuple
from diting_inspect.metrics.base_metric import BaseMetric
from diting_inspect.models.case_model import LLMCase
import difflib
import re


class ExactMatchMetric(BaseMetric):
    """
    Exact string match metric.

    Compares actual output with expected output for exact equality.
    Useful for cases where precision is critical.
    """

    def __init__(self, threshold: float = 1.0, case_sensitive: bool = True):
        """
        Initialize exact match metric.

        Args:
            threshold: Score threshold (typically 1.0 for exact match)
            case_sensitive: Whether to perform case-sensitive comparison
        """
        super().__init__(threshold)
        self.case_sensitive = case_sensitive

    async def compute(
        self, test_case: LLMCase, *args: Tuple[Any], **kwargs: Dict[str, Any]
    ) -> float:
        """
        Compute exact match score.

        Args:
            test_case: Test case containing actual and expected outputs

        Returns:
            1.0 if exact match, 0.0 otherwise
        """
        if not test_case.expected_output:
            raise ValueError("Expected output is required for exact match metric")

        actual = test_case.actual_output
        expected = test_case.expected_output

        if not self.case_sensitive:
            actual = actual.lower()
            expected = expected.lower()

        self.score = 1.0 if actual == expected else 0.0
        return self.score


class LevenshteinSimilarityMetric(BaseMetric):
    """
    Levenshtein distance-based similarity metric.

    Computes similarity based on edit distance between strings.
    Good for measuring how close outputs are character-wise.
    """

    async def compute(
        self, test_case: LLMCase, *args: Tuple[Any], **kwargs: Dict[str, Any]
    ) -> float:
        """
        Compute Levenshtein similarity score.

        Args:
            test_case: Test case containing actual and expected outputs

        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not test_case.expected_output:
            raise ValueError("Expected output is required for similarity metric")

        actual = test_case.actual_output.strip()
        expected = test_case.expected_output.strip()

        if not actual and not expected:
            self.score = 1.0
        elif not actual or not expected:
            self.score = 0.0
        else:
            # Use difflib's sequence matcher for similarity
            similarity = difflib.SequenceMatcher(None, actual, expected).ratio()
            self.score = similarity

        return self.score


class TokenOverlapMetric(BaseMetric):
    """
    Token overlap similarity metric.

    Computes similarity based on overlapping tokens (words) between
    actual and expected outputs. Less sensitive to word order.
    """

    def __init__(self, threshold: float = 0.8, case_sensitive: bool = False):
        """
        Initialize token overlap metric.

        Args:
            threshold: Score threshold
            case_sensitive: Whether to perform case-sensitive comparison
        """
        super().__init__(threshold)
        self.case_sensitive = case_sensitive

    async def compute(
        self, test_case: LLMCase, *args: Tuple[Any], **kwargs: Dict[str, Any]
    ) -> float:
        """
        Compute token overlap score.

        Args:
            test_case: Test case containing actual and expected outputs

        Returns:
            Jaccard similarity score between 0.0 and 1.0
        """
        if not test_case.expected_output:
            raise ValueError("Expected output is required for token overlap metric")

        actual = test_case.actual_output
        expected = test_case.expected_output

        if not self.case_sensitive:
            actual = actual.lower()
            expected = expected.lower()

        # Tokenize (simple word splitting)
        actual_tokens = set(re.findall(r"\w+", actual))
        expected_tokens = set(re.findall(r"\w+", expected))

        if not actual_tokens and not expected_tokens:
            self.score = 1.0
        elif not actual_tokens or not expected_tokens:
            self.score = 0.0
        else:
            # Jaccard similarity
            intersection = len(actual_tokens.intersection(expected_tokens))
            union = len(actual_tokens.union(expected_tokens))
            self.score = intersection / union if union > 0 else 0.0

        return self.score


class LengthRatioMetric(BaseMetric):
    """
    Response length ratio metric.

    Evaluates if the actual output length is appropriate compared
    to the expected output length. Useful for checking verbosity.
    """

    def __init__(self, threshold: float = 0.8, tolerance: float = 0.3):
        """
        Initialize length ratio metric.

        Args:
            threshold: Score threshold
            tolerance: Acceptable deviation from ideal ratio (±)
        """
        super().__init__(threshold)
        self.tolerance = tolerance

    async def compute(
        self, test_case: LLMCase, *args: Tuple[Any], **kwargs: Dict[str, Any]
    ) -> float:
        """
        Compute length ratio score.

        Args:
            test_case: Test case containing actual and expected outputs

        Returns:
            Score based on length similarity (0.0 to 1.0)
        """
        if not test_case.expected_output:
            # If no expected output, check if actual is reasonable length
            actual_len = len(test_case.actual_output.strip())
            # Assume reasonable response is 10-1000 characters
            if 10 <= actual_len <= 1000:
                self.score = 1.0
            else:
                self.score = max(0.0, 1.0 - abs(actual_len - 100) / 1000)
        else:
            actual_len = len(test_case.actual_output.strip())
            expected_len = len(test_case.expected_output.strip())

            if expected_len == 0:
                self.score = 1.0 if actual_len == 0 else 0.0
            else:
                ratio = actual_len / expected_len
                # Score based on how close ratio is to 1.0
                deviation = abs(ratio - 1.0)
                self.score = max(0.0, 1.0 - deviation / (1.0 + self.tolerance))

        return self.score
