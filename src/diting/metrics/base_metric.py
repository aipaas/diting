from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple

from diting.cases.llm_case import LLMCase
from diting.models.base_model import BaseLLM


class BaseMetric(ABC):
    threshold: float
    score: Optional[float] = None
    score_breakdown: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    success: Optional[bool] = None
    evaluation_model: Optional[str] = None
    strict_mode: bool = False
    async_mode: bool = True
    verbose_mode: bool = True
    include_reason: bool = False
    error: Optional[str] = None
    evaluation_cost: Optional[float] = None
    verbose_logs: Optional[str] = None
    skipped = False
    model = Optional[BaseLLM]

    @abstractmethod
    def compute(
        self, test_case: LLMCase, *args: Tuple[Any], **kwargs: Dict[str, Any]
    ) -> float:
        """Compute the metric."""
        raise NotImplementedError

    @abstractmethod
    async def acompute(
        self, test_case: LLMCase, *args: Tuple[Any], **kwargs: Dict[str, Any]
    ) -> float:
        """Asynchronously compute the metric."""
        raise NotImplementedError(
            f"Async compute for {self.__class__.__name__} not supported yet."
        )
