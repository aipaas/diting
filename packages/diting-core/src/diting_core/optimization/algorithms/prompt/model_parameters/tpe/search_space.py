"""参数搜索空间定义

参考 Opik ParameterSpec 和 ParameterSearchSpace 实现。
"""

import copy
import math
from typing import Any, Dict, List, Literal, Optional

from optuna.trial import Trial
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

from diting_core.optimization.algorithms.prompt.model_parameters.tpe.types import (
    ParameterType,
)
from diting_core.optimization.target.prompt_config import PromptConfig


class ParameterSpec(BaseModel):
    """单个参数的定义

    Attributes:
        name: 参数名称
        description: 参数描述
        distribution: 参数类型（float/int/categorical）
        low: 最小值（用于 float/int）
        high: 最大值（用于 float/int）
        step: 步长（用于离散采样）
        scale: 缩放类型（linear/log）
        choices: 可选值列表（用于 categorical）
        target: 参数应用目标（如 "model_params.temperature"）
    """

    name: str = Field(description="参数名称")
    description: Optional[str] = Field(default=None, description="参数描述")
    distribution: ParameterType = Field(description="参数类型")
    low: Optional[float] = Field(default=None, description="最小值")
    high: Optional[float] = Field(default=None, description="最大值")
    step: Optional[float] = Field(default=None, description="步长")
    scale: Literal["linear", "log"] = Field(default="linear", description="缩放类型")
    choices: Optional[List[Any]] = Field(default=None, description="可选值列表")
    target: Optional[str] = Field(
        default=None, description="参数应用目标（默认为 model_params.{name}）"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
        from_attributes=True,
    )

    @field_validator("distribution", mode="before")
    @classmethod
    def validate_distribution(cls, v: Any) -> ParameterType:
        """验证并转换参数类型"""
        if isinstance(v, ParameterType):
            return v
        if isinstance(v, str):
            return ParameterType(v)
        raise ValueError(f"无效的参数类型: {v}")

    @model_validator(mode="after")
    def validate_spec(self) -> "ParameterSpec":
        """验证参数定义的完整性"""
        if self.distribution in {ParameterType.FLOAT, ParameterType.INT}:
            if self.low is None or self.high is None:
                raise ValueError(f"{self.name}: float/int 类型需要 min 和 max")
            if self.low >= self.high:
                raise ValueError(f"{self.name}: min 必须小于 max")
            if self.scale == "log" and (self.low <= 0 or self.high <= 0):
                raise ValueError(f"{self.name}: log 缩放需要正数边界")

        elif self.distribution == ParameterType.CATEGORICAL:
            if not self.choices:
                raise ValueError(f"{self.name}: categorical 类型需要 choices")

        return self

    def suggest(self, trial: Trial) -> Any:
        """使用 Optuna trial 采样参数值

        Args:
            trial: Optuna Trial 对象

        Returns:
            采样的参数值
        """
        if self.distribution == ParameterType.FLOAT:
            assert self.low is not None and self.high is not None
            return trial.suggest_float(
                self.name,
                self.low,
                self.high,
                step=self.step,
                log=(self.scale == "log"),
            )
        elif self.distribution == ParameterType.INT:
            assert self.low is not None and self.high is not None
            return trial.suggest_int(
                self.name,
                int(self.low),
                int(self.high),
                step=int(self.step) if self.step else 1,
                log=(self.scale == "log"),
            )
        elif self.distribution == ParameterType.CATEGORICAL:
            assert self.choices is not None
            return trial.suggest_categorical(self.name, self.choices)

        raise RuntimeError(f"不支持的参数类型: {self.distribution}")

    def apply_to_prompt(self, prompt: PromptConfig, value: Any) -> None:
        """将采样值应用到 PromptConfig

        Args:
            prompt: 提示配置对象
            value: 采样的参数值
        """
        # 所有参数统一放入 model_params 中管理
        target = self.target or f"model_params.{self.name}"

        if target.startswith("model_params."):
            param_name = target[len("model_params.") :]
            if prompt.model_params is None:
                prompt.model_params = {}
            prompt.model_params[param_name] = value
        else:
            # 默认放入 model_params
            if prompt.model_params is None:
                prompt.model_params = {}
            prompt.model_params[self.name] = value

    def narrow(self, center: Any, scale: float) -> "ParameterSpec":
        """在中心值周围缩小搜索范围

        参考 Opik ParameterSpec.narrow() 实现，用于局部搜索。

        Args:
            center: 中心值
            scale: 缩放因子（0.0-1.0）

        Returns:
            缩小范围后的新 ParameterSpec
        """
        if center is None or scale <= 0:
            return self

        if self.distribution in {ParameterType.FLOAT, ParameterType.INT}:
            if self.low is None or self.high is None:
                return self

            span = float(self.high) - float(self.low)
            half_window = span * scale / 2

            center_val = float(center)
            new_low = max(float(self.low), center_val - half_window)
            new_high = min(float(self.high), center_val + half_window)

            if self.distribution == ParameterType.INT:
                new_low = math.floor(new_low)
                new_high = math.ceil(new_high)
                if new_low == new_high:
                    new_high = min(int(self.high), new_low + 1)

            if new_low >= new_high:
                return self

            # 创建新的 spec
            return ParameterSpec(
                name=self.name,
                description=self.description,
                distribution=self.distribution,
                low=new_low,
                high=new_high,
                step=self.step,
                scale=self.scale,
                target=self.target,
            )

        # 分类参数不缩小
        return self


