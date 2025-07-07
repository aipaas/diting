"""
Factory for creating metric instances based on configuration.
"""

from diting_inspect.metrics.base_metric import BaseMetric
from diting_inspect.metrics.similarity_metrics import (
    ExactMatchMetric,
    LevenshteinSimilarityMetric,
    TokenOverlapMetric,
    LengthRatioMetric,
)


class MetricFactory:
    @staticmethod
    def create(metric_type: str, threshold: float) -> BaseMetric:
        """
        Create a metric instance based on the type and configuration.

        Args:
            metric_type: Type of the metric to create
            threshold: Threshold value for the metric

        Returns:
            An instance of a metric class
        """
        if metric_type == "exact_match":
            return ExactMatchMetric(threshold=threshold)
        elif metric_type == "levenshtein":
            return LevenshteinSimilarityMetric(threshold=threshold)
        elif metric_type == "token_overlap":
            return TokenOverlapMetric(threshold=threshold)
        elif metric_type == "length_ratio":
            return LengthRatioMetric(threshold=threshold)
        else:
            raise ValueError(f"Unknown metric type: {metric_type}")
