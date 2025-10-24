"""优化器基类"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from diting_core.callbacks.base import ChainType
from diting_core.callbacks.manager import new_group
from diting_core.metrics.base_metric import BaseMetric
from diting_core.optimization.datasets.base_dataset import BaseDataset
from diting_core.callbacks.usage import (
    GetEmbedTokenCallbackHandler,
    GetLLMTokenCallbackHandler,
    compute_token_usages,
)
from diting_core.optimization.optimization_result import OptimizationResult
from diting_core.optimization.target.base_config import BaseConfig

logger = logging.getLogger(__name__)


class BaseOptimizer(ABC):
    async def optimize(
        self,
        config: BaseConfig,
        dataset: BaseDataset,
        metric: BaseMetric,
        n_samples: int | None = None,
        **kwargs: Any,
    ) -> OptimizationResult:
        """通用优化接口

        Args:
            config: 优化目标配置（任意BaseConfig子类）
            dataset: 评估数据集
            metric: 评估指标
            n_samples: Optional number of items to test in the dataset
            **kwargs: 其他优化参数，可能包含:
                - callbacks: 回调管理器
                - verbose: 是否显示详细信息
                - tags: 标签列表
                - metadata: 元数据

        Returns:
            OptimizationResult: 优化结果
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
            tags=kwargs.get("tags", None),
            metadata=kwargs.get("metadata", None),
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
        n_samples: int | None = None,
        **kwargs: Any,
    ) -> OptimizationResult:
        """子类实现的具体优化逻辑

        Args:
            config: 优化目标配置
            dataset: 评估数据集
            metric: 评估指标
            n_samples: Optional number of items to test in the dataset
            **kwargs: 其他参数

        Returns:
            OptimizationResult: 优化结果
        """
        raise NotImplementedError

    @staticmethod
    def calculate_improvement(current_score: float, previous_score: float) -> float:
        """Calculate the improvement percentage between scores."""
        return (
            (current_score - previous_score) / previous_score
            if previous_score > 0
            else 0
        )
