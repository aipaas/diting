from abc import ABC, abstractmethod
import typing as t
from pydantic import BaseModel

from diting_core.utilities.cache import CacheInterface, cacher
from diting_core.utilities.slug import camel_to_snake

DictOrPydanticClass = t.Union[t.Dict[str, t.Any], t.Type[BaseModel]]
DictOrPydantic = t.Union[t.Dict[str, t.Any], BaseModel]
_BM = t.TypeVar("_BM", bound=BaseModel)
PydanticClass = type[BaseModel]


class BaseLLM(ABC):
    cache: t.Optional[CacheInterface] = None

    def __init__(self, cache: t.Optional[CacheInterface] = None):
        self.cache = cache
        # If a cache_backend is provided, wrap the implementation methods at construction time.
        if self.cache is not None:
            self.generate = cacher(cache_backend=self.cache)(self.generate)
            self.generate_structured_output = cacher(cache_backend=self.cache)(
                self.generate_structured_output
            )

    @property
    def model_name(self) -> str:
        return camel_to_snake(self.__class__.__name__)

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        n: int = 1,
        temperature: t.Optional[float] = None,
        **kwargs: t.Any,
    ) -> str | t.List[str]:
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
