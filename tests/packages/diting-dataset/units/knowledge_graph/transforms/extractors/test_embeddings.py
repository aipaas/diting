#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest
from typing import List

from diting_core.models.embeddings.base_model import BaseEmbeddings
from diting_dataset.knowledge_graph.schema import Node
from diting_dataset.knowledge_graph.transforms.extractors.embeddings import (
    EmbeddingExtractor,
)


class MockEmbeddings(BaseEmbeddings):
    async def aembed_query(self, text: str) -> List[float]:
        return [0.1, 0.2, 0.4]

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]


class TestEmbeddingExtractor(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # 创建一个 EmbeddingExtractor 实例
        self.extractor = EmbeddingExtractor(embedding_model=MockEmbeddings())

    async def test_extract_valid_node(self):
        # 创建一个有效的 Node
        node = Node(properties={"page_content": "This is a test."})

        # 调用 extract 方法
        property_name, embedding = await self.extractor.extract(node)

        # 验证返回值
        self.assertEqual(property_name, "embedding")
        self.assertEqual(embedding, [0.1, 0.2, 0.3])

    async def test_extract_invalid_node_property(self):
        # 创建一个包含非字符串属性的 Node
        node = Node(properties={"page_content": 12345})

        # 验证提取时抛出 ValueError
        with self.assertRaises(ValueError) as context:
            await self.extractor.extract(node)

        self.assertEqual(
            str(context.exception),
            "node.property('page_content') must be a string, found '<class 'int'>'",
        )


if __name__ == "__main__":
    unittest.main()
