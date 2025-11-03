import os
import tempfile
import unittest
import uuid

from diting_dataset.knowledge_graph import get_child_nodes, get_parent_nodes
from diting_dataset.knowledge_graph.schema import (
    KnowledgeGraph,
    Node,
    Relationship,
    NodeType,
)


class TestKnowledgeGraph(unittest.TestCase):
    def setUp(self):
        self.kg = KnowledgeGraph()
        self.node1 = Node(
            id=uuid.UUID("12345678123456781234567812345678"),
            type=NodeType.CHUNK,
            properties={"name": "Node1"},
        )
        self.node2 = Node(type=NodeType.CHUNK, properties={"name": "Node2"})
        self.relationship = Relationship(
            source=self.node1, target=self.node2, type="next", properties={}
        )

    def test_node_str(self):
        self.assertEqual(
            str(self.node1),
            "Node(id: 123456, type: NodeType.CHUNK, properties: ['name'])",
        )

    def test_knowledge_graph_str(self):
        self.assertEqual(
            str(self.kg),
            "KnowledgeGraph(nodes: 0, relationships: 0)",
        )

    def test_add_node_property(self):
        with self.assertRaises(ValueError):
            self.node1.add_property("name", "Node2")

        self.node1.add_property("TESTKEY", "testvalue")
        self.assertEqual("testvalue", self.node1.get_property("testkey"))

    def test_add_node(self):
        self.kg.add(self.node1)
        self.assertIn(self.node1, self.kg.nodes)

    def test_add_relationship(self):
        self.kg.add(self.node1)
        self.kg.add(self.node2)
        self.kg.add(self.relationship)
        self.assertIn(self.relationship, self.kg.relationships)

    def test_add_invalid_item(self):
        with self.assertRaises(ValueError):
            self.kg.add("InvalidItem")

    def test_remove_node_inplace(self):
        self.kg.add(self.node1)
        self.kg.add(self.node2)
        self.kg.add(self.relationship)
        self.kg.remove_node(self.node1, inplace=True)
        self.assertNotIn(self.node1, self.kg.nodes)
        self.assertEqual(len(self.kg.relationships), 0)

    def test_remove_node_not_present(self):
        with self.assertRaises(ValueError):
            self.kg.remove_node(self.node1)

    def test_remove_node_return_copy(self):
        self.kg.add(self.node1)
        self.kg.add(self.node2)
        self.kg.add(self.relationship)
        self.kg.remove_node(self.node1, inplace=False)
        self.assertIn(self.node1, self.kg.nodes)

    def test_save_and_load(self):
        self.kg.add(self.node1)
        self.kg.add(self.node2)
        self.kg.add(self.relationship)

        # Create a temporary file to save the knowledge graph
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp_file:
            save_path = tmp_file.name

        try:
            self.kg.save(save_path)
            loaded_kg = KnowledgeGraph.load(save_path)

            self.assertEqual(len(loaded_kg.nodes), len(self.kg.nodes))
            self.assertEqual(len(loaded_kg.relationships), len(self.kg.relationships))
        finally:
            if os.path.exists(save_path):
                os.remove(save_path)

    def test_find_indirect_clusters(self):
        kg = KnowledgeGraph()
        node1 = Node(type=NodeType.CHUNK, properties={"name": "Node1"})
        node2 = Node(type=NodeType.CHUNK, properties={"name": "Node2"})
        relationship12 = Relationship(
            source=node1, target=node2, type="next", properties={}
        )
        kg.add(node1)
        kg.add(node2)
        kg.add(relationship12)
        clusters = kg.find_indirect_clusters()
        self.assertEqual(len(clusters), 1)

        node3 = Node(type=NodeType.CHUNK, properties={"name": "Node3"})
        node4 = Node(type=NodeType.CHUNK, properties={"name": "Node4"})
        relationship23 = Relationship(
            source=node2, target=node3, type="next", properties={}
        )
        relationship24 = Relationship(
            source=node2, target=node4, type="next", properties={}
        )
        kg.add(node3)
        kg.add(node4)
        kg.add(relationship23)
        kg.add(relationship24)
        clusters = kg.find_indirect_clusters()
        self.assertEqual(len(clusters), 5)  # 1->2->3, 1->2->4, 1->2, 2->3, 2->4

    def test_find_two_nodes_single_rel(self):
        self.kg.add(self.node1)
        self.kg.add(self.node2)
        self.kg.add(self.relationship)

        triplets = self.kg.find_two_nodes_single_rel()
        self.assertEqual(len(triplets), 1)

        self.kg = KnowledgeGraph()
        self.kg.add(self.node1)
        self.kg.add(self.node2)
        self.kg.add(
            Relationship(
                source=self.node2, target=self.node1, type="next", properties={}
            )
        )
        triplets = self.kg.find_two_nodes_single_rel()
        self.assertEqual(len(triplets), 1)


