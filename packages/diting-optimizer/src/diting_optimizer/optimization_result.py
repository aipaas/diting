"""Optimization result classes.

Reference design from Opik OptimizationResult, preserving core fields and display methods.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

from diting_core.callbacks.usage import Usage
from diting_optimizer.infra.eval_task import ExperimentResult
from diting_optimizer.target.base_config import BaseConfig
from diting_optimizer.target.prompt_config import PromptConfig


def _format_config(config: Any) -> str:
    """Format config field, distinguishing between PromptConfig instances and dict.

    For PromptConfig: Extract core prompt information (system/user/messages)
    For dict: Extract model_params or key-value pairs

    Args:
        config: Configuration object to format

    Returns:
        Formatted string representation of the config
    """
    if isinstance(config, PromptConfig):
        # 1. Handle PromptConfig instance: Focus on prompt content
        parts = []
        # System prompt
        if config.system:
            parts.append(f"system: {_truncate_text(config.system, 40)}")
        # User prompt
        if config.user:
            parts.append(f"user: {_truncate_text(config.user, 40)}")
        # Message list (take first 2 to avoid being too long)
        if config.messages:
            msg_count = len(config.messages)
            # Take first 2 core messages
            for i, msg in enumerate(config.messages[:2]):
                role = msg.get("role", "unknown")
                content = _truncate_text(msg.get("content", ""), 40)
                parts.append(f"msg[{i}]: {role}={content}")
            # Mark remaining message count
            if msg_count > 2:
                parts.append(f"msg[+{msg_count - 2} more]")
        # Model parameters (simplified display)
        if config.model_params:
            params = {
                k: v
                for k, v in config.model_params.items()
                if k in ["temperature", "max_tokens", "top_p"]
            }
            parts.append(f"model_params: {params}")
        # Fallback when no core info
        return "; ".join(parts) if parts else "Empty PromptConfig"

    elif isinstance(config, dict):
        # 2. Handle dict format: Prioritize displaying model_params and key fields
        if "model_params" in config:
            # Extract core model parameters (temperature, max_tokens, etc.)
            params = config["model_params"]
            if isinstance(params, dict):
                key_params = {
                    k: v
                    for k, v in params.items()
                    if k in ["temperature", "max_tokens", "top_p"]
                }
                return f"model_params: {key_params}; ..."
            else:
                return _truncate_text(f"model_params: {params}", 60)
        else:
            # Non-model parameters dict: Take first 3 key-value pairs
            key_items = list(config.items())[:3]
            items_str = ", ".join(
                [f"{k}={_truncate_text(str(v), 20)}" for k, v in key_items]
            )
            if len(config) > 3:
                items_str += ", +more"
            return items_str

    else:
        # 3. Other types: Truncate display
        return _truncate_text(str(config), 60)


def _format_config_for_table(config: Any) -> str:
    """Format config for table display, removing newlines and special characters.

    Args:
        config: Configuration object to format

    Returns:
        Table-friendly string representation of the config
    """
    if isinstance(config, PromptConfig):
        # For PromptConfig, create a compact representation
        info_parts = []

        if config.system:
            # Take first 30 characters, replace newlines
            system_text = config.system.replace("\n", " ").strip()
            info_parts.append(f"S: {_truncate_text(system_text, 30)}")

        if config.user:
            # Take first 30 characters, replace newlines
            user_text = config.user.replace("\n", " ").strip()
            info_parts.append(f"U: {_truncate_text(user_text, 30)}")

        if config.messages and len(config.messages) > 0:
            # Count messages by role
            role_counts = {}
            for msg in config.messages[:5]:  # Only check first 5
                role = msg.get("role", "unknown")
                role_counts[role] = role_counts.get(role, 0) + 1
            if len(config.messages) > 5:
                role_counts["..."] = len(config.messages) - 5

            msg_summary = ", ".join(
                [f"{role}({count})" for role, count in role_counts.items()]
            )
            info_parts.append(f"M: {msg_summary}")

        if config.model_params:
            # Show only key params
            key_params = {
                k: v
                for k, v in config.model_params.items()
                if k in ["temperature", "max_tokens", "top_p"]
            }
            if key_params:
                info_parts.append(f"P: {key_params}")

        return " | ".join(info_parts) if info_parts else "PromptConfig"

    # Handle other config types
    config_str = _format_config(config)
    # Replace newlines and pipe characters which break tables
    return config_str.replace("\n", " ").replace("|", ";")


def _format_config_for_json(config: Any) -> Dict[str, Any]:
    """Format config for JSON output, ensuring proper serialization.

    Args:
        config: Configuration object to format

    Returns:
        Dictionary representation suitable for JSON serialization
    """
    if isinstance(config, PromptConfig):
        # Use model_dump for pydantic models
        return config.model_dump(exclude_none=True)
    elif isinstance(config, dict):
        return config
    else:
        # For other objects, try to convert to dict or return string representation
        try:
            if hasattr(config, "model_dump"):
                return config.model_dump(exclude_none=True)
            elif hasattr(config, "__dict__"):
                return config.__dict__
            else:
                return {"value": str(config)}
        except Exception:
            return {"value": str(config)}


def _format_float(value: Any, digits: int = 6) -> str:
    """Format float values with specified precision.

    Args:
        value: Value to format
        digits: Number of decimal places

    Returns:
        Formatted string representation of the float value
    """
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _truncate_text(text: str, max_len: int = 60) -> str:
    """Truncate long text to avoid line wrapping issues.

    Args:
        text: Text to truncate
        max_len: Maximum length before truncation

    Returns:
        Truncated text with ellipsis if needed
    """
    if not isinstance(text, str) or len(text) <= max_len:
        return text
    return f"{text[:max_len]}..."


def _format_timestamp(ts_str: str) -> str:
    """Convert ISO timestamp to readable format (e.g., 2024-05-20 14:30:00).

    Args:
        ts_str: ISO format timestamp string

    Returns:
        Readable timestamp string
    """
    try:
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return ts.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return _truncate_text(ts_str, 18)


def _simplify_experiment_result(exp_result: Any) -> str:
    """Simplify ExperimentResult display for brevity.

    Extracts core information: experiment name, test case count, average score.
    Avoids expanding all TestResult to prevent redundancy.

    Args:
        exp_result: Experiment result to simplify

    Returns:
        Simplified string representation of the experiment result
    """
    if not exp_result:
        return "N/A"

    # Handle dict format (result from model_dump())
    if isinstance(exp_result, dict):
        exp_name = exp_result.get("experiment_name", "Unknown")
        test_results = exp_result.get("test_results", [])
        case_count = len(test_results)
        return f"Name: {exp_name}, Cases: {case_count}"

    # Handle dataclass instance format
    elif isinstance(exp_result, ExperimentResult):
        case_count = len(exp_result.test_results)
        return f"Name: {exp_result.experiment_name or 'Unknown'}, Cases: {case_count}"

    # Fallback format
    else:
        return _truncate_text(str(exp_result), 50)


class HistoryRecord(BaseModel):
    """Single optimization record structure.

    Represents one iteration in the optimization process with its configuration,
    results, and metadata.
    """

    iteration: int = Field(..., description="Iteration number, starting from 0")
    stage: str = Field(..., description="Optimization stage name")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    score: float = Field(..., description="Score achieved in this iteration")
    optimizer_name: str = Field(..., description="Name of the optimizer")
    metric_name: str = Field(..., description="Name of the evaluation metric")
    config: BaseConfig = Field(
        ..., description="Configuration used in this optimization"
    )
    experiment_result: ExperimentResult = Field(..., description="Experiment results")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Optimizer-specific additional data"
    )

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    def to_json(self) -> str:
        """Serialize to JSON string with datetime ISO format.

        Returns:
            JSON string representation of the record
        """
        return self.model_dump_json(exclude_none=True)


class OptimizationResult(BaseModel):
    """Optimization results, designed with reference to Opik OptimizationResult.

    Core fields:
        - Optimization results: best_config, best_score
        - Baseline information: initial_prompt, initial_score (for improvement calculation)
        - Metadata: optimizer_name, metric_name
        - History: histories
        - Statistics: total_llm_calls, iterations

    Attributes:
        optimizer_name: Name of the optimizer
        best_config: Best optimized configuration
        best_score: Best performance score achieved
        metric_name: Name of the evaluation metric
        initial_config: Initial configuration (baseline)
        initial_score: Initial performance score (baseline)
        improvement: Relative improvement from baseline (percentage)
        histories: Detailed history records of the optimization process
        details: Optimizer-specific details (parameter importance, search ranges, etc.)
        total_llm_calls: Total number of LLM calls
        tool_calls: Number of tool calls
        iterations: Number of iterations completed
    """

    optimizer_name: str = Field(
        default="Optimizer", description="Name of the optimizer"
    )
    metric_name: str = Field(description="Name of the evaluation metric")
    best_config: BaseConfig = Field(description="Best optimized configuration")
    best_score: float = Field(description="Best performance score achieved")

    initial_score_on_test: Optional[float] = Field(
        default=None, description="Initial performance score (testset)"
    )

    final_score_on_test: Optional[float] = Field(
        default=None, description="Final performance score (testset)"
    )

    # Baseline information (reference Opik)
    initial_config: Optional[BaseConfig] = Field(
        default=None, description="Initial configuration (baseline)"
    )
    initial_score: Optional[float] = Field(
        default=None, description="Initial performance score (baseline)"
    )

    improvement: float = Field(
        default=0.0,
        description="Relative improvement from baseline (0.0-1.0, e.g., 0.15 represents 15%)",
    )

    histories: List[HistoryRecord] = Field(
        default_factory=list,
        description="Detailed history records of the optimization process",
    )

    # Detailed information (reference Opik details field)
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optimizer-specific details (parameter importance, search ranges, etc.)",
    )

    total_llm_calls: int = Field(default=0, description="Total number of LLM calls")
    total_embedding_calls: int = Field(
        default=0, description="Total number of embedding calls"
    )
    total_usages: list[Usage] = Field(
        default=[], description="Total token usage records"
    )
    tool_calls: Optional[int] = Field(default=None, description="Number of tool calls")
    iterations: int = Field(default=0, description="Number of iterations completed")

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    def _calculate_improvement_str(self) -> str:
        """Calculate improvement string (plain text, no color markers).

        Returns:
            String representation of the improvement percentage
        """
        initial_s = self.initial_score
        final_s = self.best_score

        if not isinstance(initial_s, (int, float)):
            return "N/A (no initial score)"

        if initial_s != 0:
            improvement_pct = (final_s - initial_s) / abs(initial_s)
            return f"{improvement_pct:.2%}"
        elif final_s > 0:
            return "infinite (initial score was 0)"
        else:
            return "0.00% (no improvement from 0)"

    def _format_history_common(self, record: HistoryRecord) -> List[str]:
        """Format common attributes of history records.

        Formats: iteration, timestamp, stage, config, score, experiment_result
        Compatible with sub_iteration field but not as core display.

        Args:
            record: History record to format

        Returns:
            List of formatted strings representing the record
        """
        # 1. Extract common attributes (handle default values)
        iteration = record.iteration
        sub_iter = record.metadata.get(
            "sub_iteration"
        )  # Compatible with sub-iteration (non-common, optional display)
        timestamp = _format_timestamp(record.timestamp.isoformat())
        stage = record.stage
        score = record.score
        score_str = _format_float(score)
        # Mark best score round
        is_best = "[BEST]" if score == self.best_score else ""

        # 2. Simplify config display (take core fields, avoid large dictionary redundancy)
        config = record.config
        config_str = _format_config(config)

        # 3. Simplify experiment_result display (core statistical information)
        exp_result = record.experiment_result
        exp_str = _simplify_experiment_result(exp_result)

        # 4. Assemble iteration number (including sub-iteration)
        iter_str = f"{iteration}.{sub_iter}" if sub_iter is not None else str(iteration)

        # 5. Build output lines (two lines: core information + supplementary information)
        line1 = f"  Iter {iter_str:4s} | Stage: {stage:10s} | Score: {score_str:8s} {is_best:6s} | Time: {timestamp}"
        line2 = f"         | Config: {config_str}"
        line3 = f"         | Exp Result: {exp_str}"

        return [line1, line2, line3]

    def __str__(self) -> str:
        """Provides a clean, well-formatted plain-text summary.

        Returns:
            Formatted string representation of the optimization result
        """
        separator = "=" * 80
        sub_separator = "-" * 80
        rounds_ran = self.iterations
        initial_score_str = (
            _format_float(self.initial_score)
            if isinstance(self.initial_score, (int, float))
            else "N/A"
        )
        final_score_str = _format_float(self.best_score)
        improvement_str = self._calculate_improvement_str()
        total_tokens = (
            sum(u.total_tokens for u in self.total_usages) if self.total_usages else 0
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
            f"Total Usages:     {len(self.total_usages)} records ({total_tokens} tokens)",
        ]

        if self.histories:
            output.extend(
                [
                    f"\n{sub_separator}",
                    "OPTIMIZATION HISTORY (Common Attributes)",
                    f"{sub_separator}",
                    "  Iter   | Stage       | Score       | Time                | Config / Exp Result",
                    "  --------------------------------------------------------------------------------",
                ]
            )
            # Iterate through history records with unified formatting
            for record in self.histories:
                output.extend(self._format_history_common(record))

            # 3. History statistics (based on common score field)
            valid_scores = [r.score for r in self.histories]
            if valid_scores:
                avg_score = sum(valid_scores) / len(valid_scores)
                min_score = min(valid_scores)
                max_score = max(valid_scores)
                # Iteration number corresponding to best score
                best_iter_idx = [
                    i
                    for i, r in enumerate(self.histories)
                    if r.score == self.best_score
                ]
                best_iter = best_iter_idx[0] + 1 if best_iter_idx else "N/A"

                output.extend(
                    [
                        "  --------------------------------------------------------------------------------",
                        f"  History Stats: Avg Score={_format_float(avg_score)}, Min={_format_float(min_score)}, Max={_format_float(max_score)}",
                        f"  Best Score Iteration: {best_iter}",
                    ]
                )

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
        """Display optimization results.

        Reference Opik OptimizationResult.display()
        """
        print(self)

    def get_optimized_parameters(self) -> Dict[str, Any]:
        """Extract optimized parameter values.

        Reference Opik OptimizationResult.get_optimized_parameters()

        Returns:
            Dictionary of optimized parameters
        """
        return self.details.get("optimized_parameters", {})

    def to_json(self, file_path: Optional[str] = None) -> str:
        """将优化结果包括 histories 完整序列化为 JSON 格式。

        Args:
            file_path: 可选的文件路径，如果提供则将 JSON 写入文件

        Returns:
            JSON 字符串格式的完整优化结果
        """
        import json

        # 手动构建字典以确保正确的序列化
        data = {
            "optimizer_name": self.optimizer_name,
            "metric_name": self.metric_name,
            "best_config": _format_config_for_json(self.best_config),
            "best_score": self.best_score,
            "initial_config": _format_config_for_json(self.initial_config)
            if self.initial_config
            else None,
            "initial_score": self.initial_score,
            "improvement": self.improvement,
            "histories": [
                {
                    "iteration": h.iteration,
                    "stage": h.stage,
                    "timestamp": h.timestamp.isoformat() if h.timestamp else None,
                    "score": h.score,
                    "optimizer_name": h.optimizer_name,
                    "metric_name": h.metric_name,
                    "config": _format_config_for_json(h.config),
                    "experiment_result": h.experiment_result.model_dump(
                        exclude_none=True
                    )
                    if h.experiment_result
                    else None,
                    "metadata": h.metadata,
                }
                for h in self.histories
            ],
            "details": self.details,
            "total_llm_calls": self.total_llm_calls,
            "total_embedding_calls": self.total_embedding_calls,
            "total_usages": [
                usage.model_dump(exclude_none=True) for usage in self.total_usages
            ]
            if self.total_usages
            else [],
            "tool_calls": self.tool_calls,
            "iterations": self.iterations,
        }

        # 移除 None 值
        data = {k: v for k, v in data.items() if v is not None and v != [] and v != {}}

        json_str = json.dumps(data, indent=2, ensure_ascii=False, default=str)

        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(json_str)

        return json_str

    def to_markdown(self, file_path: Optional[str] = None) -> str:
        """将优化结果包括 histories 转换为 Markdown 格式以便展示和文档化。

        Args:
            file_path: 可选的文件路径，如果提供则将 Markdown 写入文件

        Returns:
            Markdown 格式的优化结果字符串
        """
        import json

        lines = [
            "# 优化结果报告",
            "",
            "## 基本信息",
            "",
            f"- **优化器**: {self.optimizer_name}",
            f"- **评估指标**: {self.metric_name}",
            f"- **迭代次数**: {self.iterations}",
            f"- **LLM 调用次数**: {self.total_llm_calls}",
            f"- **Embedding 调用次数**: {self.total_embedding_calls}",
        ]

        # Token 使用统计
        if self.total_usages:
            total_tokens = sum(u.total_tokens for u in self.total_usages)
            total_input_tokens = sum(u.prompt_tokens for u in self.total_usages)
            total_output_tokens = sum(u.completion_tokens for u in self.total_usages)
            lines.append(f"- **总 Token 数**: {total_tokens:,}")
            lines.append(f"  - 输入 Token: {total_input_tokens:,}")
            lines.append(f"  - 输出 Token: {total_output_tokens:,}")

        lines.append("")

        # 分数信息
        lines.append("## 性能指标")
        lines.append("")

        initial_score_str = _format_float(self.initial_score)
        final_score_str = _format_float(self.best_score)
        improvement_str = self._calculate_improvement_str()

        initial_score_on_test_str = _format_float(self.initial_score_on_test)
        final_score_on_test_str = _format_float(self.final_score_on_test)
        lines.append(f"- **测试集初始分数**: {initial_score_on_test_str}")
        lines.append(f"- **测试集最终分数**: {final_score_on_test_str}")
        lines.append("训练集：")
        lines.append(f"- **初始分数**: {initial_score_str}")
        lines.append(f"- **最佳分数**: {final_score_str}")
        lines.append(f"- **改进幅度**: {improvement_str}")
        lines.append("")

        # 最佳配置
        lines.append("## 最佳配置")
        lines.append("")

        if isinstance(self.best_config, PromptConfig):
            lines.append("### 提示配置")
            lines.append("")

            if self.best_config.system:
                lines.append("**系统提示**:")
                lines.append("```")
                lines.append(self.best_config.system)
                lines.append("```")
                lines.append("")

            if self.best_config.user:
                lines.append("**用户提示**:")
                lines.append("```")
                lines.append(self.best_config.user)
                lines.append("```")
                lines.append("")

            if self.best_config.messages:
                lines.append("**消息列表**:")
                for i, msg in enumerate(self.best_config.messages):
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    lines.append(f"- **消息 {i + 1} ({role})**:")
                    lines.append("```")
                    lines.append(str(content))
                    lines.append("```")
                    lines.append("")

            if self.best_config.model_params:
                lines.append("**模型参数**:")
                for key, value in self.best_config.model_params.items():
                    lines.append(f"- {key}: {value}")
                lines.append("")
        else:
            lines.append("```json")
            lines.append(self.best_config.model_dump_json(indent=2, exclude_none=True))
            lines.append("```")
            lines.append("")

        # 优化历史
        if self.histories:
            lines.append("## 优化历史")
            lines.append("")
            lines.append("| 迭代 | 阶段 | 分数 | 时间戳 | 优化器 | 配置摘要 |")
            lines.append("|------|------|------|--------|--------|----------|")

            for record in self.histories:
                iteration = record.iteration
                sub_iter = record.metadata.get("sub_iteration")
                iter_str = (
                    f"{iteration}.{sub_iter}"
                    if sub_iter is not None
                    else str(iteration)
                )

                stage = record.stage
                score = _format_float(record.score)
                timestamp = _format_timestamp(record.timestamp.isoformat())
                optimizer = record.optimizer_name
                config_summary = _truncate_text(
                    _format_config_for_table(record.config), 50
                )

                # 标记最佳分数
                if record.score == self.best_score:
                    score += " ⭐"

                lines.append(
                    f"| {iter_str} | {stage} | {score} | {timestamp} | {optimizer} | {config_summary} |"
                )

            lines.append("")

            # 历史统计
            valid_scores = [r.score for r in self.histories]
            if valid_scores:
                avg_score = sum(valid_scores) / len(valid_scores)
                min_score = min(valid_scores)
                max_score = max(valid_scores)

                lines.append("### 历史统计")
                lines.append("")
                lines.append(f"- **平均分数**: {_format_float(avg_score)}")
                lines.append(f"- **最低分数**: {_format_float(min_score)}")
                lines.append(f"- **最高分数**: {_format_float(max_score)}")
                lines.append("")

        # 参数重要性分析（如果有）
        if isinstance(self.best_config, PromptConfig) and self.details:
            optimized_params = self.details.get("optimized_parameters", {})
            parameter_importance = self.details.get("parameter_importance", {})

            if optimized_params and parameter_importance:
                lines.append("## 参数重要性分析")
                lines.append("")
                lines.append("| 参数 | 优化值 | 重要性 | 贡献度 |")
                lines.append("|------|--------|--------|--------|")

                # 计算总改进
                total_improvement = None
                if isinstance(self.initial_score, (int, float)) and isinstance(
                    self.best_score, (int, float)
                ):
                    if self.initial_score != 0:
                        total_improvement = (
                            self.best_score - self.initial_score
                        ) / abs(self.initial_score)

                for param_name in sorted(optimized_params.keys()):
                    value = optimized_params[param_name]
                    importance = parameter_importance.get(param_name)

                    if importance is not None:
                        importance_percent = importance * 100
                        gain_str = ""
                        if total_improvement is not None:
                            gain_value = importance * total_improvement * 100
                            gain_str = f" ({gain_value:+.2f}%)"
                        contribution_str = f"{importance_percent:.1f}%{gain_str}"
                    else:
                        contribution_str = "N/A"

                    lines.append(
                        f"| {param_name} | {_format_float(value)} | {_format_float(importance) if importance is not None else 'N/A'} | {contribution_str} |"
                    )

                lines.append("")

        # 详细信息
        if self.details:
            lines.append("## 详细信息")
            lines.append("")
            lines.append("```json")
            import json

            lines.append(
                json.dumps(self.details, indent=2, ensure_ascii=False, default=str)
            )
            lines.append("```")
            lines.append("")

        # 完整历史记录（JSON格式）
        if self.histories:
            lines.append("## 完整历史记录")
            lines.append("")
            lines.append("```json")
            histories_data = []
            for record in self.histories:
                record_dict = record.model_dump(exclude_none=True)
                # Ensure config is properly serialized
                if "config" in record_dict and record_dict["config"] is not None:
                    record_dict["config"] = _format_config_for_json(record.config)
                histories_data.append(record_dict)
            lines.append(
                json.dumps(histories_data, indent=2, ensure_ascii=False, default=str)
            )
            lines.append("```")
            lines.append("")

        lines.append("---")
        lines.append(
            f"*报告生成时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*"
        )

        markdown_str = "\n".join(lines)

        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(markdown_str)

        return markdown_str
