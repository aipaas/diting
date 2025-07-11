from abc import ABC, abstractmethod
import typing as t
from pydantic import BaseModel


DictOrPydanticClass = t.Union[t.Dict[str, t.Any], t.Type[BaseModel]]
DictOrPydantic = t.Union[t.Dict[str, t.Any], BaseModel]
_BM = t.TypeVar("_BM", bound=BaseModel)
PydanticClass = type[BaseModel]


class BaseLLM(ABC):
    @abstractmethod
    async def generate(self, *args: t.Any, **kwargs: t.Any) -> str:
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
        schema: t.Optional[PydanticClass] = None,  # noqa: UP006
        **kwargs: t.Any,
    ) -> DictOrPydantic:
        """
        Runs the model to output LLM structured response.

        Returns:
            A BaseModel instance.
        """
        ...
