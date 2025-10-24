"""优化器评估数据集

包含常用的评估数据集，用于提示词优化。
"""

from diting_core.optimization.datasets.base_dataset import (
    BaseDataset,
    InMemoryDataset,
)
from diting_core.optimization.datasets.hotpot_qa import hotpot_300, hotpot_500
from diting_core.optimization.datasets.tiny_test import tiny_test

__all__ = [
    "BaseDataset",
    "InMemoryDataset",
    "hotpot_300",
    "hotpot_500",
    "tiny_test",
]
