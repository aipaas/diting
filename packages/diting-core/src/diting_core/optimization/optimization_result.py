"""优化结果类

参考 Opik OptimizationResult 设计，保留核心字段和显示方法。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

from diting_core.callbacks.usage import Usage
from diting_core.optimization.infra.eval_task import ExperimentResult
from diting_core.optimization.target.base_config import BaseConfig
from diting_core.optimization.target.prompt_config import PromptConfig


def _format_config(config: Any) -> str:
    """
    格式化 config 字段，区分 PromptConfig 实例和 dict：
    - PromptConfig：提取 system/user/messages 核心提示信息
    - dict：提取 model_params 或关键键值对
    """
    if isinstance(config, PromptConfig):
        # 1. 处理 PromptConfig 实例：聚焦提示词内容
        parts = []
        # 系统提示
        if config.system:
            parts.append(f"system: {_truncate_text(config.system, 40)}")
        # 用户提示
        if config.user:
            parts.append(f"user: {_truncate_text(config.user, 40)}")
        # 消息列表（优先取前2条避免过长）
        if config.messages:
            msg_count = len(config.messages)
            # 取前2条核心消息
            for i, msg in enumerate(config.messages[:2]):
                role = msg.get("role", "unknown")
                content = _truncate_text(msg.get("content", ""), 40)
                parts.append(f"msg[{i}]: {role}={content}")
            # 标记剩余消息数
            if msg_count > 2:
                parts.append(f"msg[+{msg_count - 2} more]")
        # 模型参数（简化展示）
        if config.model_params:
            params = {
                k: v
                for k, v in config.model_params.items()
                if k in ["temperature", "max_tokens", "top_p"]
            }
            parts.append(f"model_params: {params}")
        # 无核心信息时兜底
        return "; ".join(parts) if parts else "Empty PromptConfig"

    elif isinstance(config, dict):
        # 2. 处理 dict 格式：优先展示 model_params 和关键字段
        if "model_params" in config:
            # 提取模型核心参数（温度、最大token等）
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
            # 非模型参数的dict：取前3个键值对
            key_items = list(config.items())[:3]
            items_str = ", ".join(
                [f"{k}={_truncate_text(str(v), 20)}" for k, v in key_items]
            )
            if len(config) > 3:
                items_str += ", +more"
            return items_str

    else:
        # 3. 其他类型：截断展示
        return _truncate_text(str(config), 60)


def _format_float(value: Any, digits: int = 6) -> str:
    """Format float values with specified precision."""
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _truncate_text(text: str, max_len: int = 60) -> str:
    """截断长文本，避免换行混乱"""
    if not isinstance(text, str) or len(text) <= max_len:
        return text
    return f"{text[:max_len]}..."


def _format_timestamp(ts_str: str) -> str:
    """ISO时间戳转为可读格式（如：2024-05-20 14:30:00）"""
    try:
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return ts.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return _truncate_text(ts_str, 18)


def _simplify_experiment_result(exp_result: Any) -> str:
    """
    简化 ExperimentResult 展示：
    - 提取核心信息：实验名、测试用例数、平均分数
    - 避免展开所有 TestResult 导致冗余
    """
    if not exp_result:
        return "N/A"

    # 处理 dict 格式（model_dump() 后的结果）
    if isinstance(exp_result, dict):
        exp_name = exp_result.get("experiment_name", "Unknown")
        test_results = exp_result.get("test_results", [])
        case_count = len(test_results)
        return f"Name: {exp_name}, Cases: {case_count}"

    # 处理 dataclass 实例格式
    elif isinstance(exp_result, ExperimentResult):
        case_count = len(exp_result.test_results)
        return f"Name: {exp_result.experiment_name or 'Unknown'}, Cases: {case_count}"

    # 兜底格式
    else:
        return _truncate_text(str(exp_result), 50)


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
        """计算改进幅度字符串（无颜色标记，适配纯文本）"""
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

    def _format_history_common(self, record: Dict[str, Any], idx: int) -> List[str]:
        """
        格式化 history 共性属性：
        iteration, timestamp, stage, config, score, experiment_result
        兼容子迭代（sub_iteration）字段，但不作为核心展示
        """
        # 1. 提取共性属性（默认值处理）
        iteration = record.get("iteration", idx + 1)
        sub_iter = record.get("sub_iteration")  # 兼容子迭代（非共性，可选展示）
        timestamp = _format_timestamp(record.get("timestamp", ""))
        stage = record.get("stage", "unknown")
        score = record.get("score", "N/A")
        score_str = _format_float(score)
        # 标记最佳分数轮次
        is_best = (
            "[BEST]"
            if isinstance(score, (int, float)) and score == self.best_score
            else ""
        )

        # 2. 简化 config 展示（取核心字段，避免大字典冗余）
        config = record.get("config", {})
        config_str = _format_config(config)

        # 3. 简化 experiment_result 展示（核心统计信息）
        exp_result = record.get("experiment_result", {})
        exp_str = _simplify_experiment_result(exp_result)

        # 4. 组装迭代号（含子迭代）
        iter_str = f"{iteration}.{sub_iter}" if sub_iter is not None else str(iteration)

        # 5. 构建输出行（分两行：核心信息 + 补充信息）
        line1 = f"  Iter {iter_str:4s} | Stage: {stage:10s} | Score: {score_str:8s} {is_best:6s} | Time: {timestamp}"
        line2 = f"         | Config: {config_str}"
        line3 = f"         | Exp Result: {exp_str}"

        return [line1, line2, line3]

    def __str__(self) -> str:
        """Provides a clean, well-formatted plain-text summary."""
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

        if self.history:
            output.extend(
                [
                    f"\n{sub_separator}",
                    "OPTIMIZATION HISTORY (Common Attributes)",
                    f"{sub_separator}",
                    "  Iter   | Stage       | Score       | Time                | Config / Exp Result",
                    "  --------------------------------------------------------------------------------",
                ]
            )
            # 遍历历史记录，统一格式化
            for idx, record in enumerate(self.history):
                output.extend(self._format_history_common(record, idx))

            # 3. 历史统计（基于共性的 score 字段）
            valid_scores = [
                r["score"]
                for r in self.history
                if isinstance(r.get("score"), (int, float))
            ]
            if valid_scores:
                avg_score = sum(valid_scores) / len(valid_scores)
                min_score = min(valid_scores)
                max_score = max(valid_scores)
                # 最佳分数对应的迭代号
                best_iter_idx = [
                    i
                    for i, r in enumerate(self.history)
                    if isinstance(r.get("score"), (int, float))
                    and r["score"] == self.best_score
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
