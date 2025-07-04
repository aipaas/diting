from abc import ABC, abstractmethod
import typing as t
from pydantic import BaseModel

_BM = t.TypeVar("_BM", bound=BaseModel)
_DictOrPydanticClass = t.Union[dict[str, t.Any], type[_BM], type]
_Pydantic = _BM


class BaseLLM(ABC):
    @abstractmethod
    async def generate(self, *args: t.Any, **kwargs: t.Dict[str, t.Any]) -> str:
        """
        Runs the model to output LLM response.

        Returns:
            A string.
        """
        ...

    @abstractmethod
    async def generate_structured_output(
        self,
        prompt: str,
        schema: t.Optional[_DictOrPydanticClass] = None,
        **kwargs: t.Any,
    ) -> _Pydantic:
        """
        Runs the model to output LLM structured response.

        Returns:
            A BaseModel instance.
        """
        ...
