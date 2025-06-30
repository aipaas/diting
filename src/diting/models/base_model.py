from abc import ABC, abstractmethod
from typing import List, Any, Dict


class BaseLLM(ABC):
    @abstractmethod
    def load_model(self, *args: Any, **kwargs: Dict[str, Any]):
        """Loads a model, that will be responsible for scoring.

        Returns:
            A model object
        """
        pass

    @abstractmethod
    def generate(self, *args: Any, **kwargs: Dict[str, Any]) -> str:
        """Runs the model to output LLM response.

        Returns:
            A string.
        """
        pass

    @abstractmethod
    async def a_generate(self, *args: Any, **kwargs: Dict[str, Any]) -> str:
        """Runs the model to output LLM response.

        Returns:
            A string.
        """
        pass

    def batch_generate(self, *args: Any, **kwargs: Dict[str, Any]) -> List[str]:
        """Runs the model to output LLM responses.

        Returns:
            A list of strings.
        """
        raise AttributeError

    @abstractmethod
    def get_model_name(self, *args: Any, **kwargs: Dict[str, Any]) -> str:
        pass
