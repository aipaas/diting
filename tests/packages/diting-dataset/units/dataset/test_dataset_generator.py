#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.documents import Document as LCDocument

from diting_core.cases.llm_case import LLMCase
from diting_core.models.embeddings.base_model import BaseEmbeddings
from diting_core.models.llms.base_model import BaseLLM
from diting_dataset.corpus.base_corpus import BaseCorpus
from diting_dataset.dataset.dataset import EvaluationDataset
from diting_dataset.dataset.dataset_generator import DataSetGenerator
from diting_dataset.knowledge_graph.transforms import BaseGraphTransformation
from diting_dataset.synthesis.base_synthesizer import BaseSynthesizer


class MockSynthesizer(BaseSynthesizer):
    async def _apply(self, corpus: BaseCorpus, **kwargs: Any) -> LLMCase:
        raise ValueError("test")


class TestDataSetGenerator(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_llm = AsyncMock(spec=BaseLLM)
        cls.mock_embedding_model = AsyncMock(spec=BaseEmbeddings)
        cls.dataset_generator = DataSetGenerator(
            llm=cls.mock_llm, embedding_model=cls.mock_embedding_model
        )

    async def test_generate_dataset_from_langchain_docs_success(self):
        mock_documents = [
            LCDocument(page_content="Content 1", metadata={"key": "value1"}),
            LCDocument(page_content="Content 2", metadata={"key": "value2"}),
        ]
        mock_synthesizers = [MagicMock(spec=BaseSynthesizer)]

        mock_transform = MagicMock(spec=BaseGraphTransformation)
        mock_default_transforms = MagicMock(return_value=[mock_transform])
        mock_corpus = MagicMock(spec=BaseCorpus)
        mock_corpus_generator = AsyncMock(return_value=[mock_corpus])

        with patch(
            "diting_dataset.dataset.dataset_generator.default_transforms",
            mock_default_transforms,
        ):
            with patch(
                "diting_dataset.dataset.dataset_generator.DefaultCorpusGenerator.generate_corpora",
                mock_corpus_generator,
            ):
                result = (
                    await self.dataset_generator.generate_dataset_from_langchain_docs(
                        documents=mock_documents, synthesizers=mock_synthesizers
                    )
                )
                self.assertIsInstance(result, EvaluationDataset)

    async def test_generate_dataset_from_docs_success(self):
        mock_document_paths = [str(Path("doc1")), str(Path("doc2"))]
        mock_synthesizers = [MagicMock(spec=BaseSynthesizer)]

        with patch(
            "langchain_community.document_loaders.DirectoryLoader.aload",
            new_callable=AsyncMock,
        ) as mock_load_wrapper:
            with patch(
                "diting_dataset.dataset.dataset_generator.default_transforms",
                new_callable=MagicMock,
            ) as mock_default_transforms:
                with patch(
                    "diting_dataset.dataset.dataset_generator.DefaultCorpusGenerator.generate_corpora",
                    new_callable=AsyncMock,
                ) as mock_corpus_generator:
                    mock_documents = [
                        LCDocument(
                            page_content="This is a sufficiently long content for testing.",
                            metadata={"key": "value1"},
                        ),
                        LCDocument(
                            page_content="This is another sufficiently long content for testing.",
                            metadata={"key": "value2"},
                        ),
                    ]
                    mock_load_wrapper.return_value = mock_documents
                    mock_default_transforms.return_value = MagicMock(
                        spec=BaseGraphTransformation
                    )
                    mock_corpus_generator.return_value = [MagicMock(spec=BaseCorpus)]
                    result = await self.dataset_generator.generate_dataset_from_docs(
                        document_paths=mock_document_paths,
                        synthesizers=mock_synthesizers,
                    )
                    self.assertIsInstance(result, EvaluationDataset)

    async def test_generate_dataset_from_corpora_success(self):
        mock_corpora = [
            MagicMock(spec=BaseCorpus),
            MagicMock(spec=BaseCorpus),
        ]
        mock_synthesizers = [
            MagicMock(spec=BaseSynthesizer),
            MagicMock(spec=BaseSynthesizer),
        ]

        result = await self.dataset_generator.generate_dataset_from_corpora(
            corpora=mock_corpora, synthesizers=mock_synthesizers
        )
        self.assertIsInstance(result, EvaluationDataset)

    async def test_generate_dataset_from_langchain_docs_no_documents(self):
        with self.assertRaises(ValueError):
            await self.dataset_generator.generate_dataset_from_langchain_docs(
                documents=[], synthesizers=[]
            )

    async def test_generate_dataset_from_langchain_docs_run_except(self):
        mock_documents = [
            LCDocument(page_content="Content 1", metadata={"key": "value1"}),
            LCDocument(page_content="Content 2", metadata={"key": "value2"}),
        ]
        mock_synthesizers = [MagicMock(spec=BaseSynthesizer)]

        mock_default_transforms = MagicMock(side_effect=ValueError("test"))

        with patch(
            "diting_dataset.dataset.dataset_generator.default_transforms",
            mock_default_transforms,
        ):
            with self.assertRaises(ValueError):
                await self.dataset_generator.generate_dataset_from_langchain_docs(
                    documents=mock_documents,
                    synthesizers=mock_synthesizers,
                    verbose=True,
                )

    async def test_generate_dataset_from_docs_no_document_paths(self):
        with self.assertRaises(ValueError):
            await self.dataset_generator.generate_dataset_from_docs(
                document_paths=[], synthesizers=[]
            )

    async def test_generate_dataset_from_docs_run_except(self):
        mock_document_paths = [str(Path("doc1")), str(Path("doc2"))]
        mock_synthesizers = [MagicMock(spec=BaseSynthesizer)]

        with patch(
            "langchain_community.document_loaders.DirectoryLoader.aload",
            new_callable=AsyncMock,
        ) as mock_load_wrapper:
            mock_load_wrapper.side_effect = ValueError("test")
            with self.assertRaises(ValueError):
                await self.dataset_generator.generate_dataset_from_docs(
                    document_paths=mock_document_paths,
                    synthesizers=mock_synthesizers,
                    verbose=True,
                )

    async def test_generate_dataset_from_corpora_no_corpora(self):
        with self.assertRaises(ValueError):
            await self.dataset_generator.generate_dataset_from_corpora(
                corpora=[], synthesizers=[]
            )

    async def test_generate_dataset_from_corpora_run_except(self):
        mock_corpora = [
            MagicMock(spec=BaseCorpus),
            MagicMock(spec=BaseCorpus),
        ]
        mock_synthesizers = [
            MockSynthesizer(),
        ]
        with self.assertRaises(ValueError):
            await self.dataset_generator.generate_dataset_from_corpora(
                corpora=mock_corpora, synthesizers=mock_synthesizers, verbose=True
            )


if __name__ == "__main__":
    unittest.main()
