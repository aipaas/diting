"""HotpotQA dataset implementations.

References Opik's implementation to provide HotpotQA multi-hop question answering dataset.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from diting_core.cases.llm_case import LLMCaseParams
from diting_optimizer.datasets.base_dataset import BaseDataset, InMemoryDataset


def xquad_qa_500(test_mode: bool = False) -> BaseDataset:
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
    nb_items = 500 if not test_mode else 5
    dataset_name = f"xquad_qa_500{'_test' if test_mode else ''}"

    # Load data file
    data_file = Path(__file__).parent / "xquad-zh.jsonl"

    if not data_file.exists():
        # If data file doesn't exist, return empty dataset with warning
        print(
            f"Warning: {data_file} not found. Returning empty dataset. "
            "Please add rag-qa-10.json to the data/ directory."
        )
        return InMemoryDataset(dataset_name, [])

    all_data = []
    with open(data_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            all_data.append(data)

    # Take first nb_items samples
    items = all_data[:nb_items]

    # Standardize data format
    formatted_items: list[dict[str, Any]] = []
    for idx, item in enumerate(items):
        formatted_items.append(
            {
                "id": f"xquad_qa_{idx}",
                LLMCaseParams.USER_INPUT.value: item.get("user_input", ""),
                LLMCaseParams.EXPECTED_OUTPUT.value: item.get("reference", ""),
                LLMCaseParams.CONTEXT.value: item.get("reference_contexts", []),
            }
        )

    return InMemoryDataset(dataset_name, formatted_items)


# ds = xquad_qa_500()
#
# for item in ds.get_items(100):
#     print(item)
