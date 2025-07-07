"""
Base metric class and common metric implementations.
Provides the foundation for evaluation metrics with async support.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
from diting_inspect.models.case_model import LLMCase


class BaseLLM(ABC):
    """
    Abstract base class for language models.

    Defines interface for LLM interactions used by metrics.
    """

    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """
        Generate text using the language model.

        Args:
            prompt: Input prompt
            **kwargs: Additional generation parameters

        Returns:
            Generated text
        """
        raise NotImplementedError


class BaseMetric(ABC):
    """
    Abstract base class for evaluation metrics.

    Provides the interface and common functionality for all metrics
    used to evaluate LLM test cases.
    """

    def __init__(self, threshold: float = 0.8, model: Optional[BaseLLM] = None):
        """
        Initialize base metric.

        Args:
            threshold: Minimum score threshold for passing
            model: Optional LLM model for metric computation
        """
        self.threshold = threshold
        self.score: Optional[float] = None
        self.model = model

    @abstractmethod
    async def compute(
        self, test_case: LLMCase, *args: Tuple[Any], **kwargs: Dict[str, Any]
    ) -> float:
        """
        Compute the metric score for a test case.

        Args:
            test_case: Test case to evaluate
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Metric score (typically between 0.0 and 1.0)
        """
        raise NotImplementedError

    def is_passing(self, score: Optional[float] = None) -> bool:
        """
        Check if the metric score meets the threshold.

        Args:
            score: Score to check (uses self.score if not provided)

        Returns:
            True if score meets or exceeds threshold
        """
        check_score = score if score is not None else self.score
        return check_score is not None and check_score >= self.threshold

    @property
    def name(self) -> str:
        """Get the metric name."""
        return self.__class__.__name__
