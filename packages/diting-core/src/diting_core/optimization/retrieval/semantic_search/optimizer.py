"""语义搜索参数优化器

通过笛卡尔积穷举所有可能的参数组合情况，评估每种情况并返回最佳参数组合。
"""

import asyncio
import itertools
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

from diting_core.optimization import BaseOptimizer
from diting_core.optimization.optimization_result import OptimizationResult as BaseOptimizationResult
from diting_core.optimization.target.semantic_search_config import SemanticSearchConfig
from diting_core.optimization.target.semantic_retriever import SemanticRetriever
from diting_core.optimization.datasets.base_dataset import BaseDataset
from diting_core.metrics.base_metric import BaseMetric
from diting_core.metrics.composite import CompositeMetric


class SemanticSearchExhaustiveOptimizer(BaseOptimizer):
    """语义搜索穷举优化器
    
    通过笛卡尔积穷举所有可能的参数组合情况，评估每种情况并返回最佳参数组合。
    """
    
    def __init__(
        self,
        similarity_threshold_range: Tuple[float, float] = (0.1, 0.9),
        similarity_threshold_step: float = 0.1,
        context_recall_tokens_range: Tuple[int, int] = (100, 30000),
        context_recall_tokens_step: int = 5000,
        max_workers: int = 5
    ):
        """初始化优化器
        
        Args:
            similarity_threshold_range: 相似度阈值范围 (min, max)
            similarity_threshold_step: 相似度阈值步长
            context_recall_tokens_range: 上下文召回 token 范围 (min, max)
            context_recall_tokens_step: 上下文召回 token 步长
            max_workers: 最大并发工作数
        """
        super().__init__()
        self.similarity_threshold_range = similarity_threshold_range
        self.similarity_threshold_step = similarity_threshold_step
        self.context_recall_tokens_range = context_recall_tokens_range
        self.context_recall_tokens_step = context_recall_tokens_step
        self.max_workers = max_workers

    async def _optimize(
        self,
        config: SemanticSearchConfig,
        dataset: BaseDataset,
        metric: BaseMetric,
        n_samples: Optional[int] = None,
        callbacks = None,
        **kwargs
    ) -> BaseOptimizationResult:
        """执行优化
        
        Args:
            config: 语义搜索配置
            dataset: 数据集
            metric: 评估指标
            n_samples: 采样数量
            callbacks: 回调函数
            
        Returns:
            优化结果
        """
        # 生成参数组合
        similarity_thresholds = self._generate_thresholds(
            self.similarity_threshold_range, 
            self.similarity_threshold_step
        )
        context_recall_tokens = self._generate_tokens(
            self.context_recall_tokens_range,
            self.context_recall_tokens_step
        )
        
        # 生成所有参数组合
        param_combinations = list(itertools.product(
            similarity_thresholds, 
            context_recall_tokens
        ))
        
        total_combinations = len(param_combinations)
        print(f"总组合数: {total_combinations}")
        print("开始语义搜索参数穷举优化...")
        print(f"相似度阈值范围: {self.similarity_threshold_range}")
        print(f"相似度阈值步长: {self.similarity_threshold_step}")
        print(f"上下文召回token数范围: {self.context_recall_tokens_range}")
        print(f"上下文召回token数步长: {self.context_recall_tokens_step}")
        print(f"参数组合总数: {total_combinations}")
        print(f"生成 {len(similarity_thresholds)} 个相似度阈值候选值")
        print(f"生成 {len(context_recall_tokens)} 个token数候选值")
        
        # 评估所有参数组合
        start_time = datetime.now()
        best_score = float('-inf')
        best_params = {}
        history = []
        
        # 限制样本数量
        items = dataset.get_items()
        if n_samples and n_samples < len(items):
            items = items[:n_samples]
            
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def evaluate_combination(params):
            async with semaphore:
                threshold, tokens = params
                try:
                    # 创建新的配置
                    test_config = SemanticSearchConfig(
                        similarity_threshold=threshold,
                        context_recall_max_tokens=tokens,
                        semantic_retriever=config.semantic_retriever
                    )
                    
                    # 评估配置
                    result = await metric.evaluate(
                        config=test_config,
                        dataset=dataset,
                        n_samples=n_samples
                    )
                    
                    score = result.score if result.score is not None else 0.0
                    
                    return {
                        "params": {
                            "similarity_threshold": threshold,
                            "context_recall_max_tokens": tokens
                        },
                        "score": score,
                        "details": result.details if hasattr(result, 'details') else {}
                    }
                except Exception as e:
                    print(f"评估参数组合时出错: {e}")
                    return {
                        "params": {
                            "similarity_threshold": threshold,
                            "context_recall_max_tokens": tokens
                        },
                        "score": 0.0,  # 出错时默认得分为0
                        "details": {"error": str(e)}
                    }
        
        # 并发评估所有组合
        eval_tasks = [evaluate_combination(params) for params in param_combinations]
        eval_results = await asyncio.gather(*eval_tasks, return_exceptions=True)
        
        # 处理评估结果
        valid_results = []
        for result in eval_results:
            if isinstance(result, Exception):
                print(f"评估任务异常: {result}")
                continue
            valid_results.append(result)
            history.append(result)
            
            if result["score"] > best_score:
                best_score = result["score"]
                best_params = result["params"]
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # 如果所有评估都失败了，使用默认参数
        if not valid_results:
            print("所有评估都失败了，使用默认参数")
            best_params = {
                "similarity_threshold": self.similarity_threshold_range[0],
                "context_recall_max_tokens": self.context_recall_tokens_range[0]
            }
            best_score = 0.0
            
        # 计算初始得分（使用默认参数）
        try:
            initial_result = await metric.evaluate(
                config=config,
                dataset=dataset,
                n_samples=n_samples
            )
            initial_score = initial_result.score if initial_result.score is not None else 0.0
        except Exception as e:
            print(f"评估初始配置时出错: {e}")
            initial_score = 0.0
            
        # 计算改进百分比，避免除以零
        if initial_score != 0:
            improvement = (best_score - initial_score) / abs(initial_score)
        else:
            improvement = 0.0 if best_score == 0 else float('inf')
            
        # 如果改进是无穷大，将其设置为一个大数
        if improvement == float('inf'):
            improvement = 1.0  # 或者其他合适的值
        elif improvement == float('-inf'):
            improvement = -1.0  # 或者其他合适的值
            
        print(f"优化完成，耗时: {execution_time:.2f}秒")
        print(f"最佳评分: {best_score:.4f}")
        print(f"最佳参数: {best_params}")
        print(f"初始评分: {initial_score:.4f}")
        print(f"性能提升: {improvement:.2%}")
        
        # 构建优化结果
        return BaseOptimizationResult(
            optimizer_name="SemanticSearchExhaustiveOptimizer",
            metric_name=metric.__class__.__name__,
            best_config=config,
            best_score=best_score,
            initial_score=initial_score,
            improvement=improvement,
            history=history,
            details={
                "best_params": best_params,
                "total_combinations": total_combinations,
                "execution_time": execution_time,
            }
        )
    
    def _generate_thresholds(
        self, 
        range_: Tuple[float, float], 
        step: float
    ) -> List[float]:
        """生成相似度阈值候选值"""
        start, end = range_
        # 确保起始值小于结束值
        if start > end:
            start, end = end, start
        # 生成候选值
        thresholds = []
        current = start
        while current <= end:
            thresholds.append(round(current, 6))  # 保留6位小数避免精度问题
            current += step
        # 确保包含结束值
        if thresholds and thresholds[-1] != end:
            thresholds.append(end)
        return thresholds
    
    def _generate_tokens(
        self, 
        range_: Tuple[int, int], 
        step: int
    ) -> List[int]:
        """生成上下文召回token数候选值"""
        start, end = range_
        # 确保起始值小于结束值
        if start > end:
            start, end = end, start
        # 生成候选值
        tokens = list(range(start, end + 1, step))
        # 确保包含结束值
        if tokens and tokens[-1] != end:
            tokens.append(end)
        return tokens