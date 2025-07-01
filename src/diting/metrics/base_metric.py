from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple

from diting.cases.llm_case import LLMCase
from diting.models.base_model import BaseLLM


class BaseMetric(ABC):
    threshold: float
    score: Optional[float] = None
    model = Optional[BaseLLM]

    @abstractmethod
    async def compute(
        self, test_case: LLMCase, *args: Tuple[Any], **kwargs: Dict[str, Any]
    ) -> float:
        """Compute the metric."""
        raise NotImplementedError
