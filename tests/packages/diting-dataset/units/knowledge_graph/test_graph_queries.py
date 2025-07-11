import unittest
from diting_dataset.knowledge_graph.graph import KnowledgeGraph, Node, Relationship
from diting_dataset.knowledge_graph.graph_queries import (
    get_child_nodes,
    get_parent_nodes,
)


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
