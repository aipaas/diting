#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from typing import List, Optional, Any
import logging

from diting_core.metrics.base_metric import BaseMetric, MetricValue
from diting_core.cases.llm_case import LLMCase
from diting_core.callbacks.base import Callbacks


# 创建日志记录器
logger = logging.getLogger("diting_core.metrics.composite")


@dataclass
class CompositeMetric(BaseMetric):
    """
    复合指标类，支持组合多个基础指标进行评估
    """

    metrics: List[BaseMetric] = field(default_factory=list)
    weights: List[float] = field(default_factory=list)
    _required_params: List = field(default_factory=list)

    def __post_init__(self):
        """
        初始化复合指标
        """
        if not self.weights:
            # 默认等权重
            self.weights = [1.0 / len(self.metrics)] * len(self.metrics) if self.metrics else []
        else:
            if len(self.weights) != len(self.metrics):
                raise ValueError("权重数量必须与指标数量相同")
            # 归一化权重
            total_weight = sum(self.weights)
            self.weights = [w / total_weight for w in self.weights]

        # 合并所有基础指标的必需参数
        all_required_params = set()
        for metric in self.metrics:
            all_required_params.update(metric._required_params)
        self._required_params = list(all_required_params)

    async def _compute(
        self,
        test_case: LLMCase,
        *args: Any,
        callbacks: Optional[Callbacks] = None,
        **kwargs: Any,
    ) -> MetricValue:
        """
        计算复合指标得分
        
        Args:
            test_case: 测试用例
            callbacks: 回调函数
            **kwargs: 其他参数
            
        Returns:
            复合指标值
        """
        scores = []
        reasons = []
        run_logs = {}

        logger.info(f"开始计算复合指标...{test_case}")
        # 计算每个基础指标的得分
        for i, metric in enumerate(self.metrics):
            try:
                result = await metric.compute(test_case, *args, callbacks=callbacks, **kwargs)
                scores.append(result.score if result.score is not None else 0.0)
                if result.reason:
                    reasons.append(f"{metric.name}: {result.reason}")
                
                # 构造包含分数和原因的run_logs条目
                metric_run_log = {
                    "score": result.score if result.score is not None else 0.0,
                    "reason": result.reason
                }
                
                # 如果有详细run_logs，也包含进来
                if result.run_logs:
                    metric_run_log["details"] = result.run_logs
                    run_logs[metric.name] = metric_run_log
                else:
                    run_logs[metric.name] = metric_run_log
                
                # 使用标准日志记录每个指标的分数
                logger.info(f"指标 [{metric.name}] 分数: {result.score if result.score is not None else 0.0}")
                
            except Exception as e:
                # 如果某个指标计算失败，得分为0
                scores.append(0.0)
                reasons.append(f"{metric.name}: 计算失败 ({str(e)})")
                run_logs[metric.name] = {
                    "score": 0.0,
                    "reason": f"计算失败 ({str(e)})",
                    "error": str(e)
                }
                logger.error(f"指标 [{metric.name}] 计算失败: {str(e)}", exc_info=True)
        
        # 计算加权平均得分
        weighted_score = sum(score * weight for score, weight in zip(scores, self.weights))
        
        # 合并所有原因
        combined_reason = "; ".join(reasons) if reasons else None
        
        logger.info(f"复合指标加权得分: {weighted_score}")
        logger.info(f"原因: {combined_reason}")

        return MetricValue(
            score=weighted_score,
            reason=combined_reason,
            run_logs=run_logs if run_logs else None
        )