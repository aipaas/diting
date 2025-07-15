import typing as t
import unittest
from unittest.mock import AsyncMock

from diting_core.models.llms.base_model import BaseLLM
from diting_dataset.knowledge_graph.schema import KnowledgeGraph, Node, Relationship
from diting_dataset.knowledge_graph.transforms.base import (
    Extractor,
    Splitter,
    LLMBasedExtractor,
    LLMBasedNodeFilter,
    RelationshipBuilder,
)
from diting_dataset.knowledge_graph.transforms.engine import run_coroutines


# 创建具体的子类以实现抽象方法
class TestExtractor(Extractor):
    async def extract(self, node: Node):
        return "property_name", "extracted_value"


class TestSplitter(Splitter):
    async def split(self, node: Node):
        return [Node(properties={"name": "Node3"})], []


class TestLLMBasedExtractor(LLMBasedExtractor):
    async def extract(self, node: Node):
        return "property_name", "extracted_value"


class TestLLMBasedNodeFilter(LLMBasedNodeFilter):
    async def custom_filter(self, node: Node, kg: KnowledgeGraph):
        return False


class TestRelationshipBuilder(RelationshipBuilder):
    async def transform(self, kg: KnowledgeGraph) -> t.List[Relationship]:
        return [
            Relationship(
                type="test",
                source=Node(properties={"name": "testNode1"}),
                target=Node(properties={"name": "testNode2"}),
            )
        ]


class TestBaseGraphTransformation(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.kg = KnowledgeGraph()
        self.node1 = Node(properties={"name": "Node1"})
        self.node2 = Node(properties={"name": "Node2"})
        self.kg.add(self.node1)
        self.kg.add(self.node2)

        self.llm = AsyncMock(spec=BaseLLM)

    async def test_filter_transform(self):
        transformer = TestLLMBasedNodeFilter(llm=self.llm)
        filtered_kg = transformer.filter(self.kg)
        self.assertEqual(len(filtered_kg.nodes), 2)

    async def test_filter_exe_plan(self):
        transformer = TestLLMBasedNodeFilter(llm=self.llm)
        plan = transformer.generate_execution_plan(self.kg)
        self.assertEqual(len(plan), 2)

    async def test_extractor_transform(self):
        extractor = TestExtractor()
        result = await extractor.transform(self.kg)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], (self.node1, ("property_name", "extracted_value")))

    async def test_extractor_exe_plan(self):
        extractor = TestExtractor()
        plan = extractor.generate_execution_plan(self.kg)
        await run_coroutines(
            plan,
            max_workers=2,
        )
        self.assertEqual(
            self.kg.nodes[0].properties,
            {"name": "Node1", "property_name": "extracted_value"},
        )

    async def test_splitter_transform(self):
        splitter = TestSplitter()
        result_nodes, result_relationships = await splitter.transform(self.kg)
        self.assertEqual(len(result_nodes), 2)
        self.assertEqual(result_nodes[0].properties.get("name"), "Node3")

    async def test_splitter_exe_plan(self):
        splitter = TestSplitter()
        plan = splitter.generate_execution_plan(self.kg)
        await run_coroutines(
            plan,
            max_workers=2,
        )
        self.assertEqual(self.kg.nodes[2].properties.get("name"), "Node3")

    async def test_relationship_builder_exe_plan(self):
        builder = TestRelationshipBuilder()
        plan = builder.generate_execution_plan(self.kg)
        await run_coroutines(
            plan,
            max_workers=2,
        )
        self.assertEqual(self.kg.relationships[0].type, "test")

    async def test_llm_based_extractor_split_text_by_token_limit(self):
        llm_extractor = TestLLMBasedExtractor(llm=self.llm)
        text = (
            "This is a test text that exceeds the token limit." * 1000
        )  # Create a long text
        chunks = llm_extractor.split_text_by_token_limit(text, max_token_limit=10)
        self.assertGreater(len(chunks), 1)  # Ensure it splits into multiple chunks

    async def test_llm_based_node_filter_transform(self):
        node_filter = TestLLMBasedNodeFilter(llm=self.llm)
        result_kg = await node_filter.transform(self.kg)
        self.assertEqual(len(result_kg.nodes), 2)  # Assuming no nodes are filtered out

    async def test_llm_based_node_filter_exe_plan(self):
        node_filter = TestLLMBasedNodeFilter(llm=self.llm)
        plan = node_filter.generate_execution_plan(self.kg)
        await run_coroutines(
            plan,
            max_workers=2,
        )
        self.assertEqual(len(self.kg.nodes), 2)  # Assuming no nodes are filtered out


if __name__ == "__main__":
    unittest.main()
