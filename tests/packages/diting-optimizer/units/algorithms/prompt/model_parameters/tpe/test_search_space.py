"""测试参数搜索空间"""

import pytest
from optuna import create_study

from diting_optimizer.algorithms.prompt.model_parameters.tpe.types import (
    ParameterType,
)
from diting_optimizer.algorithms.prompt.model_parameters.tpe.search_space import (
    ParameterSearchSpace,
    ParameterSpec,
)
from diting_optimizer.target.prompt_config import PromptConfig


class TestParameterSpec:
    """测试 ParameterSpec 类"""

    def test_float_parameter_creation(self):
        """测试创建 float 参数"""
        spec = ParameterSpec(
            name="temperature",
            distribution=ParameterType.FLOAT,
            low=0.0,
            high=1.0,
            description="Temperature model_parameters",
        )

        assert spec.name == "temperature"
        assert spec.distribution == ParameterType.FLOAT
        assert spec.low == 0.0
        assert spec.high == 1.0
        assert spec.scale == "linear"

    def test_int_parameter_creation(self):
        """测试创建 int 参数"""
        spec = ParameterSpec(
            name="max_tokens",
            distribution=ParameterType.INT,
            low=100,
            high=1000,
            step=10,
        )

        assert spec.name == "max_tokens"
        assert spec.distribution == ParameterType.INT
        assert spec.low == 100
        assert spec.high == 1000
        assert spec.step == 10

    def test_categorical_parameter_creation(self):
        """测试创建 categorical 参数"""
        spec = ParameterSpec(
            name="model",
            distribution=ParameterType.CATEGORICAL,
            choices=["gpt-3.5-turbo", "gpt-4", "claude-3"],
        )

        assert spec.name == "model"
        assert spec.distribution == ParameterType.CATEGORICAL
        assert spec.choices == ["gpt-3.5-turbo", "gpt-4", "claude-3"]

    def test_log_scale_parameter(self):
        """测试对数缩放参数"""
        spec = ParameterSpec(
            name="learning_rate",
            distribution=ParameterType.FLOAT,
            low=0.001,
            high=0.1,
            scale="log",
        )

        assert spec.scale == "log"

    def test_invalid_float_parameter_no_bounds(self):
        """测试创建无边界的 float 参数应失败"""
        with pytest.raises(ValueError, match="float/int type requires min and max"):
            ParameterSpec(
                name="temp", distribution=ParameterType.FLOAT, low=None, high=None
            )

    def test_invalid_float_parameter_inverted_bounds(self):
        """测试创建边界倒置的 float 参数应失败"""
        with pytest.raises(ValueError, match="min must be less than max"):
            ParameterSpec(
                name="temp", distribution=ParameterType.FLOAT, low=1.0, high=0.0
            )

    def test_invalid_log_scale_with_negative_bounds(self):
        """测试对数缩放负边界应失败"""
        with pytest.raises(
            ValueError, match="log scaling requires positive boundaries"
        ):
            ParameterSpec(
                name="temp",
                distribution=ParameterType.FLOAT,
                low=-1.0,
                high=1.0,
                scale="log",
            )

    def test_invalid_categorical_no_choices(self):
        """测试创建无选项的 categorical 参数应失败"""
        with pytest.raises(ValueError, match="categorical type requires choices"):
            ParameterSpec(name="model", distribution=ParameterType.CATEGORICAL)

    def test_suggest_float_parameter(self):
        """测试采样 float 参数"""
        spec = ParameterSpec(
            name="temperature", distribution=ParameterType.FLOAT, low=0.0, high=1.0
        )

        study = create_study()
        trial = study.ask()
        value = spec.suggest(trial)

        assert isinstance(value, float)
        assert 0.0 <= value <= 1.0

    def test_suggest_int_parameter(self):
        """测试采样 int 参数"""
        spec = ParameterSpec(
            name="max_tokens", distribution=ParameterType.INT, low=100, high=1000
        )

        study = create_study()
        trial = study.ask()
        value = spec.suggest(trial)

        assert isinstance(value, int)
        assert 100 <= value <= 1000

    def test_suggest_categorical_parameter(self):
        """测试采样 categorical 参数"""
        choices = ["a", "b", "c"]
        spec = ParameterSpec(
            name="choice", distribution=ParameterType.CATEGORICAL, choices=choices
        )

        study = create_study()
        trial = study.ask()
        value = spec.suggest(trial)

        assert value in choices

    def test_apply_to_prompt_default_target(self):
        """测试默认目标应用到 model_params"""
        spec = ParameterSpec(
            name="temperature", distribution=ParameterType.FLOAT, low=0.0, high=1.0
        )

        prompt = PromptConfig(user="Hello")
        spec.apply_to_prompt(prompt, 0.7)

        assert prompt.model_params is not None
        assert prompt.model_params["temperature"] == 0.7

    def test_apply_to_prompt_custom_target(self):
        """测试自定义目标"""
        spec = ParameterSpec(
            name="temp",
            distribution=ParameterType.FLOAT,
            low=0.0,
            high=1.0,
            target="model_params.temperature",
        )

        prompt = PromptConfig(user="Hello")
        spec.apply_to_prompt(prompt, 0.8)

        assert prompt.model_params is not None
        assert prompt.model_params["temperature"] == 0.8

    def test_narrow_float_parameter(self):
        """测试缩小 float 参数范围"""
        spec = ParameterSpec(
            name="temperature", distribution=ParameterType.FLOAT, low=0.0, high=1.0
        )

        narrowed = spec.narrow(center=0.5, scale=0.2)

        # 范围应缩小到 0.5 ± (1.0 * 0.2 / 2) = 0.5 ± 0.1 = [0.4, 0.6]
        assert narrowed.low == pytest.approx(0.4, abs=0.01)
        assert narrowed.high == pytest.approx(0.6, abs=0.01)
        assert narrowed.name == spec.name
        assert narrowed.distribution == spec.distribution

    def test_narrow_int_parameter(self):
        """测试缩小 int 参数范围"""
        spec = ParameterSpec(
            name="max_tokens", distribution=ParameterType.INT, low=0, high=1000
        )

        narrowed = spec.narrow(center=500, scale=0.2)

        # 范围应缩小到 500 ± (1000 * 0.2 / 2) = 500 ± 100 = [400, 600]
        assert narrowed.low == 400
        assert narrowed.high == 600

    def test_narrow_categorical_unchanged(self):
        """测试 categorical 参数不缩小"""
        spec = ParameterSpec(
            name="model",
            distribution=ParameterType.CATEGORICAL,
            choices=["a", "b", "c"],
        )

        narrowed = spec.narrow(center="b", scale=0.2)

        # categorical 参数不应改变
        assert narrowed.choices == spec.choices


