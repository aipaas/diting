#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from diting_dataset.knowledge_graph.graph import KnowledgeGraph, Node
from diting_dataset.knowledge_graph.transforms.relationship_builders.traditional import (
    JaccardSimilarityBuilder,
    OverlapScoreBuilder,
)


class TestJaccardSimilarityBuilder(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # 创建一个知识图谱实例
        self.nodes = [
            Node(properties={"entities": ["apple", "banana", "cherry"]}),
            Node(properties={"entities": ["banana", "cherry"]}),
            Node(properties={"entities": ["apple", "cherry", "banana"]}),
            Node(properties={"entities": ["fig", "grape"]}),
        ]
        self.kg = KnowledgeGraph(nodes=self.nodes)
        self.builder = JaccardSimilarityBuilder(threshold=0.5)

    async def test_transform_valid(self):
        relationships = await self.builder.transform(self.kg)
        self.assertEqual(len(relationships), 3)  # (0, 1), (0, 2), (1, 2)

    async def test_transform_invalid_node_property(self):
        self.nodes[0].properties["entities"] = None  # 设置无效的属性
        with self.assertRaises(ValueError) as context:
            await self.builder.transform(self.kg)
        self.assertIn("has no entities", str(context.exception))

    async def test_jaccard_similarity(self):
        similarity = self.builder._jaccard_similarity(
            {"apple", "banana"}, {"banana", "cherry"}
        )
        self.assertAlmostEqual(similarity, 0.3333, places=4)  # 1/3

    async def test_jaccard_similarity_empty(self):
        similarity = self.builder._jaccard_similarity(set(), set())
        self.assertEqual(similarity, 0.0)


class TestOverlapScoreBuilder(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # 创建一个知识图谱实例
        self.nodes = [
            Node(properties={"entities": ["apple", "banana"]}),
            Node(properties={"entities": ["banana", "cherry"]}),
            Node(properties={"entities": ["apple", "cherry"]}),
            Node(properties={"entities": ["fig", "grape"]}),
        ]
        self.kg = KnowledgeGraph(nodes=self.nodes)
        self.builder = OverlapScoreBuilder(threshold=0.5)

    async def test_transform_valid(self):
        relationships = await self.builder.transform(self.kg)
        self.assertEqual(len(relationships), 2)  # (0, 1), (0, 2)

    async def test_transform_invalid_node_property(self):
        self.nodes[0].properties["entities"] = None  # 设置无效的属性
        with self.assertRaises(ValueError) as context:
            await self.builder.transform(self.kg)
        self.assertIn("has no entities", str(context.exception))

    async def test_get_noisy_items(self):
        noisy_items = self.builder._get_noisy_items(self.kg.nodes, "entities", 0.5)
        self.assertIn("banana", noisy_items)  # 验证是否包含噪声项

    async def test_overlap_score(self):
        score = self.builder._overlap_score([True, False, True])
        self.assertEqual(score, 2 / 3)  # 2/3

    async def test_overlap_score_empty(self):
        score = self.builder._overlap_score([])
        self.assertEqual(score, 0.0)


if __name__ == "__main__":
    unittest.main()
