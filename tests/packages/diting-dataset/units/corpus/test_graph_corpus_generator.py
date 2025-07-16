#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# !/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from diting_core.synthesis.base_corpus import (
    BaseCorpus,
)
from diting_dataset.corpus import QueryLength, QueryStyle, Persona
from diting_dataset.corpus.graph_corpus_generator import (
    KnowledgeGraphCorpusGenerator,
)
from diting_dataset.corpus.template import PersonaThemesMapping
from diting_dataset.knowledge_graph.schema import (
    KnowledgeGraph,
    Node,
    NodeType,
    Relationship,
)


class TestDefaultCorpusGenerator(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        node1 = Node(type=NodeType.CHUNK, properties={"entities": ["Entity1"]})
        node2 = Node(type=NodeType.CHUNK, properties={"entities": ["Entity2"]})
        node3 = Node(type=NodeType.CHUNK, properties={"entities": ["Entity3"]})
        node4 = Node(type=NodeType.CHUNK, properties={"entities": ["Entity4"]})
        relationship12 = Relationship(
            source=node1, target=node2, type="next", properties={}
        )
        relationship23 = Relationship(
            source=node2, target=node3, type="next", properties={}
        )
        relationship24 = Relationship(
            source=node2, target=node4, type="next", properties={}
        )
        self.knowledge_graph = KnowledgeGraph(
            nodes=[node1, node2, node3, node4],
            relationships=[relationship12, relationship23, relationship24],
        )
        self.llm = MagicMock()
        self.generator = KnowledgeGraphCorpusGenerator(
            knowledge_graph=self.knowledge_graph, llm=self.llm
        )

    def test_post_init_no_clusters(self):
        """测试初始化时没有节点时抛出异常"""
        self.knowledge_graph.nodes = []
        with self.assertRaises(ValueError):
            KnowledgeGraphCorpusGenerator(
                knowledge_graph=self.knowledge_graph, llm=self.llm
            )

    def test_get_node_clusters(self):
        """测试获取节点集群的功能"""
        node1 = Node(type=NodeType.CHUNK, properties={"entities": ["entity1"]})

        node2 = Node(type=NodeType.DOCUMENT, properties={"entities": ["entity2"]})

        self.knowledge_graph.nodes = [node1, node2]
        clusters = self.generator._get_node_clusters()
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0], node2)

    @patch(
        "diting_dataset.corpus.graph_corpus_generator.generate_personas_from_kg",
        new_callable=AsyncMock,
    )
    async def test_generate_corpora(self, mock_gen_persona):
        """测试生成语料的功能"""
        mock_gen_persona.return_value = [
            Persona(name="persona1", role_description="test role")
        ]
        node = Node()
        node.properties = {"entities": ["concept1"]}
        self.generator.nodes = [node]

        self.generator.theme_persona_matching_prompt.generate = AsyncMock(
            return_value=PersonaThemesMapping(mapping={"persona1": ["concept1"]})
        )

        corpora = await self.generator._generate_corpora(num_corpora=5)
        self.assertIsInstance(corpora, list)
        self.assertGreater(len(corpora), 0)

    async def test_prepare_combinations(self):
        """测试准备组合的功能"""
        node = Node()
        node.properties = {"entities": ["entity1"]}
        personas = [Persona(name="persona1", role_description="test role")]
        persona_concepts = {"persona1": ["concept1"]}

        combinations = self.generator.prepare_combinations(
            node, ["concept1", "concept2"], personas, persona_concepts
        )
        self.assertEqual(len(combinations), 1)
        self.assertIn("personas", combinations[0])
        self.assertEqual(len(combinations[0]["personas"]), 1)

    def test_sample_combinations(self):
        """测试样本组合的功能"""
        data = [
            {
                "node": Node(),
                "terms": ["term1"],
                "personas": [Persona(name="persona1", role_description="test role")],
                "styles": list(QueryStyle),
                "lengths": list(QueryLength),
            }
        ]
        samples = self.generator.sample_combinations(data, num_samples=1)
        self.assertEqual(len(samples), 1)

    def test_convert_to_corpus(self):
        """测试转换为语料的功能"""
        node = Node()
        node.properties = {"page_content": "some content"}
        sample = {
            "term": "term1",
            "node": node,
            "persona": Persona(name="persona1", role_description="test role"),
            "style": QueryStyle.MISSPELLED,
            "length": QueryLength.MEDIUM,
        }
        corpus = self.generator.convert_to_corpus(sample)
        self.assertIsInstance(corpus, BaseCorpus)
        self.assertEqual(corpus.scenario, "term1")
        self.assertEqual(corpus.context, ["some content"])


if __name__ == "__main__":
    unittest.main()
