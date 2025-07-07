#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from typing import Dict, Any
from unittest.mock import AsyncMock, patch

from diting_core.cases.llm_case import LLMCase
from diting_core.synthesis.rules.base_rule import BaseGenerateRule
from diting_core.synthesis.synthesizer import Synthesizer, BaseCorpus


class MockQAGenerateRule(BaseGenerateRule):
    async def _apply(self, rule_input: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        return {"generated_output": "mocked_output"}


class TestSynthesizer(unittest.IsolatedAsyncioTestCase):
    async def test_generate(self):
        """测试generate方法的正常情况"""
        rule = MockQAGenerateRule()
        rule_input = {"key": "value"}
        with patch.object(rule, "apply", new_callable=AsyncMock) as mock_apply:
            mock_apply.return_value = {"generated_output": "mocked_output"}
            result = await Synthesizer.generate(rule, rule_input)
            self.assertEqual(result, {"generated_output": "mocked_output"})
            mock_apply.assert_called_once_with(rule_input)

    async def test_generate_llm_case_from_corpus(self):
        """测试generate_llm_case_from_corpus方法的正常情况"""
        corpus = BaseCorpus(context=["test context"], scenario="test scenario")
        mock_qa_rule = MockQAGenerateRule()
        with (
            patch(
                "diting_core.synthesis.synthesizer.QAGenerateRule",
                return_value=mock_qa_rule,
            ),
            patch.object(
                Synthesizer, "generate", new_callable=AsyncMock
            ) as mock_generate,
        ):
            mock_generate.return_value = {"generated_output": "mocked_output"}
            result = await Synthesizer.generate_llm_case_from_corpus(corpus)
            self.assertIsInstance(result, LLMCase)
            mock_generate.assert_called_once_with(mock_qa_rule, corpus.model_dump())

    async def test_generate_llm_case_from_corpus_invalid(self):
        """测试generate_llm_case_from_corpus方法的异常情况"""
        corpus = BaseCorpus(context=["test context"], scenario="test scenario")
        with (
            patch(
                "diting_core.synthesis.rules.qa.rule.QAGenerateRule",
                return_value=MockQAGenerateRule(),
            ),
            patch.object(
                Synthesizer, "generate", new_callable=AsyncMock
            ) as mock_generate,
        ):
            mock_generate.side_effect = Exception("Error during generation")
            with self.assertRaises(Exception):
                await Synthesizer.generate_llm_case_from_corpus(corpus)


if __name__ == "__main__":
    unittest.main()
