#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# !/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest
import numpy as np
from diting_dataset.knowledge_graph.graph import (
    KnowledgeGraph,
    Node,
    NodeType,
)
from diting_dataset.knowledge_graph.transforms.relationship_builders.cosine import (
    CosineSimilarityBuilder,
    SummaryCosineSimilarityBuilder,
)


class TestCosineSimilarityBuilder(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # 创建一个知识图谱实例
        self.nodes = [
            Node(properties={"embedding": [1.0, 0.0, 0.0]}),
            Node(properties={"embedding": [0.0, 1.0, 0.0]}),
            Node(properties={"embedding": [0.0, 0.0, 1.0]}),
            Node(properties={"embedding": [1.0, 1.0, 0.0]}),
        ]
        self.kg = KnowledgeGraph(nodes=self.nodes)
        self.builder = CosineSimilarityBuilder(threshold=0.6)

    async def test_transform_valid(self):
        relationships = await self.builder.transform(self.kg)
        self.assertEqual(len(relationships), 2)  # (0, 3) 和 (1, 3)

    async def test_transform_invalid_node_property(self):
        self.nodes[0].properties["embedding"] = None  # 设置无效的嵌入
        with self.assertRaises(ValueError) as context:
            await self.builder.transform(self.kg)
        self.assertIn("has no embedding", str(context.exception))

    async def test_validate_embedding_shapes_valid(self):
        embeddings = [[1, 2], [2, 3], [3, 4]]
        self.builder._validate_embedding_shapes(embeddings)  # 应该不抛出异常

    async def test_validate_embedding_shapes_invalid(self):
        embeddings = [[1, 2], [2, 3, 4]]  # 不同长度的嵌入
        with self.assertRaises(ValueError) as context:
            self.builder._validate_embedding_shapes(embeddings)
        self.assertIn(
            "Embedding at index 1 has length 3, expected 2.", str(context.exception)
        )

    async def test_find_similar_embedding_pairs(self):
        embeddings = np.array([[1, 0], [0, 1], [1, 1]])
        pairs = self.builder._find_similar_embedding_pairs(embeddings, 0.5)
        self.assertEqual(len(pairs), 2)  # (0, 2) 和 (1, 2)


class TestSummaryCosineSimilarityBuilder(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # 创建一个知识图谱实例
        self.nodes = [
            Node(
                properties={"summary_embedding": [1.0, 0.0, 0.0]},
                type=NodeType.DOCUMENT,
            ),
            Node(
                properties={"summary_embedding": [0.0, 1.0, 0.0]},
                type=NodeType.DOCUMENT,
            ),
            Node(
                properties={"summary_embedding": [0.0, 0.0, 1.0]},
                type=NodeType.DOCUMENT,
            ),
            Node(
                properties={"summary_embedding": [1.0, 1.0, 0.0]},
                type=NodeType.DOCUMENT,
            ),
            Node(
                properties={"summary_embedding": [1.0, 1.0, 1.0]}, type=NodeType.CHUNK
            ),
        ]
        self.kg = KnowledgeGraph(nodes=self.nodes)
        self.builder = SummaryCosineSimilarityBuilder(threshold=0.7)

    async def test_transform_valid(self):
        relationships = await self.builder.transform(self.kg)
        self.assertEqual(len(relationships), 3)  # (0, 3) / (1, 3) / (3, 4)

    async def test_transform_no_valid_embeddings(self):
        self.nodes[0].properties["summary_embedding"] = None  # 设置无效的嵌入
        self.nodes[1].properties["summary_embedding"] = None  # 设置无效的嵌入
        self.nodes[2].properties["summary_embedding"] = None  # 设置无效的嵌入
        self.nodes[3].properties["summary_embedding"] = None  # 设置无效的嵌入
        self.nodes[4].properties["summary_embedding"] = None  # 设置无效的嵌入
        with self.assertRaises(ValueError) as context:
            await self.builder.transform(self.kg)
        self.assertEqual(
            str(context.exception), "No nodes have a valid summary_embedding"
        )

    async def test_filter_valid(self):
        filtered_kg = self.builder.filter(self.kg)
        self.assertEqual(len(filtered_kg.nodes), 4)  # 过滤掉无效的节点

    async def test_filter_invalid_node_property(self):
        self.nodes[0].properties["summary_embedding"] = None  # 设置无效的嵌入
        with self.assertRaises(ValueError) as context:
            self.builder.filter(self.kg)
        self.assertIn("has no summary_embedding", str(context.exception))


if __name__ == "__main__":
    unittest.main()
