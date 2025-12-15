#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from diting_core.callbacks.base import Callbacks
from diting_core.callbacks.manager import new_group
from diting_core.cases.llm_case import LLMCase
from diting_core.metrics.base_metric import BaseMetric, MetricValue
from diting_core.models.reranker.base_model import BaseReranker
from diting_server.common.logging_config.config import get_logger

logger = get_logger(__name__)


@dataclass
class RerankMetric(BaseMetric):
    """
    RerankMetric 用于计算rerank相关的指标，包括：
    - MRR (Mean Reciprocal Rank)
    - NDCG (Normalized Discounted Cumulative Gain)
    - MAP (Mean Average Precision)

    该指标接受包含以下字段的数据：
    - question: 问题
    - expect_dataId: 期望的参考文档ID列表
    - rerank_topn: rerank后的前n个结果

    属性:
        rerank_model
        columns_to_evaluate: 需要评估的列名列表
        k_values: 评估的top-k值列表
    """

    rerank_model: Optional[BaseReranker] = None
    k_values: List[int] = None
    prefixes: List[str] = None
    batch_size: int = 20
    enable_batching: bool = True

    def __post_init__(self):
        if self.k_values is None:
            self.k_values = [5, 10, 15]
        if self.prefixes is None:
            self.prefixes = ["rerank"]

    @property
    def columns_to_evaluate(self) -> List[str]:
        """
        根据k值和前缀列表动态生成要评估的列名列表

        Returns:
            List[str]: 生成的列名列表，如 ['rerank_top5', 'rerank_top10', 'rerank_top15', 'embedding_top5', ...]
        """
        columns = []
        for prefix in self.prefixes:
            for k in self.k_values:
                columns.append(f"{prefix}_top{k}")
        return columns

    def _calculate_dcg(self, relevances: List[float], k: Optional[int] = None) -> float:
        """计算DCG (Discounted Cumulative Gain)"""
        if k is None:
            k = len(relevances)

        dcg_value = 0.0
        for i in range(min(k, len(relevances))):
            relevance = relevances[i]
            if i == 0:
                dcg_value += relevance
            else:
                dcg_value += relevance / math.log2(i + 2)  # log2(i+1) 因为i从0开始
        return dcg_value

    def _calculate_ndcg(
        self, predicted: List[str], relevant: List[str], k: Optional[int] = None
    ) -> float:
        """计算NDCG (Normalized Discounted Cumulative Gain)"""
        if k is None:
            k = len(predicted)

        # 创建相关性列表，1表示相关，0表示不相关
        relevances = [1.0 if item in relevant else 0.0 for item in predicted[:k]]

        # 计算DCG
        dcg_value = self._calculate_dcg(relevances, k)

        # 计算IDCG (Ideal DCG)，即理想排序下的DCG
        ideal_relevances = [1.0] * min(len(relevant), k)
        idcg_value = self._calculate_dcg(ideal_relevances, k)

        # 避免除以0
        if idcg_value == 0:
            return 0.0

        return dcg_value / idcg_value

    def _calculate_average_precision(
        self, predicted: List[str], relevant: List[str]
    ) -> float:
        """计算AP (Average Precision)"""
        if not relevant:
            return 0.0

        relevant_set = set(relevant)
        hit_count = 0
        sum_precisions = 0.0

        for i, item in enumerate(predicted):
            if item in relevant_set:
                hit_count += 1
                precision_at_i = hit_count / (i + 1)
                sum_precisions += precision_at_i

        if hit_count == 0:
            return 0.0

        return sum_precisions / len(relevant)

    def _calculate_reciprocal_rank(
        self, predicted: List[str], relevant: List[str]
    ) -> float:
        """计算RR (Reciprocal Rank)"""
        for i, item in enumerate(predicted):
            if item in relevant:
                return 1.0 / (i + 1)  # i从0开始，所以加1
        return 0.0

    async def _process_rerank_cases(
        self,
        test_cases: List[LLMCase],
        callbacks: Optional[Callbacks] = None,
    ) -> List[Dict]:
        """处理所有rerank案例"""
        run_mgt, grp_cb = await new_group(
            name="process_rerank_test_cases",
            inputs={
                "total_cases": len(test_cases),
                "metric_name": self.__class__.__name__,
            },
            callbacks=callbacks,
        )

        results = []
        try:
            # 预处理：过滤无效案例和提取需要rerank的数据
            valid_cases = []
            for i, case in enumerate(test_cases):
                retrieval_questions = case.retrieval_context
                embed_quote_list = case.metadata.get("embed_quote_list", [])

                if retrieval_questions and embed_quote_list:
                    valid_cases.append((i, case))
                else:
                    # 直接添加无需rerank的案例
                    results.append(
                        {
                            "question": case.user_input,
                            "expect_dataId": case.metadata.get("dataId", []),
                            "embed_quote_ids": [
                                ref.get("id", "") for ref in embed_quote_list
                            ],
                            "rerank_skipped": True,
                            "reason": "No retrieval context or embed quotes",
                        }
                    )

            # 批量处理有效案例
            if valid_cases:
                batch_results = await self._batch_process_cases(
                    valid_cases, callbacks=grp_cb
                )
                # 将批量结果插入到正确位置
                for original_index, case_data in batch_results:
                    if original_index < len(results):
                        results.insert(original_index, case_data)
                    else:
                        results.append(case_data)
            # 计算统计信息
            successful_count = len(
                [r for r in results if r.get("rerank_success", False)]
            )
            skipped_count = len([r for r in results if r.get("rerank_skipped", False)])
            failed_count = len(
                [r for r in results if r.get("rerank_failed", False) or "error" in r]
            )

            await run_mgt.on_chain_end(
                outputs={
                    "total_cases": len(test_cases),
                    "successful_cases": successful_count,
                    "skipped_cases": skipped_count,
                    "failed_cases": failed_count,
                    "results_summary": {
                        "columns_evaluated": self.columns_to_evaluate,
                        "k_values": self.k_values,
                        "prefixes": self.prefixes,
                    },
                }
            )

        except Exception as e:
            await run_mgt.on_chain_error(e)
            raise

        return results

    async def _batch_process_cases(
        self,
        valid_cases: List[Tuple[int, LLMCase]],
        callbacks: Optional[Callbacks] = None,
    ) -> List[Tuple[int, Dict]]:
        """批量处理案例以提高效率"""
        batch_results = []

        batch_size = self.batch_size if self.enable_batching else 1
        for i in range(0, len(valid_cases), batch_size):
            batch = valid_cases[i : i + batch_size]
            batch_tasks = []

            for original_index, case in batch:
                task = self._process_single_case(case, callbacks)
                batch_tasks.append((original_index, task))

            for original_index, task in batch_tasks:
                try:
                    case_data = await task
                    batch_results.append((original_index, case_data))
                except Exception as e:
                    logger.warning(
                        f"Failed to process case at index {original_index}: {str(e)}"
                    )
                    batch_results.append(
                        (
                            original_index,
                            {
                                "question": case.user_input,
                                "expect_dataId": case.metadata.get("dataId", []),
                                "error": str(e),
                            },
                        )
                    )

        return batch_results

    async def _process_single_case(
        self, case: LLMCase, callbacks: Optional[Callbacks] = None
    ) -> Dict:
        """处理单个rerank案例"""
        embed_quote_list = case.metadata.get("embed_quote_list", [])
        row_data = {
            "question": case.user_input,
            "expect_dataId": case.metadata.get("dataId", []),
            "embed_quote_ids": [ref.get("id", "") for ref in embed_quote_list],
        }

        retrieval_questions = case.retrieval_context
        list_len = len(retrieval_questions)

        # 1. 设置embedding检索结果
        self._set_embedding_results(row_data, list_len)

        # 2. 获取rerank结果
        if self.rerank_model:
            await self._set_rerank_results(row_data, retrieval_questions, callbacks)
        else:
            row_data["rerank_skipped"] = True
            row_data["reason"] = "No rerank model provided"
            for k in self.k_values:
                row_data[f"rerank_top{k}"] = row_data.get(f"embedding_top{k}", [])

        return row_data

    def _set_embedding_results(self, row_data: Dict, list_len: int) -> None:
        """设置embedding检索结果"""
        embed_quote_ids = row_data.get("embed_quote_ids", [])
        for k in self.k_values:
            top_k = min(k, list_len, len(embed_quote_ids))
            row_data[f"embedding_top{k}"] = (
                embed_quote_ids[:top_k] if embed_quote_ids else []
            )

    async def _set_rerank_results(
        self,
        row_data: Dict,
        retrieval_questions: List,
        callbacks: Optional[Callbacks] = None,
    ) -> None:
        """设置rerank结果"""
        query = row_data.get("question", "")
        embed_quote_ids = row_data.get("embed_quote_ids", [])

        # 输入验证
        if not retrieval_questions or not embed_quote_ids:
            logger.warning(
                f"Invalid input for rerank: query='{query}', no documents or ids"
            )
            self._use_fallback_results(row_data, embed_quote_ids)
            return

        try:
            rerank_results = await self.rerank_model.rerank(
                query=query,
                documents=retrieval_questions,
                top_k=min(max(self.k_values), len(retrieval_questions)),
                callbacks=callbacks,
            )
            # 提取rerank后的文档索引
            reranked_indices = []
            for result in rerank_results:
                idx = result.get("index", result.get("idx", -1))
                if isinstance(idx, int) and 0 <= idx < len(embed_quote_ids):
                    reranked_indices.append(idx)
            if reranked_indices:
                reranked_docs_id = [embed_quote_ids[idx] for idx in reranked_indices]
                for k in self.k_values:
                    row_data[f"rerank_top{k}"] = reranked_docs_id[:k]
                row_data["rerank_success"] = True
                row_data["rerank_failed"] = False
            else:
                logger.warning(f"Rerank结果无效，使用fallback: query='{query}'")
                self._use_fallback_results(row_data, embed_quote_ids)

        except Exception as e:
            logger.error(f"Rerank failed for query '{query}': {str(e)}", exc_info=True)
            self._use_fallback_results(row_data, embed_quote_ids)

    def _use_fallback_results(self, row_data: Dict, ref_list: List) -> None:
        """使用原始结果作为fallback"""
        for k in self.k_values:
            top_k = min(k, len(ref_list))
            row_data[f"rerank_top{k}"] = ref_list[:top_k] if ref_list else []
        row_data["rerank_failed"] = True
        row_data["rerank_success"] = False
        if "rerank_skipped" in row_data:
            del row_data["rerank_skipped"]

    async def _compute(
        self,
        test_case: List[LLMCase],
        *args: Any,
        callbacks: Optional[Callbacks] = None,
        **kwargs: Any,
    ) -> MetricValue:
        """计算rerank指标"""

        # 批量处理数据
        rerank_results = await self._process_rerank_cases(
            test_cases=test_case, callbacks=callbacks
        )

        # 初始化指标存储
        mrr_scores: Dict[str, List[float]] = {
            col: [] for col in self.columns_to_evaluate
        }
        ndcg_scores: Dict[str, List[float]] = {
            col: [] for col in self.columns_to_evaluate
        }
        map_scores: Dict[str, List[float]] = {
            col: [] for col in self.columns_to_evaluate
        }

        # 统计信息
        expect_count = 0
        valid_results_count = 0
        column_stats = {
            col: {"hit_count": 0, "total_count": 0, "error_count": 0}
            for col in self.columns_to_evaluate
        }

        # 遍历每一行数据进行指标计算
        for result_index, result in enumerate(rerank_results):
            expected_dataids = result.get("expect_dataId", [])
            # 如果没有期望数据，跳过该结果
            if not expected_dataids:
                continue

            expect_count += 1
            valid_results_count += 1
            expected_set = set(expected_dataids)

            # 处理每个评估列
            for column in self.columns_to_evaluate:
                try:
                    # 检查列是否存在且有效
                    column_refs = result.get(column)
                    if not column_refs or not isinstance(column_refs, list):
                        column_stats[column]["error_count"] += 1
                        continue

                    # 计算各项指标
                    mrr_score = self._calculate_reciprocal_rank(
                        column_refs, expected_dataids
                    )
                    mrr_scores[column].append(mrr_score)

                    # 动态计算NDCG的k值，最大不超过15
                    k_value = min(len(column_refs), 15)
                    ndcg_score = self._calculate_ndcg(
                        column_refs, expected_dataids, k_value
                    )
                    ndcg_scores[column].append(ndcg_score)

                    # 计算平均精度
                    ap_score = self._calculate_average_precision(
                        column_refs, expected_dataids
                    )
                    map_scores[column].append(ap_score)

                    # 更新统计信息
                    column_stats[column]["total_count"] += 1
                    if any(ref_id in expected_set for ref_id in column_refs):
                        column_stats[column]["hit_count"] += 1

                except (ValueError, TypeError, AttributeError, IndexError) as e:
                    logger.warning(
                        f"计算指标时出错 - 结果索引: {result_index}, "
                        f"列名: {column}, 错误: {str(e)}"
                    )
                    column_stats[column]["error_count"] += 1
                    continue

        # 计算平均指标
        results = {}
        for col in self.columns_to_evaluate:
            if mrr_scores[col]:
                results[f"{col}_mrr"] = sum(mrr_scores[col]) / len(mrr_scores[col])
            if ndcg_scores[col]:
                results[f"{col}_ndcg"] = sum(ndcg_scores[col]) / len(ndcg_scores[col])
            if map_scores[col]:
                results[f"{col}_map"] = sum(map_scores[col]) / len(map_scores[col])

            # 计算命中率 - 基于有效结果数量而不是总数量
            if column_stats[col]["total_count"] > 0:
                results[f"{col}_precision"] = (
                    column_stats[col]["hit_count"] / column_stats[col]["total_count"]
                )
                # 添加错误率统计
                if column_stats[col]["error_count"] > 0:
                    results[f"{col}_error_rate"] = (
                        column_stats[col]["error_count"]
                        / column_stats[col]["total_count"]
                    )

        # 计算整体平均分数
        overall_mrr = []
        overall_ndcg = []
        overall_map = []

        for col in self.columns_to_evaluate:
            if mrr_scores[col]:
                overall_mrr.extend(mrr_scores[col])
            if ndcg_scores[col]:
                overall_ndcg.extend(ndcg_scores[col])
            if map_scores[col]:
                overall_map.extend(map_scores[col])

        if overall_mrr:
            results["overall_mrr"] = sum(overall_mrr) / len(overall_mrr)
        if overall_ndcg:
            results["overall_ndcg"] = sum(overall_ndcg) / len(overall_ndcg)
        if overall_map:
            results["overall_map"] = sum(overall_map) / len(overall_map)

        score = results.get("overall_mrr", 0.0)
        reason_parts = [
            f"共处理 {len(rerank_results)} 条数据，其中 {expect_count} 条有期望参考文档，{valid_results_count} 条有效数据",
            f"计算的指标列: {', '.join(self.columns_to_evaluate)}",
        ]
        rerank_success_count = sum(
            1 for r in rerank_results if r.get("rerank_success", False)
        )
        rerank_failed_count = sum(
            1 for r in rerank_results if r.get("rerank_failed", False)
        )
        if rerank_success_count + rerank_failed_count > 0:
            success_rate = rerank_success_count / (
                rerank_success_count + rerank_failed_count
            )
            reason_parts.append(
                f"Rerank成功率: {success_rate:.3f} ({rerank_success_count}/{rerank_success_count + rerank_failed_count})"
            )

        for col in self.columns_to_evaluate:
            if column_stats[col]["total_count"] > 0:
                precision = results.get(f"{col}_precision", 0)
                mrr = results.get(f"{col}_mrr", 0)
                ndcg = results.get(f"{col}_ndcg", 0)
                map_score = results.get(f"{col}_map", 0)

                reason_parts.append(
                    f"{col}: 命中率={precision:.3f}, MRR={mrr:.3f}, NDCG={ndcg:.3f}, MAP={map_score:.3f}"
                )

        if "overall_mrr" in results:
            reason_parts.extend(
                [
                    f"整体平均指标: MRR={results['overall_mrr']:.3f}",
                    f"NDCG={results['overall_ndcg']:.3f}"
                    if "overall_ndcg" in results
                    else "",
                    f"MAP={results['overall_map']:.3f}"
                    if "overall_map" in results
                    else "",
                ]
            )

        reason = "; ".join([part for part in reason_parts if part])

        metric_value = MetricValue(
            score=score,
            reason=reason,
            run_logs={
                "detailed_results": results,
                "mrr_scores": {k: v for k, v in mrr_scores.items() if v},
                "ndcg_scores": {k: v for k, v in ndcg_scores.items() if v},
                "map_scores": {k: v for k, v in map_scores.items() if v},
                "column_stats": column_stats,
                "total_rows": len(rerank_results),
                "expect_count": expect_count,
            },
        )

        return metric_value
