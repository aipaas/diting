#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest
from diting_dataset.knowledge_graph.graph import Node
from diting_dataset.knowledge_graph.transforms.extractors.regex_based import (
    links_extractor,
    emails_extractor,
    markdown_headings_extractor,
)


class TestRegexBasedExtractor(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # 创建 RegexBasedExtractor 实例
        self.url_extractor = links_extractor
        self.email_extractor = emails_extractor
        self.heading_extractor = markdown_headings_extractor

    async def test_extract_urls(self):
        # 创建一个包含 URL 的 Node
        node = Node(
            properties={
                "page_content": "Visit us at https://example.com or www.example.org."
            }
        )

        # 调用 extract 方法
        property_name, matches = await self.url_extractor.extract(node)

        # 验证返回值
        self.assertEqual(property_name, "links")
        self.assertEqual(matches, ["https://example.com", "www.example.org"])

    async def test_extract_emails(self):
        # 创建一个包含 Email 的 Node
        node = Node(properties={"page_content": "Contact us at info@example.com."})

        # 调用 extract 方法
        property_name, matches = await self.email_extractor.extract(node)

        # 验证返回值
        self.assertEqual(property_name, "emails")
        self.assertEqual(matches, ["info@example.com."])

    async def test_extract_headings(self):
        # 创建一个包含 Markdown headings 的 Node
        node = Node(properties={"page_content": "# Heading 1\n## Heading 2"})

        # 调用 extract 方法
        property_name, matches = await self.heading_extractor.extract(node)

        # 验证返回值
        self.assertEqual(property_name, "headings")
        self.assertEqual(matches, [("#", "Heading 1"), ("##", "Heading 2")])

    async def test_extract_invalid_node_property(self):
        # 创建一个包含非字符串属性的 Node
        node = Node(properties={"page_content": 12345})

        # 验证提取时抛出 ValueError
        with self.assertRaises(ValueError) as context:
            await self.url_extractor.extract(node)

        self.assertEqual(
            str(context.exception),
            "node.property('page_content') must be a string, found '<class 'int'>'",
        )

    async def test_extract_empty_content(self):
        # 创建一个内容为空的 Node
        node = Node(properties={"page_content": ""})

        # 调用 extract 方法
        property_name, matches = await self.url_extractor.extract(node)

        # 验证返回值
        self.assertEqual(property_name, "links")
        self.assertEqual(matches, [])


if __name__ == "__main__":
    unittest.main()
