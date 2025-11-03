#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest
from unittest.mock import MagicMock, patch
from diting_dataset.knowledge_graph.transforms.default import (
    num_tokens_from_string,
    default_transforms,
    filter_doc_with_num_tokens,
    count_doc_length_bins,
    filter_docs,
    filter_chunks,
)
from langchain_core.documents import Document as LCDocument
from diting_core.models.llms.base_model import BaseLLM
from diting_core.models.embeddings.base_model import BaseEmbeddings
from diting_dataset.knowledge_graph.schema import Node, NodeType


class TestDefaultTransforms(unittest.TestCase):
    def setUp(self):
        self.llm = MagicMock(spec=BaseLLM)
        self.embedding_model = MagicMock(spec=BaseEmbeddings)
        self.documents = [
            LCDocument(page_content="This is a test document with some content."),
            LCDocument(page_content="Another document with more content."),
            LCDocument(page_content="Short."),
            LCDocument(
                page_content="A very long document that exceeds the token limit set for testing purposes."
                * 10
            ),
        ]

    def test_num_tokens_from_string(self):
        # Test the token counting function
        string = "Hello, world!"
        encoding_name = "cl100k_base"
        expected_tokens = 4  # Assuming the encoding gives 4 tokens for this string
        with patch("tiktoken.get_encoding") as mock_get_encoding:
            mock_encoding = MagicMock()
            mock_encoding.encode.return_value = ["Hello", ",", "world", "!"]
            mock_get_encoding.return_value = mock_encoding

            result = num_tokens_from_string(string, encoding_name)
            self.assertEqual(result, expected_tokens)

    def test_num_tokens_from_zh_string(self):
        # Test the token counting function
        string = "你好，世界!"
        encoding_name = "cl100k_base"
        expected_tokens = 7
        result = num_tokens_from_string(string, encoding_name)
        self.assertEqual(result, expected_tokens)

    def test_default_transforms_with_long_documents(self):
        # Test the default_transforms function with long documents
        documents = [
            LCDocument(page_content="This is a test document with some content."),
            LCDocument(page_content="Another document with more content."),
            LCDocument(page_content="Short."),
            LCDocument(
                page_content="A very long document that exceeds the token limit set for testing purposes."
                * 1000
            ),
        ]
        transforms = default_transforms(documents, self.llm, self.embedding_model)
        self.assertGreater(len(transforms), 0)

    def test_default_transforms_with_middle_documents(self):
        # Test the default_transforms function with long documents
        transforms = default_transforms(self.documents, self.llm, self.embedding_model)
        self.assertGreater(len(transforms), 0)

    def test_default_transforms_with_short_documents(self):
        # Test the default_transforms function with short documents
        short_documents = [LCDocument(page_content="Short.")]
        with self.assertRaises(ValueError) as context:
            default_transforms(short_documents, self.llm, self.embedding_model)
        self.assertEqual(
            str(context.exception),
            "Documents appears to be too short (ie 100 tokens or less). Please provide longer documents.",
        )

    def test_count_doc_length_bins(self):
        # Test the internal function count_doc_length_bins
        bin_ranges = [(0, 100), (101, 500), (501, 100000)]
        result = count_doc_length_bins(self.documents, bin_ranges)
        self.assertIn("0-100", result)
        self.assertIn("101-500", result)
        self.assertIn("501-100000", result)

    def test_filter_doc_with_num_tokens(self):
        # Test the filter function for documents
        node = Node(
            type=NodeType.DOCUMENT,
            properties={"page_content": "This is a test document."},
        )
        self.assertTrue(filter_doc_with_num_tokens(node, min_num_tokens=5))
        self.assertFalse(filter_doc_with_num_tokens(node, min_num_tokens=50))

    def test_filter_docs(self):
        # Test the filter function for documents
        node = Node(type=NodeType.DOCUMENT)
        self.assertTrue(filter_docs(node))
        node.type = NodeType.CHUNK
        self.assertFalse(filter_docs(node))

    def test_filter_chunks(self):
        # Test the filter function for chunks
        node = Node(type=NodeType.CHUNK)
        self.assertTrue(filter_chunks(node))
        node.type = NodeType.DOCUMENT
        self.assertFalse(filter_chunks(node))


if __name__ == "__main__":
    unittest.main()
