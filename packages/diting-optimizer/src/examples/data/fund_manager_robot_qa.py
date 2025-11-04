"""HotpotQA dataset implementations.

References Opik's implementation to provide HotpotQA multi-hop question answering dataset.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from diting_core.cases.llm_case import LLMCaseParams
from diting_optimizer.datasets.base_dataset import BaseDataset, InMemoryDataset


def fund_manager_qa_10(test_mode: bool = False) -> BaseDataset:
    """Load RAG QA dataset with first 10 samples.

    References Opik's implementation:
    - Load data from JSON file
    - Support test_mode (only 5 samples for testing)

    Parameters
    ----------
    test_mode : bool
        Whether to use test mode (only return 5 samples)

    Returns
    -------
    BaseDataset
        RAG_QA dataset instance

    Notes:
        If the data file is not found, returns an empty dataset with a warning message.
    """
    nb_items = 10 if not test_mode else 5
    dataset_name = f"rag_qa_10{'_test' if test_mode else ''}"

    # Load data file
    data_file = Path(__file__).parent / "fund-manager-rag.json"

    if not data_file.exists():
        # If data file doesn't exist, return empty dataset with warning
        print(
            f"Warning: {data_file} not found. Returning empty dataset. "
            "Please add rag-qa-10.json to the data/ directory."
        )
        return InMemoryDataset(dataset_name, [])

    with open(data_file, encoding="utf-8") as f:
        all_data = json.load(f)

    # Take first nb_items samples
    items = all_data[:nb_items]

    # Standardize data format
    formatted_items: list[dict[str, Any]] = []
    for idx, item in enumerate(items):
        formatted_items.append(
            {
                "id": f"fund-manage-qa_{idx}",
                LLMCaseParams.USER_INPUT.value: item.get("question", ""),
                LLMCaseParams.EXPECTED_OUTPUT.value: item.get("answer", ""),
                LLMCaseParams.CONTEXT.value: item.get("context", []),
            }
        )

    return InMemoryDataset(dataset_name, formatted_items)
