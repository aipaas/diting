#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest
from unittest.mock import AsyncMock, patch

from diting_core.models.llms.base_model import BaseLLM
from diting_dataset.knowledge_graph.schema import KnowledgeGraph, Node, NodeType
from diting_dataset.corpus.persona import (
    generate_personas_from_kg,
    PersonaGenerationPrompt,
    default_filter,
    PersonaList,
)
from diting_dataset.corpus import Persona


class TestPersonaGeneration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.kg = KnowledgeGraph()
        self.llm = AsyncMock(spec=BaseLLM)  # Mock the LLM
        self.persona_generation_prompt = PersonaGenerationPrompt()

        # Create sample nodes for the knowledge graph
        self.node1 = Node(
            properties={
                "summary": "This is a summary about digital marketing.",
                "summary_embedding": [0.1, 0.2, 0.3],
            },
            type=NodeType.DOCUMENT,
        )
        self.node2 = Node(
            properties={
                "summary": "This is another summary about online advertising.",
                "summary_embedding": [0.1, 0.2, 0.4],
            },
            type=NodeType.DOCUMENT,
        )
        self.node3 = Node(
            properties={
                "summary": "This summary is about social media strategies.",
                "summary_embedding": [0.1, 0.2, 0.5],
            },
            type=NodeType.DOCUMENT,
        )
        self.kg.add(self.node1)
        self.kg.add(self.node2)
        self.kg.add(self.node3)

    def test_default_filter(self):
        self.assertTrue(default_filter(self.node1))
        self.assertTrue(default_filter(self.node2))
        self.assertTrue(default_filter(self.node3))
        self.node4 = Node(
            properties={
                "summary": "This summary is about rag optimization strategies.",
            },
            type=NodeType.DOCUMENT,
        )
        self.assertFalse(default_filter(self.node4))

    async def test_generate_personas_from_kg(self):
        with patch.object(
            self.llm,
            "generate_structured_output",
            return_value=Persona(
                name="AI Developer", role_description="build the AI Platform"
            ),
        ):
            personas = await generate_personas_from_kg(
                kg=self.kg,
                llm=self.llm,
                persona_generation_prompt=self.persona_generation_prompt,
                num_personas=2,
            )

        self.assertEqual(len(personas), 2)
        self.assertIsInstance(personas[0], Persona)
        self.assertIsInstance(personas[1], Persona)

    async def test_generate_personas_from_kg_no_nodes(self):
        empty_kg = KnowledgeGraph()
        with self.assertRaises(ValueError):
            await generate_personas_from_kg(
                kg=empty_kg,
                llm=self.llm,
                persona_generation_prompt=self.persona_generation_prompt,
                num_personas=2,
            )

    async def test_generate_personas_with_filter(self):
        # Create a filter that only allows node1
        with patch.object(
            self.llm,
            "generate_structured_output",
            return_value=Persona(
                name="AI Developer", role_description="build the AI Platform"
            ),
        ):
            personas = await generate_personas_from_kg(
                kg=self.kg,
                llm=self.llm,
                persona_generation_prompt=self.persona_generation_prompt,
                num_personas=2,
                filter_fn=lambda node: node == self.node1,
            )

        self.assertEqual(len(personas), 1)  # Only node1 should be processed

    def test_persona_list_getitem(self):
        persona_list = [Persona(name="John Doe", role_description="Marketing Expert")]
        persona_container = PersonaList(personas=persona_list)

        self.assertEqual(persona_container["John Doe"].name, "John Doe")
        with self.assertRaises(KeyError):
            _ = persona_container["Jane Doe"]


if __name__ == "__main__":
    unittest.main()
