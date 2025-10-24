"""优化结果类

参考 Opik OptimizationResult 设计，保留核心字段和显示方法。
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

from diting_core.callbacks.usage import Usage
from diting_core.optimization.target.base_config import BaseConfig
from diting_core.optimization.target.prompt_config import PromptConfig


def _format_float(value: Any, digits: int = 6) -> str:
    """Format float values with specified precision."""
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


class OptimizationResult(BaseModel):
    """优化结果，参考 Opik OptimizationResult 设计

    核心字段：
        - 优化结果：best_prompt, best_score
        - 基线信息：initial_prompt, initial_score（用于计算改进）
        - 元数据：optimizer_name, metric_name
        - 历史：history
        - 统计：total_llm_calls, iterations

    Attributes:
        optimizer_name: 优化器名称
        best_config: 优化后的最佳配置
        best_score: 最佳性能分数
        metric_name: 评估指标名称
        initial_prompt: 初始配置（基线）
        initial_score: 初始性能分数（基线）
        improvement: 相对基线的改进幅度（百分比）
        history: 优化过程的详细历史记录
        details: 优化器特定的详细信息（如参数重要性、搜索范围等）
        total_llm_calls: LLM 总调用次数
        tool_calls: 工具调用次数
        iterations: 迭代次数
    """

    optimizer_name: str = Field(default="Optimizer", description="优化器名称")
    metric_name: str = Field(description="评估指标名称")
    best_config: BaseConfig = Field(description="优化后的最佳配置")
    best_score: float = Field(description="最佳性能分数")

    # 基线信息（参考 Opik）
    initial_prompt: Optional[BaseConfig] = Field(
        default=None, description="初始配置（基线）"
    )
    initial_score: Optional[float] = Field(
        default=None, description="初始性能分数（基线）"
    )

    improvement: float = Field(
        default=0.0, description="相对基线的改进幅度（0.0-1.0，如 0.15 表示 15%）"
    )

    history: List[Dict[str, Any]] = Field(
        default_factory=list, description="优化过程的详细历史记录"
    )

    # 详细信息（参考 Opik details 字段）
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="优化器特定的详细信息（参数重要性、搜索范围等）",
    )

    total_llm_calls: int = Field(default=0, description="LLM 总调用次数")
    total_embedding_calls: int = Field(default=0, description="embedding 总调用次数")
    total_usages: list[Usage] = Field(default=[], description="token总开销")
    tool_calls: Optional[int] = Field(default=None, description="工具调用次数")
    iterations: int = Field(default=0, description="迭代次数")

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    def _calculate_improvement_str(self) -> str:
        """Helper to calculate improvement percentage string."""
        initial_s = self.initial_score
        final_s = self.best_score

        # Check if initial score exists and is a number
        if not isinstance(initial_s, (int, float)):
            return "[dim]N/A (no initial score)[/dim]"

        # Proceed with calculation only if initial_s is valid
        if initial_s != 0:
            improvement_pct = (final_s - initial_s) / abs(initial_s)
            # Basic coloring for rich, plain for str
            color_start = ""
            color_end = ""
            if improvement_pct > 0:
                color_start, color_end = "[bold green]", "[/bold green]"
            elif improvement_pct < 0:
                color_start, color_end = "[bold red]", "[/bold red]"
            return f"{color_start}{improvement_pct:.2%}{color_end}"
        elif final_s > 0:
            return "[bold green]infinite[/bold green] (initial score was 0)"
        else:
            return "0.00% (no improvement from 0)"

    def __str__(self) -> str:
        """Provides a clean, well-formatted plain-text summary."""
        separator = "=" * 80
        rounds_ran = self.iterations
        initial_score = self.initial_score
        initial_score_str = (
            f"{initial_score:.4f}" if isinstance(initial_score, (int, float)) else "N/A"
        )
        final_score_str = f"{self.best_score:.4f}"
        improvement_str = (
            self._calculate_improvement_str()
            .replace("[bold green]", "")
            .replace("[/bold green]", "")
            .replace("[bold red]", "")
            .replace("[/bold red]", "")
            .replace("[dim]", "")
            .replace("[/dim]", "")
        )

        output = [
            f"\n{separator}",
            "OPTIMIZATION COMPLETE",
            f"{separator}",
            f"Optimizer:        {self.optimizer_name}",
            f"Metric Evaluated: {self.metric_name}",
            f"Initial Score:    {initial_score_str}",
            f"Final Best Score: {final_score_str}",
            f"Total Improvement:{improvement_str.rjust(max(0, 18 - len('Total Improvement:')))}",
            f"Rounds Completed: {rounds_ran}",
            f"LLM Calls:        {self.total_llm_calls}",
            f"Embedding Calls:  {self.total_embedding_calls}",
            f"Total Usages:     {self.total_usages}",
        ]

        if isinstance(self.best_config, PromptConfig):
            optimized_params = self.details.get("optimized_parameters") or {}
            parameter_importance = self.details.get("parameter_importance") or {}
            search_ranges = self.details.get("search_ranges") or {}
            precision = self.details.get("parameter_precision", 6)

            if optimized_params:

                def _format_range(desc: dict[str, Any]) -> str:
                    if "min" in desc and "max" in desc:
                        step_str = (
                            f", step={_format_float(desc['step'], precision)}"
                            if desc.get("step") is not None
                            else ""
                        )
                        return f"[{_format_float(desc['min'], precision)}, {_format_float(desc['max'], precision)}{step_str}]"
                    if desc.get("choices"):
                        return f"choices={desc['choices']}"
                    return str(desc)

                rows = []
                stage_order = [
                    record.get("stage")
                    for record in self.details.get("search_stages", [])
                    if record.get("stage") in search_ranges
                ]
                if not stage_order:
                    stage_order = sorted(search_ranges)

                for name in sorted(optimized_params):
                    contribution = parameter_importance.get(name)
                    stage_ranges = []
                    for stage in stage_order:
                        params = search_ranges.get(stage) or {}
                        if name in params:
                            stage_ranges.append(
                                f"{stage}: {_format_range(params[name])}"
                            )
                    if not stage_ranges:
                        for stage, params in search_ranges.items():
                            if name in params:
                                stage_ranges.append(
                                    f"{stage}: {_format_range(params[name])}"
                                )
                    joined_ranges = "\n".join(stage_ranges) if stage_ranges else "N/A"
                    rows.append(
                        {
                            "model_parameters": name,
                            "value": optimized_params[name],
                            "contribution": contribution,
                            "ranges": joined_ranges,
                        }
                    )

                if rows:
                    output.append("Parameter Summary:")
                    # Compute overall improvement fraction for gain calculation
                    total_improvement = None
                    if isinstance(self.initial_score, (int, float)) and isinstance(
                        self.best_score, (int, float)
                    ):
                        if self.initial_score != 0:
                            total_improvement = (
                                self.best_score - self.initial_score
                            ) / abs(self.initial_score)
                        else:
                            total_improvement = self.best_score
                    for row in rows:
                        value_str = _format_float(row["value"], precision)
                        contrib_val = row["contribution"]
                        if contrib_val is not None:
                            contrib_percent = contrib_val * 100
                            gain_str = ""
                            if total_improvement is not None:
                                gain_value = contrib_val * total_improvement * 100
                                gain_str = f" ({gain_value:+.2f}%)"
                            contrib_str = f"{contrib_percent:.1f}%{gain_str}"
                        else:
                            contrib_str = "N/A"
                        output.append(
                            f"- {row['model_parameters']}: value={value_str}, contribution={contrib_str}, ranges=\n  {row['ranges']}"
                        )

            try:
                final_prompt_display = "\n".join(
                    [
                        f"  {msg.get('role', 'unknown')}: {str(msg.get('content', ''))[:150]}..."
                        for msg in self.best_config.get_messages()
                    ]
                )
            except Exception:
                final_prompt_display = str(self.prompt)

            output.extend(
                [
                    "\nFINAL OPTIMIZED PROMPT / STRUCTURE:",
                    "--------------------------------------------------------------------------------",
                    f"{final_prompt_display}",
                    "--------------------------------------------------------------------------------",
                    f"{separator}",
                ]
            )

        return "\n".join(output)

    def display(self) -> None:
        """显示优化结果

        参考 Opik OptimizationResult.display()
        """
        print(self)

    def get_optimized_parameters(self) -> Dict[str, Any]:
        """提取优化后的参数值

        参考 Opik OptimizationResult.get_optimized_parameters()

        Returns:
            优化后的参数字典
        """
        return self.details.get("optimized_parameters", {})