class TestParameterSearchSpace:
    """测试 ParameterSearchSpace 类"""

    def test_create_search_space(self):
        """测试创建搜索空间"""
        space = ParameterSearchSpace(
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
                    low=100,
                    high=1000,
                ),
            ]
        )

        assert len(space.parameters) == 2
        assert space.parameters[0].name == "temperature"
        assert space.parameters[1].name == "max_tokens"

    def test_create_from_dict(self):
        """测试从字典创建搜索空间"""
        space = ParameterSearchSpace.model_validate(
            {
                "temperature": {"distribution": "float", "low": 0.0, "high": 1.0},
                "max_tokens": {"distribution": "int", "low": 100, "high": 1000},
            }
        )

        assert len(space.parameters) == 2
        param_names = {p.name for p in space.parameters}
        assert "temperature" in param_names
        assert "max_tokens" in param_names

    def test_duplicate_parameter_names(self):
        """测试重复参数名应失败"""
        with pytest.raises(ValueError, match="Duplicate parameter names"):
            ParameterSearchSpace(
                parameters=[
                    ParameterSpec(
                        name="temp",
                        distribution=ParameterType.FLOAT,
                        low=0.0,
                        high=1.0,
                    ),
                    ParameterSpec(
                        name="temp",
                        distribution=ParameterType.FLOAT,
                        low=0.5,
                        high=1.5,
                    ),
                ]
            )

    def test_empty_search_space(self):
        """测试空搜索空间应失败"""
        with pytest.raises(ValueError, match="Parameter search space cannot be empty"):
            ParameterSearchSpace(parameters=[])

    def test_suggest_all_parameters(self):
        """测试采样所有参数"""
        space = ParameterSearchSpace(
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
                    low=100,
                    high=1000,
                ),
            ]
        )

        study = create_study()
        trial = study.ask()
        values = space.suggest(trial)

        assert "temperature" in values
        assert "max_tokens" in values
        assert isinstance(values["temperature"], float)
        assert isinstance(values["max_tokens"], int)

    def test_apply_parameters_to_prompt(self):
        """测试将参数应用到 PromptConfig"""
        space = ParameterSearchSpace(
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
                    low=100,
                    high=1000,
                ),
            ]
        )

        prompt = PromptConfig(user="Hello")
        values = {"temperature": 0.7, "max_tokens": 500}

        new_prompt = space.apply(prompt, values)

        assert new_prompt.model_params is not None
        assert new_prompt.model_params["temperature"] == 0.7
        assert new_prompt.model_params["max_tokens"] == 500
        assert new_prompt.user == "Hello"

    def test_narrow_around_values(self):
        """测试在指定值周围缩小搜索空间"""
        space = ParameterSearchSpace(
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
                    low=0,
                    high=1000,
                ),
            ]
        )

        values = {"temperature": 0.5, "max_tokens": 500}
        narrowed = space.narrow_around(values, scale=0.2)

        # 检查 temperature 范围缩小
        temp_spec = next(p for p in narrowed.parameters if p.name == "temperature")
        assert temp_spec.low == pytest.approx(0.4, abs=0.01)
        assert temp_spec.high == pytest.approx(0.6, abs=0.01)

        # 检查 max_tokens 范围缩小
        tokens_spec = next(p for p in narrowed.parameters if p.name == "max_tokens")
        assert tokens_spec.low == 400
        assert tokens_spec.high == 600

    def test_describe_search_space(self):
        """测试描述搜索空间"""
        space = ParameterSearchSpace(
            parameters=[
                ParameterSpec(
                    name="temperature",
                    distribution=ParameterType.FLOAT,
                    low=0.0,
                    high=1.0,
                    scale="linear",
                ),
                ParameterSpec(
                    name="model",
                    distribution=ParameterType.CATEGORICAL,
                    choices=["a", "b"],
                ),
            ]
        )

        description = space.describe()

        assert "temperature" in description
        assert description["temperature"]["type"] == "float"
        assert description["temperature"]["min"] == 0.0
        assert description["temperature"]["max"] == 1.0
        assert description["temperature"]["scale"] == "linear"

        assert "model" in description
        assert description["model"]["type"] == "categorical"
        assert description["model"]["choices"] == ["a", "b"]