class TestRelationship(unittest.TestCase):
    def setUp(self):
        # 创建源节点和目标节点的模拟对象
        self.source_node = Node(id=uuid.uuid4(), properties={"name": "Source"})
        self.target_node = Node(id=uuid.uuid4(), properties={"name": "Target"})
        self.relationship = Relationship(
            source=self.source_node,
            target=self.target_node,
            type="friend",
            properties={"strength": "strong"},
            bidirectional=True,
        )

    def test_initialization(self):
        self.assertIsInstance(self.relationship.id, uuid.UUID)
        self.assertEqual(self.relationship.type, "friend")
        self.assertEqual(self.relationship.source, self.source_node)
        self.assertEqual(self.relationship.target, self.target_node)
        self.assertTrue(self.relationship.bidirectional)
        self.assertEqual(self.relationship.properties, {"strength": "strong"})

    def test_get_property_existing_key(self):
        self.assertEqual(self.relationship.get_property("strength"), "strong")

    def test_get_property_non_existing_key(self):
        self.assertIsNone(self.relationship.get_property("non_existing_key"))

    def test_get_property_case_insensitive(self):
        self.assertEqual(self.relationship.get_property("STRENGTH"), "strong")

    def test_repr(self):
        expected_repr = f"Relationship(Node(id: {str(self.source_node.id)[:6]}) <-> Node(id: {str(self.target_node.id)[:6]}), type: friend, properties: ['strength'])"
        self.assertEqual(repr(self.relationship), expected_repr)

    def test_str(self):
        self.assertEqual(str(self.relationship), repr(self.relationship))

    def test_hash(self):
        relationship_id = self.relationship.id
        self.assertEqual(hash(self.relationship), hash(relationship_id))

    def test_eq_same_object(self):
        self.assertTrue(self.relationship == self.relationship)

    def test_eq_different_object_same_id(self):
        another_relationship = Relationship(
            id=self.relationship.id,
            source=self.source_node,
            target=self.target_node,
            type="friend",
            properties={"strength": "strong"},
            bidirectional=True,
        )
        self.assertTrue(self.relationship == another_relationship)

    def test_eq_different_object_different_id(self):
        another_relationship = Relationship(
            source=self.source_node,
            target=self.target_node,
            type="friend",
            properties={"strength": "weak"},
            bidirectional=False,
        )
        self.assertFalse(self.relationship == another_relationship)


class TestGraphQueries(unittest.TestCase):
    def setUp(self):
        # 创建一个知识图谱实例
        self.graph = KnowledgeGraph()

        # 创建节点
        self.node_a = Node(properties={"name": "A"})
        self.node_b = Node(properties={"name": "B"})
        self.node_c = Node(properties={"name": "C"})
        self.node_d = Node(properties={"name": "D"})

        # 添加节点到图谱
        self.graph.add(self.node_a)
        self.graph.add(self.node_b)
        self.graph.add(self.node_c)
        self.graph.add(self.node_d)

        # 创建关系
        self.rel_ab = Relationship(source=self.node_a, target=self.node_b, type="child")
        self.rel_ac = Relationship(source=self.node_a, target=self.node_c, type="child")
        self.rel_bd = Relationship(source=self.node_b, target=self.node_d, type="child")

        # 添加关系到图谱
        self.graph.add(self.rel_ab)
        self.graph.add(self.rel_ac)
        self.graph.add(self.rel_bd)

    def test_get_child_nodes_level_1(self):
        children = get_child_nodes(self.node_a, self.graph, level=1)
        self.assertEqual(len(children), 2)
        self.assertIn(self.node_b, children)
        self.assertIn(self.node_c, children)

    def test_get_child_nodes_level_2(self):
        children = get_child_nodes(self.node_a, self.graph, level=2)
        self.assertEqual(len(children), 3)
        self.assertIn(self.node_b, children)
        self.assertIn(self.node_c, children)
        self.assertIn(self.node_d, children)

    def test_get_child_nodes_no_children(self):
        children = get_child_nodes(self.node_d, self.graph, level=1)
        self.assertEqual(len(children), 0)

    def test_get_parent_nodes_level_1(self):
        parents = get_parent_nodes(self.node_b, self.graph, level=1)
        self.assertEqual(len(parents), 1)
        self.assertIn(self.node_a, parents)

    def test_get_parent_nodes_level_2(self):
        parents = get_parent_nodes(self.node_d, self.graph, level=2)
        self.assertEqual(len(parents), 2)
        self.assertIn(self.node_b, parents)
        self.assertIn(self.node_a, parents)

    def test_get_parent_nodes_no_parents(self):
        parents = get_parent_nodes(self.node_a, self.graph, level=1)
        self.assertEqual(len(parents), 0)


if __name__ == "__main__":
    unittest.main()
