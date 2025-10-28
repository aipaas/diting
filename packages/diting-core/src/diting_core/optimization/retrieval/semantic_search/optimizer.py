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
            context_recall_tokens_range: 上下文召回token数范围 (min, max)
            context_recall_tokens_step: 上下文召回token数步长
            max_workers: 最大并发评估工作数
        """
        self.similarity_threshold_range = similarity_threshold_range
        self.similarity_threshold_step = similarity_threshold_step
        self.context_recall_tokens_range = context_recall_tokens_range
        self.context_recall_tokens_step = context_recall_tokens_step
        self.max_workers = max_workers
        
        # 生成参数候选值
        self._generate_parameter_candidates()
    
    def _generate_parameter_candidates(self):
        """生成参数候选值"""
        # 生成相似度阈值候选值
        min_threshold, max_threshold = self.similarity_threshold_range
        self.similarity_threshold_candidates = [
            round(threshold, 2) 
            for threshold in self._frange(min_threshold, max_threshold + self.similarity_threshold_step, self.similarity_threshold_step)
            if min_threshold <= round(threshold, 2) <= max_threshold
        ]
        
        # 生成上下文召回token数候选值
        min_tokens, max_tokens = self.context_recall_tokens_range
        self.context_recall_tokens_candidates = list(range(
            min_tokens, 
            max_tokens + self.context_recall_tokens_step, 
            self.context_recall_tokens_step
        ))
        
        print(f"生成 {len(self.similarity_threshold_candidates)} 个相似度阈值候选值")
        print(f"生成 {len(self.context_recall_tokens_candidates)} 个token数候选值")
        print(f"总组合数: {len(self.similarity_threshold_candidates) * len(self.context_recall_tokens_candidates)}")
    
    def _frange(self, start: float, stop: float, step: float):
        """浮点数范围生成器"""
        while start < stop:
            yield start
            start += step
    
    async def _evaluate_single_combination(
        self,
        semantic_retriever: SemanticRetriever,
        dataset: BaseDataset,
        metric: BaseMetric,
        similarity_threshold: float,
        context_recall_tokens: int,
        n_samples: Optional[int] = None
    ) -> Dict[str, Any]:
        """评估单个参数组合
        
        Args:
            semantic_retriever: 语义检索器
            dataset: 评估数据集
            metric: 评估指标
            similarity_threshold: 相似度阈值
            context_recall_tokens: 上下文召回token数
            n_samples: 采样数量
            
        Returns:
            包含参数组合和评分的字典
        """
        # 创建配置
        config = SemanticSearchConfig.create_with_threshold(
            semantic_retriever=semantic_retriever,
            similarity_threshold=similarity_threshold,
            context_recall_max_tokens=context_recall_tokens
        )
        
        # 评估配置
        try:
            score_result = await self._evaluate_config(config, dataset, metric, n_samples)
            score = score_result if isinstance(score_result, (int, float)) else score_result[0]
            run_log = {} if isinstance(score_result, (int, float)) else score_result[1]
            
            return {
                "params": {
                    "similarity_threshold": similarity_threshold,
                    "context_recall_max_tokens": context_recall_tokens
                },
                "score": score,
                "success": True,
                "run_log": run_log
            }
        except Exception as e:
            print(f"评估参数组合时出错: 阈值={similarity_threshold}, tokens={context_recall_tokens}, 错误={str(e)}")
            return {
                "params": {
                    "similarity_threshold": similarity_threshold,
                    "context_recall_max_tokens": context_recall_tokens
                },
                "score": 0.0,
                "success": False,
                "error": str(e),
                "run_log": {}
            }
    
    async def _evaluate_config(
        self,
        config: SemanticSearchConfig,
        dataset: BaseDataset,
        metric: BaseMetric,
        n_samples: Optional[int] = None
    ) -> tuple:
        """评估配置
        
        Args:
            config: 语义搜索配置
            dataset: 评估数据集
            metric: 评估指标
            n_samples: 采样数量
            
        Returns:
            (平均评分, 运行日志)
        """
        samples = dataset.get_items(n_samples=n_samples)
        if not samples:
            raise ValueError("数据集为空")
        
        scores = []
        total_retrieval_count = 0
        sample_count = 0
        run_logs = []
        
        for sample in samples:
            try:
                # 执行配置
                results = await config.execute(dataset_item=sample)
                
                # 统计检索条数
                total_retrieval_count += len(results)
                sample_count += 1
                
                # 收集文档ID列表
                document_ids = [result.get("id", "unknown") for result in results]
                
                # 计算指标
                if isinstance(metric, CompositeMetric):
                    # 对于复合指标，需要构造LLMCase对象
                    from diting_core.cases.llm_case import LLMCase
                    test_case = LLMCase(
                        user_input=sample.get("user_input", ""),
                        expected_output=sample.get("expected_output", ""),  # 示例中没有提供预期输出
                        retrieval_context=[r.get("content", "") for r in results]
                    )
                    metric_value = await metric.compute(test_case)
                    score = metric_value.score
                    # 收集运行日志
                    if metric_value.run_logs:
                        run_logs.append({
                            "sample_id": sample.get("id", "unknown"),
                            "score": score,
                            "retrieval_count": len(results),
                            "document_ids": document_ids,
                            "run_logs": metric_value.run_logs
                        })
                else:
                    # 对于单一指标，使用_compute方法
                    score = await metric._compute(results)
                    run_logs.append({
                        "sample_id": sample.get("id", "unknown"),
                        "score": score,
                        "retrieval_count": len(results),
                        "document_ids": document_ids
                    })
                scores.append(score)
            except Exception as e:
                print(f"评估样本时出错: {str(e)}")
                scores.append(0.0)
                run_logs.append({
                    "sample_id": sample.get("id", "unknown"),
                    "score": 0.0,
                    "error": str(e)
                })
        
        # 计算平均检索条数
        avg_retrieval_count = total_retrieval_count / sample_count if sample_count > 0 else 0
        
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        return avg_score, {
            "avg_retrieval_count": avg_retrieval_count,
            "total_samples": sample_count,
            "run_logs": run_logs
        }
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """计算两个向量的余弦相似度"""
        # 转换为numpy数组
        a = np.array(a)
        b = np.array(b)
        
        # 计算点积
        dot_product = np.dot(a, b)
        
        # 计算范数
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        # 避免除零错误
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        # 计算余弦相似度
        return dot_product / (norm_a * norm_b)
    
    async def _optimize(
        self,
        config: SemanticSearchConfig,
        dataset: BaseDataset,
        metric: BaseMetric,
        n_samples: Optional[int] = None,
        verbose: bool = True,
        **kwargs: Any
    ) -> BaseOptimizationResult:
        """执行穷举优化
        
        Args:
            config: 语义搜索配置
            dataset: 评估数据集
            metric: 评估指标
            n_samples: 采样数量
            verbose: 是否输出详细信息
            **kwargs: 其他参数
            
        Returns:
            优化结果
        """
        start_time = datetime.now()
        
        if verbose:
            print("开始语义搜索参数穷举优化...")
            print(f"相似度阈值范围: {self.similarity_threshold_range}")
            print(f"相似度阈值步长: {self.similarity_threshold_step}")
            print(f"上下文召回token数范围: {self.context_recall_tokens_range}")
            print(f"上下文召回token数步长: {self.context_recall_tokens_step}")
            print(f"参数组合总数: {len(self.similarity_threshold_candidates) * len(self.context_recall_tokens_candidates)}")
        
        # 生成所有参数组合
        param_combinations = list(itertools.product(
            self.similarity_threshold_candidates,
            self.context_recall_tokens_candidates
        ))
        
        if verbose:
            print(f"生成 {len(param_combinations)} 个参数组合")
        
        # 评估所有参数组合
        all_results = []
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def evaluate_with_semaphore(combination):
            async with semaphore:
                similarity_threshold, context_recall_tokens = combination
                result = await self._evaluate_single_combination(
                    config.semantic_retriever,
                    dataset,
                    metric,
                    similarity_threshold,
                    context_recall_tokens,
                    n_samples
                )
                return result
        
        # 并发评估所有组合
        tasks = [evaluate_with_semaphore(combination) for combination in param_combinations]
        all_results = await asyncio.gather(*tasks)
        
        # 找到最佳结果
        valid_results = [r for r in all_results if r["success"]]
        if not valid_results:
            raise RuntimeError("所有参数组合评估都失败了")
        
        best_result = max(valid_results, key=lambda x: x["score"])
        
        # 计算初始评分（使用默认参数）
        initial_config = SemanticSearchConfig.create_default(config.semantic_retriever)
        initial_score_result = await self._evaluate_config(initial_config, dataset, metric, n_samples)
        initial_score = initial_score_result if isinstance(initial_score_result, (int, float)) else initial_score_result[0]
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        if verbose:
            print(f"优化完成，耗时: {execution_time:.2f}秒")
            print(f"最佳评分: {best_result['score']:.4f}")
            print(f"最佳参数: {best_result['params']}")
            print(f"初始评分: {initial_score:.4f}")
            improvement = (best_result['score'] - initial_score) / initial_score if initial_score != 0 else float('inf')
            print(f"性能提升: {improvement:.2%}")
        
        # 构建历史记录
        history = []
        # 添加初始配置记录
        history.append({
            "iteration": 0,
            "type": "baseline",
            "score": initial_score,
            "params": {
                "similarity_threshold": initial_config.similarity_threshold,
                "context_recall_max_tokens": initial_config.context_recall_max_tokens
            }
        })
        
        # 添加所有评估记录
        for i, result in enumerate(all_results, 1):
            history_record = {
                "iteration": i,
                "type": "evaluation",
                "score": result["score"],
                "params": result["params"],
                "success": result["success"],
                "execution_time": execution_time
            }
            
            # 添加运行日志信息
            if "run_log" in result:
                history_record["run_log"] = result["run_log"]
                
            history.append(history_record)
        
        # 创建符合系统规范的优化结果对象
        optimization_result = BaseOptimizationResult(
            optimizer_name=self.__class__.__name__,
            metric_name=metric.name,
            best_config=initial_config,
            best_score=best_result["score"],
            initial_config=initial_config,
            initial_score=initial_score,
            improvement=(best_result['score'] - initial_score) / initial_score if initial_score != 0 else float('inf'),
            history=history,
            details={
                "all_results": all_results,
                "total_combinations": len(param_combinations),
                "execution_time": execution_time,
                "best_params": best_result["params"]
            },
            total_llm_calls=0,
            iterations=len(all_results) + 1  # 包含初始评估
        )
        
        return optimization_result
    
    def get_parameter_space_summary(self) -> Dict[str, Any]:
        """获取参数空间摘要
        
        Returns:
            参数空间信息
        """
        return {
            "similarity_threshold": {
                "range": self.similarity_threshold_range,
                "step": self.similarity_threshold_step,
                "candidates": self.similarity_threshold_candidates,
                "count": len(self.similarity_threshold_candidates)
            },
            "context_recall_max_tokens": {
                "range": self.context_recall_tokens_range,
                "step": self.context_recall_tokens_step,
                "candidates": self.context_recall_tokens_candidates,
                "count": len(self.context_recall_tokens_candidates)
            },
            "total_combinations": len(self.similarity_threshold_candidates) * len(self.context_recall_tokens_candidates)
        }