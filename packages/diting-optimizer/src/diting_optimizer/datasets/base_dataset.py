"""数据集基类

参考 Opik Dataset 的设计，提供标准的数据集接口。
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseDataset(ABC):
    """优化器数据集基类

    所有评估数据集都应继承此类并实现 get_items 方法。

    Attributes:
        name: 数据集名称
    """

    def __init__(self, name: str):
        """初始化数据集

        Args:
            name: 数据集名称
        """
        self.name = name

    @abstractmethod
    def get_items(self, n_samples: Optional[int] = None) -> list[dict[str, Any]]:
        """获取数据集项目

        Args:
            n_samples: 可选，限制返回的项目数量

        Returns:
            数据项列表，每个项目是一个字典，通常包含：
            - id: 唯一标识
            - input: 输入数据
            - expected_output: 期望输出（如果有）
            - context: 上下文信息（如果有）
        """
        raise NotImplementedError

    def __len__(self) -> int:
        """返回数据集大小

        Returns:
            int: 数据集项目数量
        """
        return len(self.get_items())


class InMemoryDataset(BaseDataset):
    """内存数据集实现

    将数据项存储在内存中的简单实现。

    Attributes:
        name: 数据集名称
        _items: 数据项列表
    """

    def __init__(self, name: str, items: list[dict[str, Any]]):
        """初始化内存数据集

        Args:
            name: 数据集名称
            items: 数据项列表
        """
        super().__init__(name)
        self._items = items

    def get_items(self, n_samples: Optional[int] = None) -> list[dict[str, Any]]:
        """获取数据集项目

        Args:
            n_samples: 可选，限制返回的项目数量

        Returns:
            数据项列表
        """
        if n_samples is None:
            return self._items
        return self._items[:n_samples]
