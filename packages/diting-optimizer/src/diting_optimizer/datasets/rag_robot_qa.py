"""HotpotQA dataset implementations.

References Opik's implementation to provide HotpotQA multi-hop question answering dataset.
"""

from __future__ import annotations

import json
from pathlib import Path

from diting_core.cases.llm_case import LLMCaseParams
from diting_optimizer.datasets.base_dataset import BaseDataset, InMemoryDataset


def transform_context(data_dict):
    # 1. 获取原始的 context 列表
    original_context = data_dict.get("context", [])

    # 2. 使用列表推导式创建新的 context 列表
    new_context = [
        json.dumps(
            {
                "id": item["id"],
                "updateTime": item["updateTime"],
                "content": item["q"],  # 从 'q' 键获取内容
                "sourceName": item["sourceName"],
            },
            ensure_ascii=False,
            indent=2,
        )
        for item in original_context
    ]

    # 3. 更新原始字典的 context 键
    data_dict["context"] = new_context

    return data_dict


def rag_qa_10(test_mode: bool = False) -> BaseDataset:
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
    data_file = Path(__file__).parent / "data" / "rag-qa-10.json"

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
    formatted_items = []
    for idx, item in enumerate(items):
        item = transform_context(item)
        formatted_items.append(
            {
                "id": f"rag-qa_{idx}",
                LLMCaseParams.USER_INPUT.value: item.get("question", ""),
                LLMCaseParams.EXPECTED_OUTPUT.value: item.get("answer", ""),
                LLMCaseParams.CONTEXT.value: item.get("context", []),
            }
        )

    return InMemoryDataset(dataset_name, formatted_items)
