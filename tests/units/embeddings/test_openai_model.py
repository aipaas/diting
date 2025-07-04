import unittest
from unittest.mock import MagicMock, AsyncMock
from langchain_core.embeddings import Embeddings
from typing import List
from diting.models.embeddings.openai_model import (
    PrivateEmbeddings,
    LangchainEmbeddingsWrapper,
)


class TestPrivateEmbeddingsSync(unittest.TestCase):
    def setUp(self):
        # Mock 同步 client
        self.mock_sync_client = MagicMock()
        self.mock_sync_client.embeddings.create.return_value.data = [
            MagicMock(embedding=[0.1, 0.2, 0.3]),
            MagicMock(embedding=[0.4, 0.5, 0.6]),
        ]
        self.emb = PrivateEmbeddings(
            model="test-model",
            client=self.mock_sync_client,
        )

    def test_embed_query(self):
        result = self.emb.embed_query("hello")
        self.assertEqual(result, [0.1, 0.2, 0.3])
        self.mock_sync_client.embeddings.create.assert_called_once_with(
            model="test-model", input=["hello"]
        )

    def test_embed_documents(self):
        result = self.emb.embed_documents(["a", "b"])
        self.assertEqual(result, [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
        self.mock_sync_client.embeddings.create.assert_called_once_with(
            model="test-model", input=["a", "b"]
        )


class TestPrivateEmbeddingsAsync(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_async_client = MagicMock()
        async_create = AsyncMock()
        async_create.return_value.data = [
            MagicMock(embedding=[0.1, 0.2, 0.3]),
            MagicMock(embedding=[0.4, 0.5, 0.6]),
        ]
        self.mock_async_client.embeddings.create = async_create

        self.emb = PrivateEmbeddings(
            model="test-model", client=None, async_client=self.mock_async_client
        )

    async def test_aembed_query(self):
        result = await self.emb.aembed_query("async-hello")
        self.assertEqual(result, [0.1, 0.2, 0.3])

    async def test_aembed_documents(self):
        result = await self.emb.aembed_documents(["x", "y"])
        self.assertEqual(result, [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])


class DummyLangchainEmbedding(Embeddings):
    def embed_query(self, text: str) -> List[float]:
        return [1.1, 1.2, 1.3]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [[1.1, 1.2, 1.3] for _ in texts]

    async def aembed_query(self, text: str) -> List[float]:
        return [1.1, 1.2, 1.3]

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        return [[1.1, 1.2, 1.3] for _ in texts]


class TestLangchainEmbeddingsWrapper(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.wrapper = LangchainEmbeddingsWrapper(embeddings=DummyLangchainEmbedding())

    def test_repr(self):
        self.assertIn("LangchainEmbeddingsWrapper", repr(self.wrapper))

    async def test_aembed_query(self):
        result = await self.wrapper.aembed_query("query")
        self.assertEqual(result, [1.1, 1.2, 1.3])

    async def test_aembed_documents(self):
        result = await self.wrapper.aembed_documents(["d1", "d2"])
        self.assertEqual(result, [[1.1, 1.2, 1.3], [1.1, 1.2, 1.3]])

    async def test_aembed_query_type_error(self):
        with self.assertRaises(TypeError):
            await self.wrapper.aembed_query(123)  # type: ignore

    async def test_aembed_documents_type_error(self):
        with self.assertRaises(TypeError):
            await self.wrapper.aembed_documents("not-a-list")  # type: ignore


if __name__ == "__main__":
    unittest.main()
