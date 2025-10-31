"""HotpotQA 数据集

参考 Opik 的实现，提供 HotpotQA 多跳问答数据集。
"""

import json
from pathlib import Path

from diting_core.cases.llm_case import LLMCaseParams
from diting_optimizer.datasets.base_dataset import BaseDataset, InMemoryDataset


def hotpot_300(test_mode: bool = False) -> BaseDataset:
    """HotpotQA 数据集前 300 个样本

    参考 Opik 的实现：
    - 从 JSON 文件加载数据
    - 支持 test_mode（仅5个样本用于测试）

    Args:
        test_mode: 是否使用测试模式（仅返回5个样本）

    Returns:
        BaseDataset: HotpotQA 数据集实例
    """
    nb_items = 300 if not test_mode else 5
    dataset_name = f"hotpot_300{'_test' if test_mode else ''}"

    # 加载数据文件
    data_file = Path(__file__).parent / "data" / "hotpot-500.json"

    if not data_file.exists():
        # 如果数据文件不存在，返回空数据集并给出提示
        print(
            f"Warning: {data_file} not found. Returning empty dataset. "
            "Please add hotpot-500.json to the data/ directory."
        )
        return InMemoryDataset(dataset_name, [])

    with open(data_file, encoding="utf-8") as f:
        all_data = json.load(f)

    # 取前 nb_items 个样本
    items = all_data[:nb_items]

    # 标准化数据格式
    formatted_items = []
    for idx, item in enumerate(items):
        formatted_items.append(
            {
                "id": f"hotpot_{idx}",
                LLMCaseParams.USER_INPUT.value: item.get("question", ""),
                LLMCaseParams.EXPECTED_OUTPUT.value: item.get("answer", ""),
                LLMCaseParams.CONTEXT.value: item.get("context", []),
            }
        )

    return InMemoryDataset(dataset_name, formatted_items)


def hotpot_500(test_mode: bool = False) -> BaseDataset:
    """HotpotQA 数据集前 500 个样本

    Args:
        test_mode: 是否使用测试模式（仅返回5个样本）

    Returns:
        BaseDataset: HotpotQA 数据集实例
    """
    nb_items = 500 if not test_mode else 5
    dataset_name = f"hotpot_500{'_test' if test_mode else ''}"

    data_file = Path(__file__).parent / "data" / "hotpot-500.json"

    if not data_file.exists():
        print(
            f"Warning: {data_file} not found. Returning empty dataset. "
            "Please add hotpot-500.json to the data/ directory."
        )
        return InMemoryDataset(dataset_name, [])

    with open(data_file, encoding="utf-8") as f:
        all_data = json.load(f)

    items = all_data[:nb_items]

    formatted_items = []
    for idx, item in enumerate(items):
        formatted_items.append(
            {
                "id": f"hotpot_{idx}",
                LLMCaseParams.USER_INPUT.value: item.get("question", ""),
                LLMCaseParams.EXPECTED_OUTPUT.value: item.get("answer", ""),
                LLMCaseParams.CONTEXT.value: item.get("context", []),
                **item,
            }
        )

    return InMemoryDataset(dataset_name, formatted_items)
