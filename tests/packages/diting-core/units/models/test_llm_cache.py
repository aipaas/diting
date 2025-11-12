import asyncio
import typing as t
import unittest
from time import sleep
from typing import Any

from langchain_core.callbacks import Callbacks
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult, Generation
from langchain_core.prompt_values import PromptValue
from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.utils import Input, Output

from diting_core.models.llms.base_model import (
    BaseLLM,
    DictOrPydanticClass,
    DictOrPydantic,
)
from diting_core.models.llms.openai_model import LangchainLLMWrapper
from diting_core.utilities.cache import DiskCacheBackend


class MockLLM(BaseLLM):
    call_count = 0

    async def generate(
        self, *args: t.Tuple[t.Any], **kwargs: t.Dict[str, t.Any]
    ) -> str:
        self.call_count += 1
        await asyncio.sleep(0.1)
        return "Generated Response"

    async def generate_structured_output(
        self,
        prompt: str,
        schema: t.Optional[DictOrPydanticClass] = None,
        **kwargs: t.Any,
    ) -> DictOrPydantic:
        self.call_count += 1
        await asyncio.sleep(0.1)
        return {"testkey": "testval"}


class MockLangchainLLM(BaseLanguageModel[BaseMessage]):
    call_count: int = 0

    def invoke(
        self, input: Input, config: RunnableConfig | None = None, **kwargs: Any
    ) -> Output:
        self.call_count += 1
        sleep(0.1)
        return {"testkey": "testval"}

    def generate_prompt(
        self,
        prompts: list[PromptValue],
        stop: list[str] | None = None,
        callbacks: Callbacks = None,
        **kwargs: Any,
    ) -> LLMResult:
        self.call_count += 1
        sleep(0.1)
        return LLMResult(generations=[[Generation(text='{"testkey": "testval"}')]])

    async def agenerate_prompt(
        self,
        prompts: list[PromptValue],
        stop: list[str] | None = None,
        callbacks: Callbacks = None,
        **kwargs: Any,
    ) -> LLMResult:
        self.call_count += 1
        await asyncio.sleep(0.1)
        return LLMResult(generations=[[Generation(text='{"testkey": "testval"}')]])


class TestLLMCache(unittest.IsolatedAsyncioTestCase):
    async def test_custom_llm_with_cache_backend(self):
        """Test that caching works for async functions when a backend is provided."""
        llm = MockLLM(
            cache=DiskCacheBackend(".cache/test_custom_llm_with_cache_backend")
        )

        # First call: should run the function
        result1 = await llm.generate_structured_output("aaa")
        assert result1 == {"testkey": "testval"}
        assert llm.call_count == 1

        # Second call with same args: should return cached result
        result2 = await llm.generate_structured_output("aaa")
        assert result2 == {"testkey": "testval"}
        assert llm.call_count == 1, "Should have come from cache"

    async def test_custom_llm_without_cache_backend(self):
        """Test that caching works for async functions when a backend is provided."""
        llm = MockLLM()

        # First call: should run the function
        result1 = await llm.generate_structured_output("aaa")
        assert result1 == {"testkey": "testval"}
        assert llm.call_count == 1

        # Second call with same args: should return cached result
        result2 = await llm.generate_structured_output("aaa")
        assert result2 == {"testkey": "testval"}
        assert llm.call_count == 2, "Should not have come from cache"

    async def test_langchain_llm_with_cache_backend(self):
        """Test that caching works for async functions when a backend is provided."""
        mock_llm = MockLangchainLLM()
        wrapper = LangchainLLMWrapper(
            llm=mock_llm,
            is_guided_json_support=True,
            cache=DiskCacheBackend(".cache/test_langchain_llm_with_cache_backend"),
        )

        # First call: should run the function
        result1 = await wrapper.generate_structured_output("aaa")
        assert result1 == {"testkey": "testval"}
        assert mock_llm.call_count == 1

        # Second call with same args: should return cached result
        result2 = await wrapper.generate_structured_output("aaa")
        assert result2 == {"testkey": "testval"}
        assert mock_llm.call_count == 1, "Should have come from cache"

    async def test_langchain_llm_without_cache_backend(self):
        """Test that caching works for async functions when a backend is provided."""
        mock_llm = MockLangchainLLM()
        wrapper = LangchainLLMWrapper(
            llm=mock_llm,
            is_guided_json_support=True,
        )

        # First call: should run the function
        result1 = await wrapper.generate_structured_output("aaa")
        assert result1 == {"testkey": "testval"}
        assert mock_llm.call_count == 1

        # Second call with same args: should return cached result
        result2 = await wrapper.generate_structured_output("aaa")
        assert result2 == {"testkey": "testval"}
        assert mock_llm.call_count == 2, "Should not have come from cache"


if __name__ == "__main__":
    unittest.main()
