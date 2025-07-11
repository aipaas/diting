#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from diting_dataset.knowledge_graph.graph import Node
from diting_dataset.knowledge_graph.transforms.splitters.headline import (
    HeadlineSplitter,
)


class TestHeadlineSplitter(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.splitter = HeadlineSplitter(min_tokens=3, max_tokens=5)

    def test_adjust_chunks_over_max_tokens(self):
        chunks = ["This is a test chunk with more than five tokens."]
        adjusted = self.splitter.adjust_chunks(chunks)
        self.assertEqual(len(adjusted), 2)
        self.assertEqual(adjusted[0], "This is a test chunk")
        self.assertEqual(adjusted[1], "with more than five tokens.")

    def test_adjust_chunks_under_min_tokens(self):
        chunks = ["This is a test."]
        adjusted = self.splitter.adjust_chunks(chunks)
        self.assertEqual(len(adjusted), 1)
        self.assertEqual(adjusted[0], "This is a test.")

    def test_adjust_chunks_combined(self):
        chunks = [
            "This is a test chunk with more than five tokens.",
            "Another short chunk.",
        ]
        adjusted = self.splitter.adjust_chunks(chunks)
        self.assertEqual(len(adjusted), 3)
        self.assertEqual("This is a test chunk", adjusted[0])
        self.assertEqual("with more than five tokens.", adjusted[1])
        self.assertEqual("Another short chunk.", adjusted[2])

    async def test_split_valid(self):
        node = Node(
            properties={
                "page_content": "This is a test. Headline 1. Headline 2.",
                "headlines": ["Headline 1", "Headline 2"],
            }
        )
        nodes, relationships = await self.splitter.split(node)
        self.assertEqual(len(nodes), 2)  # 应该生成 2 个节点
        self.assertEqual(len(relationships), 3)  # 应该生成 3 个关系

    async def test_split_no_headlines(self):
        node = Node(properties={"page_content": "This is a test.", "headlines": []})
        nodes, relationships = await self.splitter.split(node)
        self.assertEqual(len(nodes), 1)  # 应该返回原始节点
        self.assertEqual(len(relationships), 0)  # 应该没有关系

    async def test_split_insufficient_tokens(self):
        node = Node(properties={"page_content": "Short.", "headlines": ["Headline"]})
        nodes, relationships = await self.splitter.split(node)
        self.assertEqual(len(nodes), 1)  # 应该返回原始节点
        self.assertEqual(len(relationships), 0)  # 应该没有关系

    async def test_split_missing_page_content(self):
        node = Node(properties={"headlines": ["Headline"]})
        with self.assertRaises(ValueError) as context:
            await self.splitter.split(node)
        self.assertIn(
            "'page_content' property not found in this node", str(context.exception)
        )

    async def test_split_missing_headlines(self):
        node = Node(properties={"page_content": "This is a test."})
        with self.assertRaises(ValueError) as context:
            await self.splitter.split(node)
        self.assertIn(
            "'headlines' property not found in this node", str(context.exception)
        )


if __name__ == "__main__":
    unittest.main()