class ParameterSearchSpace(BaseModel):
    """参数搜索空间

    包含多个参数的搜索空间定义。

    Attributes:
        parameters: 参数列表
    """

    parameters: List[ParameterSpec] = Field(default_factory=list)

    model_config = {"extra": "forbid"}

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, data: Any) -> Any:
        """标准化输入格式

        支持字典格式：{"temp": {"type": "float", "min": 0, "max": 1}}
        """
        if isinstance(data, dict) and "parameters" not in data:
            # 将字典转换为参数列表
            parameters = []
            for name, spec_dict in data.items():
                if isinstance(spec_dict, dict):
                    spec_dict = dict(spec_dict)
                    spec_dict.setdefault("name", name)
                    parameters.append(spec_dict)
            return {"parameters": parameters}
        return data

    @model_validator(mode="after")
    def validate_unique_names(self) -> "ParameterSearchSpace":
        """验证参数名称唯一性"""
        names = [spec.name for spec in self.parameters]
        if len(names) != len(set(names)):
            duplicates = {name for name in names if names.count(name) > 1}
            raise ValueError(f"参数名称重复: {', '.join(sorted(duplicates))}")
        if not self.parameters:
            raise ValueError("参数搜索空间不能为空")
        return self

    def suggest(self, trial: Trial) -> Dict[str, Any]:
        """采样所有参数的值

        Args:
            trial: Optuna Trial 对象

        Returns:
            参数名到值的字典
        """
        return {spec.name: spec.suggest(trial) for spec in self.parameters}

    def apply(
        self,
        prompt: PromptConfig,
        values: Dict[str, Any],
        *,
        base_model_params: Optional[Dict[str, Any]] = None,
    ) -> PromptConfig:
        """将参数值应用到提示配置

        Args:
            prompt: 基础提示配置
            values: 参数值字典
            base_model_params: 基础模型参数（可选）

        Returns:
            应用参数后的新 PromptConfig
        """
        prompt_copy = prompt.deep_copy()

        # 重置 model_params
        if base_model_params is not None:
            prompt_copy.model_params = copy.deepcopy(base_model_params)

        # 应用所有参数
        for spec in self.parameters:
            if spec.name in values:
                spec.apply_to_prompt(prompt_copy, values[spec.name])

        return prompt_copy

    def narrow_around(
        self, values: Dict[str, Any], scale: float
    ) -> "ParameterSearchSpace":
        """在给定值周围缩小搜索空间

        用于局部搜索阶段。

        Args:
            values: 中心参数值
            scale: 缩放因子

        Returns:
            缩小后的新搜索空间
        """
        narrowed_params = [
            spec.narrow(values.get(spec.name), scale) for spec in self.parameters
        ]
        return ParameterSearchSpace(parameters=narrowed_params)

    def describe(self) -> Dict[str, Dict[str, Any]]:
        """返回搜索空间的描述

        Returns:
            参数名到描述信息的字典
        """
        summary: Dict[str, Dict[str, Any]] = {}
        for spec in self.parameters:
            entry: Dict[str, Any] = {"type": spec.distribution.value}
            if spec.distribution in {ParameterType.FLOAT, ParameterType.INT}:
                entry["min"] = spec.low
                entry["max"] = spec.high
                if spec.step:
                    entry["step"] = spec.step
                entry["scale"] = spec.scale
            else:
                entry["choices"] = list(spec.choices) if spec.choices else []
            summary[spec.name] = entry
        return summary
