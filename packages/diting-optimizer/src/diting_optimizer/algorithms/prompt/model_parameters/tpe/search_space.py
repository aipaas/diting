"""Parameter search space definitions.

Reference implementation based on Opik ParameterSpec and ParameterSearchSpace.
"""

from __future__ import annotations

import copy
import math
from typing import Any, Dict, List, Literal, Optional

from optuna.trial import Trial
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

from diting_optimizer.algorithms.prompt.model_parameters.tpe.types import (
    ParameterType,
)
from diting_optimizer.target.prompt_config import PromptConfig


class ParameterSpec(BaseModel):
    """Definition of a single parameter.

    Attributes:
        name: Parameter name
        description: Parameter description
        distribution: Parameter type (float/int/categorical)
        low: Minimum value (for float/int)
        high: Maximum value (for float/int)
        step: Step size (for discrete sampling)
        scale: Scaling type (linear/log)
        choices: List of choices (for categorical)
        target: Parameter application target (e.g., "model_params.temperature")
    """

    name: str = Field(description="Parameter name")
    description: Optional[str] = Field(
        default=None, description="Parameter description"
    )
    distribution: ParameterType = Field(description="Parameter type")
    low: Optional[float] = Field(default=None, description="Minimum value")
    high: Optional[float] = Field(default=None, description="Maximum value")
    step: Optional[float] = Field(default=None, description="Step size")
    scale: Literal["linear", "log"] = Field(
        default="linear", description="Scaling type"
    )
    choices: Optional[List[Any]] = Field(default=None, description="List of choices")
    target: Optional[str] = Field(
        default=None,
        description="Parameter application target (defaults to model_params.{name})",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
        from_attributes=True,
    )

    @field_validator("distribution", mode="before")
    @classmethod
    def validate_distribution(cls, v: Any) -> ParameterType:
        """Validate and convert parameter type."""
        if isinstance(v, ParameterType):
            return v
        if isinstance(v, str):
            return ParameterType(v)
        raise ValueError(f"Invalid parameter type: {v}")

    @model_validator(mode="after")
    def validate_spec(self) -> "ParameterSpec":
        """Validate the completeness of parameter definition."""
        if self.distribution in {ParameterType.FLOAT, ParameterType.INT}:
            if self.low is None or self.high is None:
                raise ValueError(f"{self.name}: float/int type requires min and max")
            if self.low >= self.high:
                raise ValueError(f"{self.name}: min must be less than max")
            if self.scale == "log" and (self.low <= 0 or self.high <= 0):
                raise ValueError(
                    f"{self.name}: log scaling requires positive boundaries"
                )

        elif self.distribution == ParameterType.CATEGORICAL:
            if not self.choices:
                raise ValueError(f"{self.name}: categorical type requires choices")

        return self

    def suggest(self, trial: Trial) -> Any:
        """Sample parameter values using Optuna trial.

        Args:
            trial: Optuna Trial object

        Returns:
            Sampled parameter value
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

        raise RuntimeError(f"Unsupported parameter type: {self.distribution}")

    def apply_to_prompt(self, prompt: PromptConfig, value: Any) -> None:
        """Apply sampled values to PromptConfig.

        Args:
            prompt: Prompt configuration object
            value: Sampled parameter value
        """
        # All parameters are uniformly managed in model_params
        target = self.target or f"model_params.{self.name}"

        if target.startswith("model_params."):
            param_name = target[len("model_params.") :]
            if prompt.model_params is None:
                prompt.model_params = {}
            prompt.model_params[param_name] = value
        else:
            # Default to putting in model_params
            if prompt.model_params is None:
                prompt.model_params = {}
            prompt.model_params[self.name] = value

    def narrow(self, center: Any, scale: float) -> "ParameterSpec":
        """Narrow search range around center value.

        Reference implementation based on Opik ParameterSpec.narrow() for local search.

        Args:
            center: Center value
            scale: Scaling factor (0.0-1.0)

        Returns:
            New ParameterSpec with narrowed range
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

            # Create new spec
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

        # Categorical parameters are not narrowed
        return self


class ParameterSearchSpace(BaseModel):
    """Parameter search space.

    Contains search space definitions for multiple parameters.

    Attributes:
        parameters: List of parameters
    """

    parameters: List[ParameterSpec] = Field(default_factory=list)

    model_config = {"extra": "forbid"}

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, data: Any) -> Any:
        """Normalize input format.

        Supports dictionary format: {"temp": {"type": "float", "min": 0, "max": 1}}
        """
        if isinstance(data, dict) and "parameters" not in data:
            # Convert dictionary to parameter list
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
        """Validate parameter name uniqueness."""
        names = [spec.name for spec in self.parameters]
        if len(names) != len(set(names)):
            duplicates = {name for name in names if names.count(name) > 1}
            raise ValueError(
                f"Duplicate parameter names: {', '.join(sorted(duplicates))}"
            )
        if not self.parameters:
            raise ValueError("Parameter search space cannot be empty")
        return self

    def suggest(self, trial: Trial) -> Dict[str, Any]:
        """Sample values for all parameters.

        Args:
            trial: Optuna Trial object

        Returns:
            Dictionary mapping parameter names to values
        """
        return {spec.name: spec.suggest(trial) for spec in self.parameters}

    def apply(
        self,
        prompt: PromptConfig,
        values: Dict[str, Any],
        *,
        base_model_params: Optional[Dict[str, Any]] = None,
    ) -> PromptConfig:
        """Apply parameter values to prompt configuration.

        Args:
            prompt: Base prompt configuration
            values: Parameter value dictionary
            base_model_params: Base model parameters (optional)

        Returns:
            New PromptConfig with applied parameters
        """
        prompt_copy = prompt.deep_copy()

        # Reset model_params
        if base_model_params is not None:
            prompt_copy.model_params = copy.deepcopy(base_model_params)

        # Apply all parameters
        for spec in self.parameters:
            if spec.name in values:
                spec.apply_to_prompt(prompt_copy, values[spec.name])

        return prompt_copy

    def narrow_around(
        self, values: Dict[str, Any], scale: float
    ) -> "ParameterSearchSpace":
        """Narrow search space around given values.

        Used for local search phase.

        Args:
            values: Center parameter values
            scale: Scaling factor

        Returns:
            New narrowed search space
        """
        narrowed_params = [
            spec.narrow(values.get(spec.name), scale) for spec in self.parameters
        ]
        return ParameterSearchSpace(parameters=narrowed_params)

    def describe(self) -> Dict[str, Dict[str, Any]]:
        """Return description of the search space.

        Returns:
            Dictionary mapping parameter names to description information
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
