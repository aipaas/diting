"""Base optimizer module for all optimization algorithms."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from diting_core.callbacks.base import ChainType
from diting_core.callbacks.manager import new_group
from diting_core.callbacks.usage import (
    GetEmbedTokenCallbackHandler,
    GetLLMTokenCallbackHandler,
    compute_token_usages,
)
from diting_core.metrics.base_metric import BaseMetric
from diting_optimizer.datasets.base_dataset import BaseDataset
from diting_optimizer.optimization_result import OptimizationResult
from diting_optimizer.target.base_config import BaseConfig

logger = logging.getLogger(__name__)


class BaseOptimizer(ABC):
    """Abstract base class for all optimization algorithms.

    This class provides the common optimization interface and handles
    token tracking, callback management, and error handling for all
    optimizer implementations.

    Attributes:
        None (base class only defines interface)

    Notes:
        - All optimizers must inherit from this class
        - Token usage is automatically tracked
        - Callback management is handled centrally
        - Errors are properly propagated with callback notification
    """

    async def optimize(
        self,
        config: BaseConfig,
        dataset: BaseDataset,
        metric: BaseMetric,
        n_samples: Optional[int] = None,
        **kwargs: Any,
    ) -> OptimizationResult:
        """Execute optimization process using the provided configuration.

        This is the main entry point for optimization. It handles setup,
        token tracking, callback management, and error handling before
        delegating to the concrete implementation in _optimize.

        Parameters
        ----------
        config : BaseConfig
            Target configuration to optimize (any BaseConfig subclass)
        dataset : BaseDataset
            Dataset used for evaluation during optimization
        metric : BaseMetric
            Metric function used to evaluate performance
        n_samples : Optional[int]
            Number of items to test from the dataset. If None, use all items.
        **kwargs : Any
            Additional optimization parameters, may include:
                - callbacks : Callback handlers
                - verbose : bool
                    Whether to display detailed information

        Returns
        -------
        OptimizationResult
            Complete optimization results including best configuration,
            scores, and optimization history.

        Raises
        ------
        ValueError
            If configuration dependencies are not properly set
        Exception
            Propagates any errors from the optimization process
        """
        config.validate_dependencies()

        get_llm_token = GetLLMTokenCallbackHandler()
        get_embed_token = GetEmbedTokenCallbackHandler()
        callbacks = kwargs.pop("callbacks", [])
        callbacks.extend([get_llm_token, get_embed_token])

        run_manager, grp_cb = await new_group(
            name=self.__class__.__name__,
            inputs={
                "config": config,
                "metric": metric.name,
                "dataset": dataset.name,
                "n_samples": n_samples,
            },
            chain_type=ChainType.OPTIMIZE,
            callbacks=callbacks,
            verbose=kwargs.get("verbose", False),
        )

        try:
            result = await self._optimize(
                config=config,
                dataset=dataset,
                metric=metric,
                n_samples=n_samples,
                callbacks=grp_cb,
                **kwargs,
            )
        except Exception as e:
            await run_manager.on_chain_error(e)
            raise e

        result.total_llm_calls = len(get_llm_token.usages)
        result.total_embedding_calls = len(get_embed_token.usages)
        result.total_usages = compute_token_usages(
            get_llm_token.usages, get_embed_token.usages
        )
        await run_manager.on_chain_end({"optimization_result": result})
        return result

    @abstractmethod
    async def _optimize(
        self,
        config: BaseConfig,
        dataset: BaseDataset,
        metric: BaseMetric,
        n_samples: Optional[int] = None,
        **kwargs: Any,
    ) -> OptimizationResult:
        """Concrete optimization logic implemented by subclasses.

        This method must be implemented by all optimizer subclasses to
        define the specific optimization algorithm.

        Parameters
        ----------
        config : BaseConfig
            Target configuration to optimize
        dataset : BaseDataset
            Dataset used for evaluation during optimization
        metric : BaseMetric
            Metric function used to evaluate performance
        n_samples : Optional[int]
            Number of items to test from the dataset
        **kwargs : Any
            Additional parameters specific to the optimizer implementation

        Returns
        -------
        OptimizationResult
            Complete optimization results

        Raises
        ------
        NotImplementedError
            If not implemented by subclass
        """
        raise NotImplementedError

    @staticmethod
    def calculate_improvement(current_score: float, previous_score: float) -> float:
        """Calculate the improvement percentage between scores.

        Parameters
        ----------
        current_score : float
            The current score
        previous_score : float
            The previous/baseline score

        Returns
        -------
        float
            Improvement percentage (0.0 for no improvement or division by zero case)
        """
        if previous_score == 0:
            return 0.0 if current_score == 0 else float("inf")
        return (current_score - previous_score) / previous_score
