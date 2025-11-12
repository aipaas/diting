"""Base dataset classes for optimization.

References Opik Dataset design to provide standard dataset interfaces.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple
import random


class BaseDataset(ABC):
    """Base class for optimizer datasets.

    All evaluation datasets should inherit from this class and implement the get_items method.

    Attributes:
        name : str
            Name of the dataset
    """

    def __init__(self, name: str):
        """Initialize dataset.

        Parameters
        ----------
        name : str
            Name of the dataset
        """
        self.name = name

    @abstractmethod
    def get_items(self, n_samples: Optional[int] = None) -> List[dict[str, Any]]:
        """Get dataset items.

        Parameters
        ----------
        n_samples : Optional[int]
            Optional limit on the number of items to return

        Returns
        -------
        List[dict[str, Any]]
            List of data items, where each item is a dictionary typically containing:
            - id: Unique identifier
            - input: Input data
            - expected_output: Expected output (if available)
            - context: Context information (if available)

        Raises
        ------
        NotImplementedError
            If not implemented by subclass
        """
        raise NotImplementedError

    @abstractmethod
    def split(
        self,
        train_ratio: float = 0.8,
        shuffle: bool = True,
        random_state: Optional[int] = None,
    ) -> Tuple["BaseDataset", "BaseDataset"]:
        """Split dataset into training and testing sets.

        Parameters
        ----------
        train_ratio : float, default 0.8
            Ratio of data to allocate to training set (0.0-1.0)
        shuffle : bool, default True
            Whether to shuffle data before splitting
        random_state : Optional[int], default None
            Random seed for reproducible splits

        Returns
        -------
        Tuple[BaseDataset, BaseDataset]
            Tuple of (train_dataset, test_dataset)

        Raises
        ------
        NotImplementedError
            If not implemented by subclass
        """
        raise NotImplementedError

    def __len__(self) -> int:
        """Return dataset size.

        Returns
        -------
        int
            Number of items in the dataset
        """
        return len(self.get_items())


class InMemoryDataset(BaseDataset):
    """In-memory dataset implementation.

    Simple implementation that stores data items in memory.

    Attributes:
        name : str
            Name of the dataset
        _items : List[dict[str, Any]]
            List of data items
    """

    def __init__(self, name: str, items: List[dict[str, Any]]):
        """Initialize in-memory dataset.

        Parameters
        ----------
        name : str
            Name of the dataset
        items : List[dict[str, Any]]
            List of data items
        """
        super().__init__(name)
        self._items = items

    def get_items(self, n_samples: Optional[int] = None) -> List[dict[str, Any]]:
        """Get dataset items.

        Parameters
        ----------
        n_samples : Optional[int]
            Optional limit on the number of items to return

        Returns
        -------
        List[dict[str, Any]]
            List of data items (limited by n_samples if provided)
        """
        if n_samples is None:
            return self._items
        return self._items[:n_samples]

    def __len__(self) -> int:
        """Return dataset size.

        Returns
        -------
        int
            Number of items in the dataset
        """
        return len(self._items)

    def split(
        self,
        train_ratio: float = 0.8,
        shuffle: bool = True,
        random_state: Optional[int] = None,
    ) -> Tuple["BaseDataset", "BaseDataset"]:
        """Split dataset into training and testing sets.

        Parameters
        ----------
        train_ratio : float, default 0.8
            Ratio of data to allocate to training set (0.0-1.0)
        shuffle : bool, default True
            Whether to shuffle data before splitting
        random_state : Optional[int], default None
            Random seed for reproducible splits

        Returns
        -------
        Tuple[BaseDataset, BaseDataset]
            Tuple of (train_dataset, test_dataset)
        """
        if not 0.0 <= train_ratio <= 1.0:
            raise ValueError("train_ratio must be between 0.0 and 1.0")

        items = self._items.copy()

        if shuffle:
            if random_state is not None:
                random.seed(random_state)
            random.shuffle(items)

        split_index = int(len(items) * train_ratio)
        train_items = items[:split_index]
        test_items = items[split_index:]

        train_dataset = InMemoryDataset(f"{self.name}_train", train_items)
        test_dataset = InMemoryDataset(f"{self.name}_test", test_items)

        return train_dataset, test_dataset
