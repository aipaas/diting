"""测试 ParameterOptimizer"""

from unittest.mock import patch

import pytest

from diting_core.metrics.base_metric import BaseMetric
from diting_core.optimization.algorithms.prompt.model_parameters.tpe.optimizer import (
    ParameterOptimizer,
)
from diting_core.optimization.algorithms.prompt.model_parameters.tpe.search_space import (
    ParameterSearchSpace,
    ParameterSpec,
    ParameterType,
)
from diting_core.optimization.datasets.base_dataset import InMemoryDataset
from diting_core.optimization.optimization_result import OptimizationResult
from diting_core.optimization.target.prompt_config import PromptConfig

# Import mock helpers from parent directory
import sys
from pathlib import Path

test_helpers_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(test_helpers_path))
from test_helpers import (  # noqa: E402
    mock_evaluate_prompt_sync,
    mock_evaluate_prompt,
    MockLLMAdapter,
)


class MockMetric(BaseMetric):
    """模拟评估指标"""

    async def _compute(self, output: str, expected_output: str, **kwargs) -> float:
        """简单的模拟评分"""
        if not output or not expected_output:
            return 0.0
        # 简单的相似度计算
        return len(set(output.split()) & set(expected_output.split())) / max(
            len(output.split()), len(expected_output.split())
        )


