#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch, MagicMock

from diting_core.cases.llm_case import LLMCase
from diting_dataset.dataset.dataset import EvaluationDataset


class TestEvaluationDataset(unittest.TestCase):
    @patch("diting_core.cases.llm_case.LLMCase.model_validate")
    def test_from_list(self, mock_model_validate):
        mock_case = MagicMock()
        mock_model_validate.return_value = mock_case
        data = [{"key": "value"}, {"key": "value2"}]

        dataset = EvaluationDataset.from_list(data)

        self.assertEqual(len(dataset.testcases), 2)
        self.assertEqual(dataset.testcases[0], mock_case)
        mock_model_validate.assert_any_call(data[0])
        mock_model_validate.assert_any_call(data[1])

    @patch("diting_dataset.dataset.dataset.PandasDataframe")
    def test_from_pandas(self, mock_dataframe):
        mock_dataframe.to_dict.return_value = [{"key": "value"}]
        dataset = EvaluationDataset.from_pandas(mock_dataframe)

        self.assertEqual(len(dataset.testcases), 1)

    def test_to_pandas(self):
        mock_case = MagicMock(model_dump=lambda: {"key": "value"})
        self.dataset = EvaluationDataset(testcases=[mock_case])
        df = self.dataset.to_pandas()
        self.assertEqual(df.to_dict(), {"key": {0: "value"}})

    @patch("datasets.Dataset")
    def test_from_hf_dataset(self, mock_hf_dataset):
        mock_hf_dataset.to_list.return_value = [{"key": "value"}]
        dataset = EvaluationDataset.from_hf_dataset(mock_hf_dataset)

        self.assertEqual(len(dataset.testcases), 1)

    @patch(
        "builtins.open",
        new_callable=unittest.mock.mock_open,
        read_data='{"key": "value"}\n{"key": "value2"}\n',
    )
    @patch("diting_core.cases.llm_case.LLMCase.model_validate")
    def test_from_jsonl(self, mock_model_validate, mock_open):
        mock_case = MagicMock()
        mock_model_validate.return_value = mock_case

        dataset = EvaluationDataset.from_jsonl("dummy_path.jsonl")

        self.assertEqual(len(dataset.testcases), 2)
        mock_model_validate.assert_any_call({"key": "value"})
        mock_model_validate.assert_any_call({"key": "value2"})

    @patch("diting_core.cases.llm_case.LLMCase.model_dump")
    def test_to_list(self, mock_model_dump):
        mock_case = LLMCase()
        self.dataset = EvaluationDataset(testcases=[mock_case])
        mock_model_dump.return_value = {"key": "value"}

        result = self.dataset.to_list()

        self.assertEqual(result, [{"key": "value"}])

    @patch("builtins.open", new_callable=unittest.mock.mock_open)
    def test_to_csv(self, mock_open):
        # 修正 model_dump 返回的内容
        mock_case = MagicMock(model_dump=lambda: {"key": "value"})
        self.dataset = EvaluationDataset(testcases=[mock_case])
        self.dataset.to_csv("dummy_path.csv")

        mock_open.assert_called_once_with("dummy_path.csv", "w", newline="")

    @patch("builtins.open", new_callable=unittest.mock.mock_open)
    def test_to_jsonl(self, mock_open):
        self.dataset = EvaluationDataset(
            testcases=[MagicMock(model_dump=lambda: {"key": "value"})]
        )
        self.dataset.to_jsonl("dummy_path.jsonl")

        mock_open.assert_called_once_with("dummy_path.jsonl", "w")
        handle = mock_open()
        handle.write.assert_called_once_with('{"key": "value"}\n')

    @patch("datasets.Dataset")
    def test_to_hf_dataset(self, mock_hf_dataset):
        self.dataset = EvaluationDataset(
            testcases=[MagicMock(model_dump=lambda: {"key": "value"})]
        )
        mock_hf_dataset.from_list.return_value = mock_hf_dataset

        result = self.dataset.to_hf_dataset()

        self.assertEqual(result, mock_hf_dataset)
        mock_hf_dataset.from_list.assert_called_once_with(self.dataset.to_list())

    def test_repr(self):
        self.dataset = EvaluationDataset(testcases=[])
        self.assertEqual(repr(self.dataset), "EvaluationDataset, len=0)")


if __name__ == "__main__":
    unittest.main()
