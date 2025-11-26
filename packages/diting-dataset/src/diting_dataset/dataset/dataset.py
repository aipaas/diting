#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import typing as t
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pandas import DataFrame as PandasDataframe

from diting_core.cases.llm_case import LLMCase

if TYPE_CHECKING:
    from datasets import Dataset as HFDataset


@dataclass
class EvaluationDataset:
    """
    Represents a dataset of evaluation testcases.

    Attributes
    ----------
    testcases : List[LLMCase]
        A list of evaluation cases.

    Methods
    -------
    to_hf_dataset()
        Converts the dataset to a Hugging Face Dataset.
    to_pandas()
        Converts the dataset to a pandas DataFrame.
    to_csv(path)
        Converts the dataset to a CSV file.
    to_jsonl(path)
        Converts the dataset to a JSONL file.
    from_hf_dataset(HFDataset)
        Creates an EvaluationDataset from a HFDataset.
    from_pandas(PandasDataframe)
        Creates an EvaluationDataset from a PandasDataframe.
    from_list(mapping)
        Creates an EvaluationDataset from a list of dictionaries.
    from_jsonl(path)
        Creates an EvaluationDataset from a JSONL file.
    """

    testcases: t.List[LLMCase]

    @classmethod
    def from_list(cls, data: t.List[t.Dict[str, t.Any]]) -> "EvaluationDataset":
        cases = [LLMCase.model_validate(testcase) for testcase in data]
        return cls(testcases=cases)

    @classmethod
    def from_pandas(cls, dataframe: PandasDataframe):
        """Creates an EvaluationDataset from a pandas DataFrame."""
        return cls.from_list(dataframe.to_dict(orient="records"))

    @classmethod
    def from_hf_dataset(cls, dataset: "HFDataset") -> "EvaluationDataset":
        """Creates an EvaluationDataset from a Hugging Face Dataset."""
        return cls.from_list(dataset.to_list())

    @classmethod
    def from_jsonl(cls, path: t.Union[str, Path]) -> "EvaluationDataset":
        """Creates an EvaluationDataset from a JSONL file."""
        with open(path, "r") as jsonlfile:
            data = [json.loads(line) for line in jsonlfile]
        return cls.from_list(data)

    def to_pandas(self) -> PandasDataframe:
        """Converts the dataset to a pandas DataFrame."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "pandas is not installed. Please install it to use this function."
            )

        data = self.to_list()
        return pd.DataFrame(data)

    def to_list(self) -> t.List[t.Dict[str, t.Any]]:
        rows = [testcase.model_dump() for testcase in self.testcases]
        return rows

    def to_csv(self, path: t.Union[str, Path]):
        """Converts the dataset to a CSV file."""
        import csv

        data = self.to_list()
        if not data:
            return

        fieldnames = data[0].keys()

        with open(path, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(row)

    def to_jsonl(self, path: t.Union[str, Path]):
        """Converts the dataset to a JSONL file."""
        with open(path, "w") as jsonlfile:
            for testcase in self.to_list():
                jsonlfile.write(json.dumps(testcase, ensure_ascii=False) + "\n")

    def to_hf_dataset(self) -> "HFDataset":
        """Converts the dataset to a Hugging Face Dataset."""
        try:
            from datasets import Dataset as HFDataset
        except ImportError:
            raise ImportError(
                "datasets is not installed. Please install it to use this function."
            )

        return HFDataset.from_list(self.to_list())

    def __repr__(self) -> str:
        return f"EvaluationDataset, len={len(self.testcases)})"