class TestParameterOptimizer:
    """测试 ParameterOptimizer 类"""

    def test_optimizer_initialization(self):
        """测试优化器初始化"""
        optimizer = ParameterOptimizer(
            max_iterations=20, seed=42, local_search_ratio=0.3
        )

        assert optimizer.max_iterations == 20
        assert optimizer.seed == 42
        assert optimizer.local_search_ratio == 0.3
        assert optimizer.local_search_scale > 0

    def test_local_search_ratio_bounds(self):
        """测试局部搜索比例边界"""
        # 测试超过上限
        optimizer1 = ParameterOptimizer(local_search_ratio=1.5)
        assert optimizer1.local_search_ratio == 1.0

        # 测试低于下限
        optimizer2 = ParameterOptimizer(local_search_ratio=-0.1)
        assert optimizer2.local_search_ratio == 0.0

    @pytest.mark.asyncio
    async def test_optimize_requires_parameter_space(self):
        """测试优化需要 parameter_space 参数"""
        optimizer = ParameterOptimizer(max_iterations=5)
        prompt = PromptConfig(user="Hello {input}", llm=MockLLMAdapter())
        dataset = InMemoryDataset(
            name="test_dataset",
            items=[{"id": "1", "input": "world", "expected_output": "Hello world"}],
        )
        metric = MockMetric()

        # 缺少 parameter_space 应抛出异常
        with pytest.raises(
            ValueError, match="ParameterOptimizer requires parameter_space"
        ):
            await optimizer.optimize(
                config=prompt, dataset=dataset, metric=metric, n_trials=5
            )

    @pytest.mark.asyncio
    @patch(
        "diting_core.optimization.algorithms.prompt.model_parameters.tpe.optimizer.evaluate_prompt",
        mock_evaluate_prompt,
    )
    @patch(
        "diting_core.optimization.algorithms.prompt.model_parameters.tpe.optimizer.evaluate_prompt_sync",
        mock_evaluate_prompt_sync,
    )
    async def test_optimize_with_dict_parameter_space(self):
        """测试使用字典形式的 parameter_space 进行优化"""
        optimizer = ParameterOptimizer(max_iterations=3, seed=42)
        prompt = PromptConfig(user="Say {input}", llm=MockLLMAdapter())
        dataset = InMemoryDataset(
            name="test_dataset",
            items=[
                {"id": "1", "input": "hello", "expected_output": "hello"},
                {"id": "2", "input": "world", "expected_output": "world"},
            ],
        )
        metric = MockMetric()

        # 使用字典形式定义参数空间
        parameter_space_dict = {
            "temperature": {"distribution": "float", "low": 0.0, "high": 1.0},
        }

        result = await optimizer.optimize(
            config=prompt,
            dataset=dataset,
            metric=metric,
            n_trials=3,
            parameter_space=parameter_space_dict,
        )

        assert isinstance(result, OptimizationResult)
        assert result.optimizer_name == "ParameterOptimizer"
        # metric_name 可能是 "MockMetric" 或 "BaseMetric"
        assert "Metric" in result.metric_name
        assert result.initial_score is not None
        assert result.best_score >= 0

    @pytest.mark.asyncio
    @patch(
        "diting_core.optimization.algorithms.prompt.model_parameters.tpe.optimizer.evaluate_prompt",
        mock_evaluate_prompt,
    )
    @patch(
        "diting_core.optimization.algorithms.prompt.model_parameters.tpe.optimizer.evaluate_prompt_sync",
        mock_evaluate_prompt_sync,
    )
    async def test_optimize_with_parameter_search_space(self):
        """测试使用 ParameterSearchSpace 对象进行优化"""
        optimizer = ParameterOptimizer(max_iterations=5, seed=42)
        prompt = PromptConfig(user="Echo {input}", llm=MockLLMAdapter())
        dataset = InMemoryDataset(
            name="test_dataset",
            items=[
                {"id": "1", "input": "test", "expected_output": "test"},
                {"id": "2", "input": "data", "expected_output": "data"},
            ],
        )
        metric = MockMetric()

        parameter_space = ParameterSearchSpace(
            parameters=[
                ParameterSpec(
                    name="temperature",
                    distribution=ParameterType.FLOAT,
                    low=0.0,
                    high=1.0,
                ),
                ParameterSpec(
                    name="max_tokens",
                    distribution=ParameterType.INT,
                    low=10,
                    high=100,
                ),
            ]
        )

        result = await optimizer.optimize(
            config=prompt,
            dataset=dataset,
            metric=metric,
            n_trials=5,
            parameter_space=parameter_space,
        )

        assert isinstance(result, OptimizationResult)
        assert result.best_config is not None
        assert result.best_config.model_params is not None
        assert "temperature" in result.best_config.model_params
        assert "max_tokens" in result.best_config.model_params

    @pytest.mark.asyncio
    @patch(
        "diting_core.optimization.algorithms.prompt.model_parameters.tpe.optimizer.evaluate_prompt",
        mock_evaluate_prompt,
    )
    @patch(
        "diting_core.optimization.algorithms.prompt.model_parameters.tpe.optimizer.evaluate_prompt_sync",
        mock_evaluate_prompt_sync,
    )
    async def test_optimization_result_structure(self):
        """测试优化结果结构"""
        optimizer = ParameterOptimizer(max_iterations=3, seed=42)
        prompt = PromptConfig(user="{input}", llm=MockLLMAdapter())
        dataset = InMemoryDataset(
            name="test_dataset",
            items=[{"id": "1", "input": "a", "expected_output": "a"}],
        )
        metric = MockMetric()

        parameter_space = ParameterSearchSpace(
            parameters=[
                ParameterSpec(
                    name="temperature",
                    distribution=ParameterType.FLOAT,
                    low=0.0,
                    high=1.0,
                )
            ]
        )

        result = await optimizer.optimize(
            config=prompt,
            dataset=dataset,
            metric=metric,
            n_trials=3,
            parameter_space=parameter_space,
        )

        # 检查结果字段
        assert result.optimizer_name == "ParameterOptimizer"
        assert result.best_config is not None
        assert result.best_score >= 0
        # metric_name 可能是 "MockMetric" 或 "BaseMetric"
        assert "Metric" in result.metric_name
        assert result.initial_prompt is not None
        assert result.initial_score is not None
        assert isinstance(result.improvement, float)

        # 检查 details 字段
        assert "optimized_parameters" in result.details
        assert "optimized_model_params" in result.details
        assert "parameter_space" in result.details
        assert "n_trials" in result.details
        assert "global_trials" in result.details
        assert "local_trials" in result.details
        assert "search_ranges" in result.details
        assert "parameter_importance" in result.details

        # 检查历史记录
        assert len(result.history) > 0
        first_entry = result.history[0]
        assert first_entry["iteration"] == 0
        assert first_entry["type"] == "baseline"
        assert first_entry["score"] == result.initial_score

    @pytest.mark.asyncio
    @patch(
        "diting_core.optimization.algorithms.prompt.model_parameters.tpe.optimizer.evaluate_prompt",
        mock_evaluate_prompt,
    )
    @patch(
        "diting_core.optimization.algorithms.prompt.model_parameters.tpe.optimizer.evaluate_prompt_sync",
        mock_evaluate_prompt_sync,
    )
    async def test_two_stage_optimization(self):
        """测试两阶段优化（全局搜索 + 局部搜索）"""
        optimizer = ParameterOptimizer(
            max_iterations=10, seed=42, local_search_ratio=0.3
        )
        prompt = PromptConfig(user="{input}", llm=MockLLMAdapter())
        dataset = InMemoryDataset(
            name="test_dataset",
            items=[{"id": "1", "input": "test", "expected_output": "test"}],
        )
        metric = MockMetric()

        parameter_space = ParameterSearchSpace(
            parameters=[
                ParameterSpec(
                    name="temperature",
                    distribution=ParameterType.FLOAT,
                    low=0.0,
                    high=1.0,
                )
            ]
        )

        result = await optimizer.optimize(
            config=prompt,
            dataset=dataset,
            metric=metric,
            n_trials=10,
            parameter_space=parameter_space,
        )

        # 检查是否执行了两阶段优化
        assert result.details["global_trials"] == 7  # 70% for global
        assert result.details["local_trials"] == 3  # 30% for local

        # 检查搜索范围记录
        assert "global" in result.details["search_ranges"]

        # 局部搜索可能因参数类型而不执行（如只有 categorical）
        if "local" in result.details["search_ranges"]:
            # 检查局部搜索范围是否缩小
            global_range = result.details["search_ranges"]["global"]["temperature"]
            local_range = result.details["search_ranges"]["local"]["temperature"]
            assert (
                local_range["max"] - local_range["min"]
                < global_range["max"] - global_range["min"]
            )

    @pytest.mark.asyncio
    @patch(
        "diting_core.optimization.algorithms.prompt.model_parameters.tpe.optimizer.evaluate_prompt",
        mock_evaluate_prompt,
    )
    @patch(
        "diting_core.optimization.algorithms.prompt.model_parameters.tpe.optimizer.evaluate_prompt_sync",
        mock_evaluate_prompt_sync,
    )
    async def test_parameter_importance_analysis(self):
        """测试参数重要性分析"""
        optimizer = ParameterOptimizer(max_iterations=8, seed=42)
        prompt = PromptConfig(user="{input}", llm=MockLLMAdapter())
        dataset = InMemoryDataset(
            name="test_dataset",
            items=[{"id": "1", "input": "test", "expected_output": "test"}],
        )
        metric = MockMetric()

        parameter_space = ParameterSearchSpace(
            parameters=[
                ParameterSpec(
                    name="temperature",
                    distribution=ParameterType.FLOAT,
                    low=0.0,
                    high=1.0,
                ),
                ParameterSpec(
                    name="max_tokens",
                    distribution=ParameterType.INT,
                    low=10,
                    high=100,
                ),
            ]
        )

        result = await optimizer.optimize(
            config=prompt,
            dataset=dataset,
            metric=metric,
            n_trials=8,
            parameter_space=parameter_space,
        )

        # 检查参数重要性
        importance = result.details.get("parameter_importance", {})
        # 至少应该有参数重要性信息（即使为空字典也可以）
        assert isinstance(importance, dict)

    @pytest.mark.asyncio
    @patch(
        "diting_core.optimization.algorithms.prompt.model_parameters.tpe.optimizer.evaluate_prompt",
        mock_evaluate_prompt,
    )
    @patch(
        "diting_core.optimization.algorithms.prompt.model_parameters.tpe.optimizer.evaluate_prompt_sync",
        mock_evaluate_prompt_sync,
    )
    async def test_optimization_with_categorical_parameter(self):
        """测试包含分类参数的优化"""
        optimizer = ParameterOptimizer(max_iterations=5, seed=42)
        prompt = PromptConfig(user="{input}", llm=MockLLMAdapter())
        dataset = InMemoryDataset(
            name="test_dataset",
            items=[{"id": "1", "input": "test", "expected_output": "test"}],
        )
        metric = MockMetric()

        parameter_space = ParameterSearchSpace(
            parameters=[
                ParameterSpec(
                    name="temperature",
                    distribution=ParameterType.FLOAT,
                    low=0.0,
                    high=1.0,
                ),
                ParameterSpec(
                    name="response_format",
                    distribution=ParameterType.CATEGORICAL,
                    choices=["text", "json"],
                ),
            ]
        )

        result = await optimizer.optimize(
            config=prompt,
            dataset=dataset,
            metric=metric,
            n_trials=5,
            parameter_space=parameter_space,
        )

        # 检查分类参数是否被优化
        optimized_params = result.get_optimized_parameters()
        assert "response_format" in optimized_params
        assert optimized_params["response_format"] in ["text", "json"]

    @pytest.mark.asyncio
    @patch(
        "diting_core.optimization.algorithms.prompt.model_parameters.tpe.optimizer.evaluate_prompt",
        mock_evaluate_prompt,
    )
    @patch(
        "diting_core.optimization.algorithms.prompt.model_parameters.tpe.optimizer.evaluate_prompt_sync",
        mock_evaluate_prompt_sync,
    )
    async def test_result_display_methods(self):
        """测试结果显示方法"""
        optimizer = ParameterOptimizer(max_iterations=3, seed=42)
        prompt = PromptConfig(user="{input}", llm=MockLLMAdapter())
        dataset = InMemoryDataset(
            name="test_dataset",
            items=[{"id": "1", "input": "test", "expected_output": "test"}],
        )
        metric = MockMetric()

        parameter_space = ParameterSearchSpace(
            parameters=[
                ParameterSpec(
                    name="temperature",
                    distribution=ParameterType.FLOAT,
                    low=0.0,
                    high=1.0,
                )
            ]
        )

        result = await optimizer.optimize(
            config=prompt,
            dataset=dataset,
            metric=metric,
            n_trials=3,
            parameter_space=parameter_space,
        )

        # 测试 __str__ 方法
        result_str = str(result)
        assert "OPTIMIZATION COMPLETE" in result_str
        assert "ParameterOptimizer" in result_str
        assert "Metric" in result_str

        # 测试 calculate_improvement 方法
        improvement_str = result._calculate_improvement_str()
        assert isinstance(improvement_str, str)

        # 测试 get_optimized_parameters 方法
        params = result.get_optimized_parameters()
        assert isinstance(params, dict)
        assert "temperature" in params
