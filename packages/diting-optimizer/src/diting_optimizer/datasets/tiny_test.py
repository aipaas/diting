"""微型测试数据集

用于快速验证优化器功能的小型测试数据集。
"""

from diting_core.cases.llm_case import LLMCaseParams
from diting_optimizer.datasets.base_dataset import BaseDataset, InMemoryDataset


def tiny_test() -> BaseDataset:
    """微型测试数据集，用于快速验证

    包含 3 个简单的问答样本，适合快速测试和调试。

    Returns:
        BaseDataset: 微型测试数据集实例
    """
    items = [
        {
            "id": "tiny_1",
            LLMCaseParams.USER_INPUT.value: "What is the capital of France?",
            LLMCaseParams.EXPECTED_OUTPUT.value: "Paris",
        },
        {
            "id": "tiny_2",
            LLMCaseParams.USER_INPUT.value: "What is 2 + 2?",
            LLMCaseParams.EXPECTED_OUTPUT.value: "4",
        },
        {
            "id": "tiny_3",
            LLMCaseParams.USER_INPUT.value: "Who wrote Romeo and Juliet?",
            LLMCaseParams.EXPECTED_OUTPUT.value: "William Shakespeare",
        },
    ]
    return InMemoryDataset("tiny_test", items)
