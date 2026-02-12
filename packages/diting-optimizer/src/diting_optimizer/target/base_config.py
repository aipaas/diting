"""Base configuration classes for optimization targets."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict


class BaseConfig(BaseModel, ABC):
    """Base configuration class for optimization targets.

    All optimization target configurations should inherit from this class
    and implement the execute method. Configuration classes are responsible for:

    1. Storing configuration parameters
    2. Validating and formatting inputs
    3. Executing corresponding operations (through injected dependencies)

    Design Principles:
    - Configuration and execution logic are separated but self-contained
    - Dependency injection for testability
    - Support for method chaining

    Attributes:
        None (base class only defines interface)
    """

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    @abstractmethod
    def validate_dependencies(self) -> None:
        """Validate that dependencies have been properly injected.

        Subclasses should implement this method to check that necessary
        dependencies have been set. If dependencies are missing,
        a ValueError should be raised.

        Raises
        ------
        ValueError
            If required dependencies are not properly configured
        """
        pass

    @abstractmethod
    async def execute(self, input_data: Any, **kwargs) -> Any:
        """Execute the operation corresponding to this configuration.

        Parameters
        ----------
        input_data : Any
            Input data, specific type defined by subclass
        **kwargs : Any
            Additional parameters

        Returns
        -------
        Any
            Execution result, specific type defined by subclass

        Raises
        ------
        ValueError
            When dependencies are not properly configured
        """
        pass
