import asyncio
import unittest
from time import sleep
from typing import List, Any, Optional

from langchain_core.embeddings import Embeddings

from diting_core.models.embeddings.base_model import BaseEmbeddings
from diting_core.models.embeddings.openai_model import (
    LangchainEmbeddingsWrapper,
)
from diting_core.utilities.cache import DiskCacheBackend, CacheInterface


class DummyLangchainEmbedding(Embeddings):
    def __init__(self):
        self.call_count: int = 0

    def embed_query(self, text: str) -> List[float]:
        self.call_count += 1
        sleep(0.1)
        return [1.1, 1.2, 1.3]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        self.call_count += 1
        sleep(0.1)
        return [[1.1, 1.2, 1.3] for _ in texts]

    async def aembed_query(self, text: str) -> List[float]:
        self.call_count += 1
        await asyncio.sleep(0.1)
        return [1.1, 1.2, 1.3]

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        self.call_count += 1
        await asyncio.sleep(0.1)
        return [[1.1, 1.2, 1.3] for _ in texts]


class MockEmbeddings(BaseEmbeddings):
    def __init__(self, cache: Optional[CacheInterface] = None):
        super().__init__(cache)
        self.call_count: int = 0

    async def embed_text(self, text: str, **kwargs: Any) -> List[float]:
        self.call_count += 1
        await asyncio.sleep(0.1)
        return [0.1, 0.2, 0.3]

    async def embed_texts(self, texts: List[str], **kwargs: Any) -> List[List[float]]:
        self.call_count += 1
        await asyncio.sleep(0.1)
        return [[0.1, 0.2, 0.3] for _ in texts]


class TestEmbeddingCache(unittest.IsolatedAsyncioTestCase):
    async def test_langchain_embed_with_cache_backend(self):
        """Test that caching works for async functions when a backend is provided."""
        embedding = DummyLangchainEmbedding()
        wrapper = LangchainEmbeddingsWrapper(
            embeddings=embedding,
            cache=DiskCacheBackend(".cache/test_langchain_embed_with_cache_backend"),
        )

        # First call: should run the function
        result1 = await wrapper.embed_text("aaa")
        assert result1 == [1.1, 1.2, 1.3]
        assert embedding.call_count == 1

        # Second call with same args: should return cached result
        result2 = await wrapper.embed_text("aaa")
        assert result2 == [1.1, 1.2, 1.3]
        assert embedding.call_count == 1, "Should have come from cache"

    async def test_langchain_embed_without_cache_backend(self):
        """Test that caching works for async functions when a backend is provided."""
        embedding = DummyLangchainEmbedding()
        wrapper = LangchainEmbeddingsWrapper(embeddings=embedding)

        # First call: should run the function
        result1 = await wrapper.embed_text("aaa")
        assert result1 == [1.1, 1.2, 1.3]
        assert embedding.call_count == 1

        # Second call with same args: should return cached result
        result2 = await wrapper.embed_text("aaa")
        assert result2 == [1.1, 1.2, 1.3]
        assert embedding.call_count == 2, "Should not have come from cache"

    async def test_custom_embed_with_cache_backend(self):
        """Test that caching works for async functions when a backend is provided."""
        embedding = MockEmbeddings(
            cache=DiskCacheBackend(".cache/test_custom_embed_with_cache_backend")
        )

        # First call: should run the function
        result1 = await embedding.embed_text("aaa")
        assert result1 == [0.1, 0.2, 0.3]
        assert embedding.call_count == 1

        # Second call with same args: should return cached result
        result2 = await embedding.embed_text("aaa")
        assert result2 == [0.1, 0.2, 0.3]
        assert embedding.call_count == 1, "Should have come from cache"

    async def test_custom_embed_without_cache_backend(self):
        """Test that caching works for async functions when a backend is provided."""
        embedding = MockEmbeddings()

        # First call: should run the function
        result1 = await embedding.embed_text("aaa")
        assert result1 == [0.1, 0.2, 0.3]
        assert embedding.call_count == 1

        # Second call with same args: should return cached result
        result2 = await embedding.embed_text("aaa")
        assert result2 == [0.1, 0.2, 0.3]
        assert embedding.call_count == 2, "Should not have come from cache"


if __name__ == "__main__":
    unittest.main()
