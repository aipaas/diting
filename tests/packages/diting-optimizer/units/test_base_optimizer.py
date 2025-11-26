"""测试重构后的BaseOptimizer"""

from typing import Optional, Tuple

import pytest

from diting_optimizer.base_optimizer import BaseOptimizer
from diting_optimizer.target.base_config import BaseConfig
from diting_optimizer.datasets.base_dataset import BaseDataset
from diting_core.metrics.base_metric import BaseMetric
from diting_optimizer.optimization_result import OptimizationResult


class MockConfig(BaseConfig):
    """用于测试的Mock配置"""

    def __init__(self, value: str = "test"):
        super().__init__()
        self.value = value
        self.execute_calls = []

    def validate_dependencies(self) -> None:
        pass

    async def execute(self, input_data: str, **kwargs) -> str:
        self.execute_calls.append({"input": input_data, "kwargs": kwargs})
        return f"result_{self.value}_{input_data}"


class MockOptimizer(BaseOptimizer):
    """用于测试的Mock优化器"""

    def __init__(self):
        super().__init__()
        self.optimize_calls = []

    async def _optimize(
        self,
        config: BaseConfig,
        dataset: BaseDataset,
        metric: BaseMetric,
        **kwargs,
    ) -> OptimizationResult:
        self.optimize_calls.append(
            {
                "config": config,
                "dataset": dataset,
                "metric": metric,
                "kwargs": kwargs,
            }
        )

        # 返回模拟的优化结果
        return OptimizationResult(
            optimizer_name=self.__class__.__name__,
            best_config=config,
            best_score=0.8,
            metric_name=metric.__class__.__name__,
            initial_config=config,
            initial_score=0.6,
            improvement=0.2,
            histories=[],
            details={},
            total_llm_calls=5,
            iterations=3,
        )


class MockDataset(BaseDataset):
    """用于测试的Mock数据集"""

    def split(
        self,
        train_ratio: float = 0.8,
        shuffle: bool = True,
        random_state: Optional[int] = None,
    ) -> Tuple["BaseDataset", "BaseDataset"]:
        pass

    def __init__(self, name: str = "test_dataset"):
        self.name = name
        self.items = [
            {"input": "test1", "expected_output": "output1"},
            {"input": "test2", "expected_output": "output2"},
        ]

    def get_items(self):
        return self.items


class MockMetric(BaseMetric):
    """用于测试的Mock指标"""

    async def _compute(self, output: str, expected_output: str, **kwargs) -> float:
        return 0.8


class TestBaseOptimizer:
    """测试BaseOptimizer基类"""

    def test_base_optimizer_is_abstract(self):
        """测试BaseOptimizer是抽象类"""
        with pytest.raises(TypeError):
            BaseOptimizer()

    @pytest.mark.asyncio
    async def test_optimize_interface(self):
        """测试optimize通用接口"""
        optimizer = MockOptimizer()
        config = MockConfig("test_config")
        dataset = MockDataset("test_data")
        metric = MockMetric()

        result = await optimizer.optimize(
            config=config,
            dataset=dataset,
            metric=metric,
            n_samples=10,
            n_trials=10,
            verbose=True,
            test_param="test_value",
        )

        # 验证调用
        assert len(optimizer.optimize_calls) == 1
        call = optimizer.optimize_calls[0]
        assert call["config"] is config
        assert call["dataset"] is dataset
        assert call["metric"] is metric
        assert call["kwargs"]["n_trials"] == 10
        assert call["kwargs"]["verbose"]
        assert call["kwargs"]["test_param"] == "test_value"

        # 验证结果
        assert isinstance(result, OptimizationResult)
        assert result.optimizer_name == "MockOptimizer"
        assert result.best_score == 0.8

    @pytest.mark.asyncio
    async def test_optimize_with_exception(self):
        """测试optimize过程中异常处理"""
        optimizer = MockOptimizer()
        config = MockConfig()
        dataset = MockDataset()
        metric = MockMetric()

        # 修改Mock优化器让它抛出异常
        async def failing_optimize(*args, **kwargs):
            raise ValueError("Test exception")

        optimizer._optimize = failing_optimize

        with pytest.raises(ValueError, match="Test exception"):
            await optimizer.optimize(config, dataset, metric, 5)
