"""覆盖所有情况的排列组合优化器

这个优化器通过枚举参数空间的所有可能组合来进行全面搜索。
适用于参数数量较少、每个参数可选值不多的场景。
"""

import copy
import logging
import itertools
from datetime import datetime
from typing import Any, Dict, List, Optional

from tqdm import tqdm

from diting_core.metrics.base_metric import BaseMetric
from diting_core.optimization.algorithms.parameter.search_space import (
    ParameterSearchSpace,
    ParameterType,
)
from diting_core.optimization.base_optimizer import BaseOptimizer
from diting_core.optimization.datasets.base_dataset import BaseDataset
from diting_core.optimization.optimization_result import OptimizationResult
from diting_core.optimization.target.base_config import BaseConfig
from diting_core.optimization.target.prompt_config import PromptConfig
from diting_core.optimization.utils.eval_task import evaluate_prompt

logger = logging.getLogger(__name__)


class CoverAllSituationsOptimizer(BaseOptimizer):
    """排列组合优化器，枚举所有可能的参数组合

    适用于：
    - 参数空间较小的情况
    - 需要全面探索所有可能性的场景
    - 确定性搜索（相同输入总是得到相同结果）
    """

    def __init__(
            self,
            *,
            num_eval_threads: int = 12,
            show_progress: bool = True,
            **kwargs: Any,
    ):
        """初始化排列组合优化器

        Args:
            num_eval_threads: 评估线程数
            show_progress: 是否显示进度条
            **kwargs: 基类参数
        """
        super().__init__(**kwargs)
        self.num_eval_threads = num_eval_threads
        self.show_progress = show_progress

    def _generate_parameter_combinations(
            self, parameter_space: ParameterSearchSpace
    ) -> List[Dict[str, Any]]:
        """生成所有可能的参数组合

        Args:
            parameter_space: 参数搜索空间

        Returns:
            参数组合列表，每个元素是参数字典
        """
        parameter_values = {}

        for spec in parameter_space.parameters:
            if spec.distribution == ParameterType.FLOAT:
                # 对于浮点数，根据范围和步长生成离散值
                if spec.low is None or spec.high is None:
                    continue

                if spec.step:
                    # 有步长的情况
                    values = []
                    current = spec.low
                    while current <= spec.high:
                        values.append(current)
                        current += spec.step
                    # 确保包含上限
                    if values and values[-1] < spec.high:
                        values.append(spec.high)
                else:
                    # 无步长的情况，使用边界值
                    values = [spec.low, spec.high]
                    # 添加中间值（如果范围足够大）
                    mid = (spec.low + spec.high) / 2
                    if mid not in values:
                        values.append(mid)
                    values.sort()

            elif spec.distribution == ParameterType.INT:
                # 对于整数，生成范围内的所有整数或按步长生成
                if spec.low is None or spec.high is None:
                    continue

                low, high = int(spec.low), int(spec.high)
                if spec.step:
                    step = int(spec.step)
                    values = list(range(low, high + 1, step))
                    if values and values[-1] < high:
                        values.append(high)
                else:
                    values = list(range(low, high + 1))

            elif spec.distribution == ParameterType.CATEGORICAL:
                # 分类参数，直接使用所有可选值
                values = list(spec.choices) if spec.choices else []

            else:
                logger.warning(f"未知的参数类型: {spec.distribution}，跳过参数 {spec.name}")
                continue

            if values:
                parameter_values[spec.name] = values

        # 计算所有组合
        combinations = []
        param_names = list(parameter_values.keys())
        param_value_lists = [parameter_values[name] for name in param_names]

        for combination in itertools.product(*param_value_lists):
            param_dict = dict(zip(param_names, combination))
            combinations.append(param_dict)

        logger.info(f"生成了 {len(combinations)} 种参数组合")
        return combinations

    async def _optimize(
            self,
            config: BaseConfig,
            dataset: BaseDataset,
            metric: BaseMetric,
            n_trials: int = 0,  # 对于排列组合优化器，n_trials 参数被忽略
            **kwargs: Any,
    ) -> OptimizationResult:
        """执行排列组合优化

        Args:
            config: 基础配置
            dataset: 数据集
            metric: 评估指标
            n_trials: 试验次数（在此优化器中忽略）
            **kwargs: 其他参数

        Returns:
            优化结果
        """
        # 验证配置类型
        if not isinstance(config, PromptConfig):
            raise ValueError(
                f"CoverAllSituationsOptimizer requires PromptConfig, got {type(config).__name__}"
            )

        prompt_config = config
        history: List[Dict[str, Any]] = []

        # 获取参数空间
        parameter_space = kwargs.get("parameter_space")
        if parameter_space is None:
            raise ValueError(
                "CoverAllSituationsOptimizer requires parameter_space argument. "
                "Example: optimizer.optimize_prompt(..., parameter_space={...})"
            )

        if not isinstance(parameter_space, ParameterSearchSpace):
            parameter_space = ParameterSearchSpace.model_validate(parameter_space)

        # 基线评估
        logger.info("执行基线评估...")
        baseline_score = await evaluate_prompt(
            prompt_config, dataset, metric, self.num_eval_threads
        )

        history.append(
            {
                "iteration": 0,
                "timestamp": datetime.utcnow().isoformat(),
                "parameters": {},
                "score": baseline_score,
                "model_params": copy.deepcopy(prompt_config.model_params or {}),
                "type": "baseline",
                "stage": "baseline",
            }
        )

        logger.info(f"基线得分: {baseline_score:.4f}")

        # 生成所有参数组合
        combinations = self._generate_parameter_combinations(parameter_space)

        if not combinations:
            logger.warning("没有生成任何参数组合，返回基线结果")
            return self._create_result(
                prompt_config=prompt_config,
                parameter_space=parameter_space,
                best_prompt=prompt_config,
                best_score=baseline_score,
                baseline_score=baseline_score,
                metric=metric,
                history=history,
                best_parameters={},
                total_combinations=0,
                evaluated_combinations=0,
            )

        # 评估所有组合
        logger.info(f"开始评估 {len(combinations)} 种参数组合...")
        best_score = baseline_score
        best_parameters: Dict[str, Any] = {}
        best_model_params = copy.deepcopy(prompt_config.model_params or {})
        evaluated_combinations = 0

        # 使用进度条
        combinations_iter = tqdm(
            combinations,
            desc="评估参数组合",
            disable=not self.show_progress
        )

        for i, parameters in enumerate(combinations_iter):
            try:
                # 应用参数到提示配置
                tuned_prompt = parameter_space.apply(
                    prompt_config,
                    parameters,
                    base_model_params=copy.deepcopy(prompt_config.model_params or {}),
                )

                # 异步评估
                score = await evaluate_prompt(
                    tuned_prompt, dataset, metric, self.num_eval_threads
                )

                # 更新最佳结果
                if score > best_score:
                    best_score = score
                    best_parameters = copy.deepcopy(parameters)
                    best_model_params = copy.deepcopy(tuned_prompt.model_params or {})

                # 记录历史
                history.append(
                    {
                        "iteration": i + 1,
                        "timestamp": datetime.utcnow().isoformat(),
                        "parameters": copy.deepcopy(parameters),
                        "score": float(score),
                        "model_params": copy.deepcopy(tuned_prompt.model_params or {}),
                        "type": "combination",
                        "stage": "full_search",
                    }
                )

                evaluated_combinations += 1

                # 更新进度条描述
                if self.show_progress:
                    combinations_iter.set_postfix(
                        best_score=f"{best_score:.4f}",
                        current_score=f"{score:.4f}",
                    )

            except Exception as e:
                logger.error(f"评估参数组合 {parameters} 时出错: {e}")
                continue

        # 构建最终的最佳提示配置
        if best_parameters:
            best_prompt = parameter_space.apply(
                prompt_config,
                best_parameters,
                base_model_params=copy.deepcopy(prompt_config.model_params or {}),
            )
        else:
            best_prompt = prompt_config

        logger.info(f"优化完成。最佳得分: {best_score:.4f} (基线: {baseline_score:.4f})")
        if best_parameters:
            logger.info(f"最佳参数: {best_parameters}")

        return self._create_result(
            prompt_config=prompt_config,
            parameter_space=parameter_space,
            best_prompt=best_prompt,
            best_score=best_score,
            baseline_score=baseline_score,
            metric=metric,
            history=history,
            best_parameters=best_parameters,
            total_combinations=len(combinations),
            evaluated_combinations=evaluated_combinations,
        )

    def _create_result(
            self,
            prompt_config: PromptConfig,
            parameter_space: ParameterSearchSpace,
            best_prompt: PromptConfig,
            best_score: float,
            baseline_score: float,
            metric: BaseMetric,
            history: List[Dict[str, Any]],
            best_parameters: Dict[str, Any],
            total_combinations: int,
            evaluated_combinations: int,
    ) -> OptimizationResult:
        """创建优化结果对象

        Args:
            prompt_config: 原始提示配置
            parameter_space: 参数空间
            best_prompt: 最佳提示配置
            best_score: 最佳得分
            baseline_score: 基线得分
            metric: 评估指标
            history: 优化历史
            best_parameters: 最佳参数
            total_combinations: 总组合数
            evaluated_combinations: 已评估组合数

        Returns:
            优化结果
        """
        # 计算参数重要性（基于历史数据）
        parameter_importance = self._calculate_parameter_importance(history)

        return OptimizationResult(
            optimizer_name=self.__class__.__name__,
            best_prompt=best_prompt,
            best_score=best_score,
            metric_name=metric.__class__.__name__,
            initial_prompt=prompt_config,
            initial_score=baseline_score,
            improvement=(best_score - baseline_score) / baseline_score
            if baseline_score != 0
            else 0.0,
            history=history,
            details={
                "optimized_parameters": best_parameters,
                "optimized_model_kwargs": copy.deepcopy(best_prompt.model_params or {}),
                "parameter_space": parameter_space.model_dump(),
                "total_combinations": total_combinations,
                "evaluated_combinations": evaluated_combinations,
                "parameter_importance": parameter_importance,
                "search_type": "exhaustive",
                "rounds": [
                    {
                        "iteration": entry["iteration"],
                        "parameters": entry["parameters"],
                        "score": entry["score"],
                        "stage": entry.get("stage", "full_search"),
                    }
                    for entry in history
                    if entry.get("type") != "baseline"
                ],
            },
            iterations=evaluated_combinations,
        )

    def _calculate_parameter_importance(
            self, history: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """基于历史数据计算参数重要性

        通过分析每个参数值变化对得分的影响来计算重要性。

        Args:
            history: 优化历史

        Returns:
            参数名到重要性得分的字典
        """
        if len(history) <= 1:
            return {}

        # 只使用组合评估的历史记录
        eval_history = [h for h in history if h.get("type") == "combination"]
        if not eval_history:
            return {}

        importance = {}
        param_names = set()

        # 收集所有参数名
        for entry in eval_history:
            param_names.update(entry["parameters"].keys())

        # 对每个参数计算重要性
        for param_name in param_names:
            param_values = []
            scores = []

            for entry in eval_history:
                if param_name in entry["parameters"]:
                    param_values.append(entry["parameters"][param_name])
                    scores.append(entry["score"])

            if len(param_values) < 2:
                continue

            # 简单的相关性计算：参数值变化与得分变化的关系
            try:
                # 使用参数值的标准差和得分的标准差来计算相对重要性
                if all(isinstance(v, (int, float)) for v in param_values):
                    # 数值参数：使用变异系数
                    import numpy as np
                    param_array = np.array(param_values)
                    score_array = np.array(scores)

                    if param_array.std() > 0 and score_array.std() > 0:
                        # 参数变化对得分的影响程度
                        importance[param_name] = float(
                            score_array.std() / param_array.std()
                        )
                    else:
                        importance[param_name] = 0.0
                else:
                    # 分类参数：使用不同值对应的平均得分差异
                    value_scores = {}
                    for val, score in zip(param_values, scores):
                        key = str(val)
                        if key not in value_scores:
                            value_scores[key] = []
                        value_scores[key].append(score)

                    if len(value_scores) > 1:
                        # 计算不同值之间的最大平均得分差异
                        avg_scores = [np.mean(scores) for scores in value_scores.values()]
                        importance[param_name] = float(np.std(avg_scores))
                    else:
                        importance[param_name] = 0.0

            except Exception:
                importance[param_name] = 0.0

        # 归一化重要性得分
        if importance:
            max_importance = max(importance.values())
            if max_importance > 0:
                importance = {k: v / max_importance for k, v in importance.items()}

        return importance

    @property
    def description(self) -> str:
        """返回优化器描述"""
        return "覆盖所有情况的排列组合优化器，通过枚举所有参数组合进行彻底搜索"