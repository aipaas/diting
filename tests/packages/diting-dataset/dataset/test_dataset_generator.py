#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest
from unittest.mock import AsyncMock, MagicMock
from diting_core.models.llms.base_model import BaseLLM
from diting_dataset.dataset.dataset_generator import DataSetGenerator
from diting_dataset.dataset.dataset import EvaluationDataset
from diting_dataset.synthesis.base_synthesizer import BaseCorpus, BaseSynthesizer


class TestDataSetGenerator(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_llm = AsyncMock(spec=BaseLLM)
        cls.dataset_generator = DataSetGenerator(llm=cls.mock_llm)

    async def test_generate_dataset_from_corpora_success(self):
        mock_corpora = [
            MagicMock(spec=BaseCorpus),
            MagicMock(spec=BaseCorpus),
            MagicMock(spec=BaseCorpus),
        ]
        mock_synthesizers = [
            MagicMock(spec=BaseSynthesizer),
            MagicMock(spec=BaseSynthesizer),
            MagicMock(spec=BaseSynthesizer),
        ]

        # self.dataset_generator.generate_dataset_from_corpora = AsyncMock(return_value=mock_dataset)
        result = await self.dataset_generator.generate_dataset_from_corpora(
            corpora=mock_corpora, synthesizers=mock_synthesizers, verbose=True
        )
        self.assertEqual(result, EvaluationDataset(testcases=[]))


if __name__ == "__main__":
    unittest.main()
