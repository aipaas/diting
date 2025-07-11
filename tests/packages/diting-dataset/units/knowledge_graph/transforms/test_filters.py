#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest
from unittest.mock import AsyncMock, patch

from diting_core.models.llms.base_model import BaseLLM
from diting_dataset.knowledge_graph.transforms.filters import (
    CustomNodeFilter,
    QuestionPotentialOutput,
)
from diting_dataset.knowledge_graph.graph import Node, KnowledgeGraph, NodeType


class TestCustomNodeFilter(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.node_filter = CustomNodeFilter(
            llm=AsyncMock(spec=BaseLLM),
            min_score=3,
        )
        self.node = Node(
            properties={
                "summary": "This is a test summary.",
                "page_content": "This is the content of the node.",
            },
            type=NodeType.CHUNK,
        )
        self.kg = KnowledgeGraph()

    @patch("diting_dataset.knowledge_graph.transforms.filters.get_parent_nodes")
    async def test_custom_filter_with_high_score(self, mock_get_parent_nodes):
        # Mock the parent nodes
        mock_get_parent_nodes.return_value = [
            Node(properties={"summary": "This is a test summary."})
        ]

        # Mock the response from the scoring prompt
        with patch.object(
            self.node_filter.scoring_prompt, "generate", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = QuestionPotentialOutput(score=4)

            result = await self.node_filter.custom_filter(self.node, self.kg)
            self.assertFalse(
                result
            )  # Should return False since score is greater than min_score

    @patch("diting_dataset.knowledge_graph.transforms.filters.get_parent_nodes")
    async def test_custom_filter_with_low_score(self, mock_get_parent_nodes):
        # Mock the parent nodes
        mock_get_parent_nodes.return_value = [
            Node(properties={"summary": "This is a test summary."})
        ]

        # Mock the response from the scoring prompt
        with patch.object(
            self.node_filter.scoring_prompt, "generate", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = QuestionPotentialOutput(score=2)

            result = await self.node_filter.custom_filter(self.node, self.kg)
            self.assertTrue(
                result
            )  # Should return True since score is less than or equal to min_score

    @patch("diting_dataset.knowledge_graph.transforms.filters.get_parent_nodes")
    async def test_custom_filter_with_no_summary(self, mock_get_parent_nodes):
        # Set node properties to simulate no summary
        self.node.properties["summary"] = ""
        mock_get_parent_nodes.return_value = []

        result = await self.node_filter.custom_filter(self.node, self.kg)
        self.assertFalse(result)  # Should return False since there is no summary

    @patch("diting_dataset.knowledge_graph.transforms.filters.get_parent_nodes")
    async def test_custom_filter_with_empty_node_content(self, mock_get_parent_nodes):
        # Mock the parent nodes
        mock_get_parent_nodes.return_value = [
            Node(properties={"summary": "This is a test summary."})
        ]

        # Set node content to empty
        self.node.properties["page_content"] = ""

        # Mock the response from the scoring prompt
        with patch.object(
            self.node_filter.scoring_prompt, "generate", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = QuestionPotentialOutput(score=1)

            result = await self.node_filter.custom_filter(self.node, self.kg)
            self.assertTrue(
                result
            )  # Should return True since score is less than or equal to min_score


if __name__ == "__main__":
    unittest.main()
