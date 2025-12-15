#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import time
import random
import threading
import multiprocessing as mp
from typing import Any, List, Dict, Set, Optional, Tuple
from functools import lru_cache
import hashlib

from diting_server.common.logging_config.config import get_logger
from diting_core.callbacks.base import Callbacks
from diting_core.cases.llm_case import LLMCase
from diting_core.synthesis.base_synthesizer import BaseSynthesizer
from diting_core.synthesis.base_corpus import BaseCorpus
from diting_core.synthesis.qa.schema import FineTuneSample, PrecomputedData

logger = get_logger(__name__)


class FineTuneDataSynthesizer(BaseSynthesizer):
    """
    构建微调数据，包括正负样本生成、知识库占比采样
    1. 输入验证和预处理
    2. 统计各知识库的数据量和占比
    3. 预构建映射表：
       - 问题到数据项的映射
       - 问题到知识库的映射
       - 知识库到问题的映射
    4. 构建样本：
       a. 从indexes中提取每个[q1, q2]对作为正样本
       b. 使用预构建映射采样负样本
    5. 按知识库占比分配基础样本
    6. 生成统计信息并返回结果
    """

    def __init__(
        self,
        negative_sample_ratio: float = 0.5,
        same_collection_base_ratio: float = 0.3,
        same_collection_weight: float = 0.5,
        max_workers: int = 4,
        use_process_pool: bool = True,
        chunk_size: int = 100,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.negative_sample_ratio = negative_sample_ratio
        self.same_collection_base_ratio = same_collection_base_ratio
        self.same_collection_weight = same_collection_weight
        self.max_workers = max_workers
        self.use_process_pool = use_process_pool
        self.chunk_size = chunk_size

        # 根据配置选择执行器
        if use_process_pool:
            self.executor = ProcessPoolExecutor(
                max_workers=min(max_workers, mp.cpu_count())
            )
        else:
            self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # 预分配随机数生成器池
        self._random_generators = [random.Random() for _ in range(max_workers)]

        # 使用更细粒度的锁，减少锁竞争
        self._worker_locks = [threading.Lock() for _ in range(max_workers)]

        # 缓存优化：预计算数据结构
        self._precomputed_cache = {}
        self._cache_max_size = 100

    async def _apply(
        self,
        corpus: BaseCorpus,
        callbacks: Optional[Callbacks] = None,
        **kwargs: Any,
    ) -> LLMCase:
        items = getattr(corpus, "fine_tune_items", [])
        min_negative_samples = getattr(corpus, "min_negative_samples", 1)
        max_negative_samples = getattr(corpus, "max_negative_samples", 10)
        include_original_q = getattr(corpus, "include_original_q", True)
        request_id = getattr(corpus, "request_id", "unknown")

        result = await self._build_fine_tune_data(
            items=items,
            min_negative_samples=min_negative_samples,
            max_negative_samples=max_negative_samples,
            include_original_q=include_original_q,
            request_id=request_id,
        )

        # 创建 LLMCase 返回结果
        llm_case = LLMCase(
            user_input=f"Build fine tune data from {len(items)} items",
            expected_output=f"Generated {result['total_samples']} samples",
            context=[f"Request ID: {request_id}"],
            metadata={
                "synthesizer": self.name,
                "result": result,
                "total_items": result["total_items"],
                "total_samples": result["total_samples"],
                "processing_time": result["processing_time"],
            },
        )

        return llm_case

    def _build_precomputed_data_optimized(
        self, items: List[Any], collection_ids: Set[str]
    ) -> PrecomputedData:
        """预计算数据结构构建 - 减少内存分配和提升速度"""
        # 预分配字典容量，减少动态扩容
        estimated_questions = len(items) * 4  # 估算问题数量
        all_questions: List[str] = []
        all_questions.reserve(estimated_questions) if hasattr(
            all_questions, "reserve"
        ) else None

        question_to_items: Dict[str, Set[str]] = {}  # 使用集合避免重复
        question_to_collection: Dict[str, str] = {}
        collection_questions: Dict[str, Set[str]] = {
            cid: set() for cid in collection_ids
        }
        question_index_map: Dict[str, int] = {}

        # 批量处理，减少中间对象创建
        question_pairs_batch = []

        for item in items:
            item_id = item.dataId
            collection_id = item.collectionId

            # 批量提取问题对
            for pair in item.indexes:
                if len(pair) >= 2:
                    q1, q2 = pair[0], pair[1]
                    question_pairs_batch.append((q1, q2, item_id, collection_id))

        # 批量处理问题对，减少字典操作
        for q1, q2, item_id, collection_id in question_pairs_batch:
            for question in (q1, q2):
                if question not in question_to_items:
                    question_to_items[question] = set()
                    question_to_collection[question] = collection_id
                    collection_questions[collection_id].add(question)
                    question_index_map[question] = len(all_questions)
                    all_questions.append(question)

                question_to_items[question].add(item_id)

        # 转换为预期格式（集合转列表）
        question_to_items_list = {
            q: list(items_set) for q, items_set in question_to_items.items()
        }
        collection_questions_list = {
            cid: list(questions_set)
            for cid, questions_set in collection_questions.items()
        }

        return PrecomputedData(
            all_questions=all_questions,
            question_to_items=question_to_items_list,
            question_to_collection=question_to_collection,
            collection_questions=collection_questions_list,
            question_index_map=question_index_map,
        )

    def _process_items_chunk(
        self,
        items_chunk: List[Any],
        precomputed: PrecomputedData,
        collection_stats: Dict[str, Dict[str, Any]],
        min_negative_samples: int,
        max_negative_samples: int,
        include_original_q: bool,
        chunk_start_index: int = 0,
    ) -> List[Any]:
        """处理数据项块 - 用于并行处理"""
        chunk_samples = []

        for local_index, item in enumerate(items_chunk):
            item_index = chunk_start_index + local_index
            item_id = item.dataId
            collection_id = item.collectionId

            # 构建正样本：每个indexes中的[q1, q2]对
            for pair_index, pair in enumerate(item.indexes):
                if len(pair) < 2:
                    continue

                q1, q2 = pair[0], pair[1]

                # 负样本采样
                negatives = self._sample_negatives_optimized(
                    precomputed=precomputed,
                    q1=q1,
                    q2=q2,
                    item_id=item_id,
                    collection_id=collection_id,
                    collection_stats=collection_stats,
                    min_negative_samples=min_negative_samples,
                    max_negative_samples=max_negative_samples,
                    worker_id=item_index % len(self._random_generators),
                )

                # 创建样本
                sample = self._create_fine_tune_sample(
                    query=q1,
                    positive=q2,
                    negatives=negatives,
                    source_id=item_id,
                    collection_id=collection_id,
                    original_q=item.q if include_original_q else None,
                    original_a=item.a if include_original_q else None,
                    metadata={
                        "pair_index": pair_index,
                        "source_type": "index_pair",
                        "negative_count": len(negatives),
                    },
                )
                chunk_samples.append(sample)

        return chunk_samples

    def _build_precomputed_data(
        self, items: List[Any], collection_ids: Set[str]
    ) -> PrecomputedData:
        """构建预计算数据结构"""
        # 检查缓存
        cache_key = self._get_question_hash(
            str(len(items)) + str(sorted(collection_ids))
        )
        if cache_key in self._precomputed_cache:
            return self._precomputed_cache[cache_key]

        result = self._build_precomputed_data_optimized(items, collection_ids)

        # 缓存结果
        if len(self._precomputed_cache) < self._cache_max_size:
            self._precomputed_cache[cache_key] = result

        return result

    @lru_cache(maxsize=1000)
    def _get_question_hash(self, question: str) -> str:
        """缓存问题哈希值，减少重复计算"""
        return hashlib.md5(question.encode()).hexdigest()[:8]

    def _sample_negatives_optimized(
        self,
        precomputed: PrecomputedData,
        q1: str,
        q2: str,
        item_id: str,
        collection_id: str,
        collection_stats: Dict[str, Dict[str, Any]],
        min_negative_samples: int,
        max_negative_samples: int,
        worker_id: int = 0,
    ) -> List[str]:
        """负样本采样算法"""
        # 使用预分配的随机数生成器
        rng = self._random_generators[worker_id % len(self._random_generators)]

        # 使用worker特定的锁，减少锁竞争
        worker_lock = self._worker_locks[worker_id % len(self._worker_locks)]

        # 预计算排除集合，避免重复查找
        exclude_q1 = q1
        exclude_q2 = q2
        exclude_items_set = {item_id}

        with worker_lock:
            same_collection_questions = precomputed.collection_questions.get(
                collection_id, []
            )
            same_collection_candidates = []
            for question in same_collection_questions:
                if (
                    question != exclude_q1
                    and question != exclude_q2
                    and item_id
                    not in precomputed.question_to_items.get(question, set())
                ):
                    same_collection_candidates.append(question)

            exclude_set = {exclude_q1, exclude_q2}
            max_candidates_needed = max_negative_samples * 2

            # 从其他知识库获取候选（限制数量，提前退出）
            other_collection_candidates = []
            candidates_count = 0

            for cid, questions in precomputed.collection_questions.items():
                if cid == collection_id or candidates_count >= max_candidates_needed:
                    continue

                for question in questions:
                    if (
                        question not in exclude_set
                        and item_id
                        not in precomputed.question_to_items.get(question, set())
                    ):
                        other_collection_candidates.append(question)
                        candidates_count += 1
                        if candidates_count >= max_candidates_needed:
                            break

        # 计算需要采样的数量
        total_candidates = len(same_collection_candidates) + len(
            other_collection_candidates
        )
        if total_candidates == 0:
            return []

        num_negatives = max(
            min_negative_samples,
            min(
                max_negative_samples, int(total_candidates * self.negative_sample_ratio)
            ),
        )

        # 计算同库样本比例 - 使用缓存的统计值
        current_collection_percentage = (
            collection_stats[collection_id]["percentage"] / 100
        )
        same_collection_ratio = 0.3 + 0.5 * current_collection_percentage
        same_collection_count = max(1, int(num_negatives * same_collection_ratio))

        negatives: List[str] = []

        # 随机采样
        if total_candidates > 1000 and hasattr(rng, "random"):
            # 合并候选并按类型标记
            all_candidates = same_collection_candidates + other_collection_candidates
            same_count = len(same_collection_candidates)

            # 计算采样索引
            if len(all_candidates) >= num_negatives:
                sampled_indices = rng.sample(range(len(all_candidates)), num_negatives)
            else:
                sampled_indices = range(len(all_candidates))

            # 根据索引和类型筛选样本
            same_sampled = 0
            for idx in sampled_indices:
                if idx < same_count and same_sampled < same_collection_count:
                    negatives.append(all_candidates[idx])
                    same_sampled += 1
                elif idx >= same_count:
                    negatives.append(all_candidates[idx])
        else:
            # 小数据集
            # 从同知识库采样
            if same_collection_count > 0 and same_collection_candidates:
                actual_same_count = min(
                    same_collection_count, len(same_collection_candidates)
                )
                if actual_same_count <= len(same_collection_candidates):
                    negatives.extend(
                        rng.sample(same_collection_candidates, actual_same_count)
                    )
                else:
                    negatives.extend(same_collection_candidates[:actual_same_count])

            # 从其他知识库采样
            needed_other = num_negatives - len(negatives)
            if needed_other > 0 and other_collection_candidates:
                actual_other_count = min(needed_other, len(other_collection_candidates))
                if actual_other_count <= len(other_collection_candidates):
                    negatives.extend(
                        rng.sample(other_collection_candidates, actual_other_count)
                    )
                else:
                    negatives.extend(other_collection_candidates[:actual_other_count])

        # 如果样本不足，从剩余候选中补充
        if len(negatives) < num_negatives:
            remaining_needed = num_negatives - len(negatives)

            # 使用集合操作提高性能
            negatives_set = set(negatives)
            remaining_candidates = [
                q
                for q in (same_collection_candidates + other_collection_candidates)
                if q not in negatives_set
            ]

            if remaining_candidates:
                if len(remaining_candidates) >= remaining_needed:
                    additional_samples = rng.sample(
                        remaining_candidates, remaining_needed
                    )
                else:
                    additional_samples = remaining_candidates
                negatives.extend(additional_samples)

        return negatives[:num_negatives]  # 确保返回正确数量的样本

    def _compute_collection_stats_optimized(
        self, items: List[Any]
    ) -> Tuple[Dict[str, Dict[str, Any]], int]:
        """统计信息计算"""
        collection_stats: Dict[str, Dict[str, Any]] = {}
        total_data_count = len(items)
        total_index_pairs = 0

        # 批量处理统计信息
        for item in items:
            collection_id = item.collectionId
            if collection_id not in collection_stats:
                collection_stats[collection_id] = {
                    "data_count": 0,
                    "index_pairs": 0,
                    "percentage": 0.0,
                }
            collection_stats[collection_id]["data_count"] += 1
            collection_stats[collection_id]["index_pairs"] += len(item.indexes)
            total_index_pairs += len(item.indexes)

        # 计算各库占比
        for collection_id in collection_stats:
            collection_stats[collection_id]["percentage"] = (
                collection_stats[collection_id]["data_count"] / total_data_count * 100
            )

        return collection_stats, total_index_pairs

    async def _build_fine_tune_data(
        self,
        items: List[Any],
        min_negative_samples: int,
        max_negative_samples: int,
        include_original_q: bool,
        request_id: str,
    ) -> Dict[str, Any]:
        # 输入验证
        if not items:
            return {
                "total_items": 0,
                "total_samples": 0,
                "positive_samples": 0,
                "negative_samples": 0,
                "processing_time": 0.0,
                "samples": [],
                "statistics": {},
                "collection_stats": {},
            }

        if min_negative_samples < 0 or max_negative_samples < 0:
            raise ValueError(
                f"Negative sampling parameters must be non-negative: min={min_negative_samples}, max={max_negative_samples}"
            )

        if min_negative_samples > max_negative_samples:
            raise ValueError(
                f"min_negative_samples ({min_negative_samples}) cannot be greater than max_negative_samples ({max_negative_samples})"
            )

        start_time = time.time()

        logger.info(f"开始并发处理 {len(items)} 个数据项，请求ID: {request_id}")

        # 1. 统计信息计算
        collection_stats, total_index_pairs = self._compute_collection_stats_optimized(
            items
        )
        logger.info(
            f"统计完成：{len(collection_stats)} 个知识库，{total_index_pairs} 个问题对"
        )

        # 2. 预构建映射表
        precomputed_start = time.time()
        precomputed = self._build_precomputed_data(items, collection_stats.keys())
        precomputed_time = time.time() - precomputed_start
        logger.info(
            f"预构建映射表完成，耗时: {precomputed_time:.3f}s，{len(precomputed.all_questions)} 个唯一问题"
        )

        # 3. 并发构建样本
        all_samples: List[Any] = []
        collection_samples: Dict[str, List[Any]] = {
            collection_id: [] for collection_id in collection_stats
        }

        # 分块处理以实现并发
        if len(items) > self.chunk_size and self.max_workers > 1:
            # 分块
            chunks = []
            for i in range(0, len(items), self.chunk_size):
                chunk = items[i : i + self.chunk_size]
                chunks.append((chunk, i))

            # 并发处理
            loop = asyncio.get_event_loop()
            tasks = []

            for chunk, start_idx in chunks:
                task = loop.run_in_executor(
                    self.executor,
                    self._process_items_chunk,
                    chunk,
                    precomputed,
                    collection_stats,
                    min_negative_samples,
                    max_negative_samples,
                    include_original_q,
                    start_idx,
                )
                tasks.append(task)

            # 等待所有任务完成
            chunk_results = await asyncio.gather(*tasks)

            # 合并结果
            for chunk_samples in chunk_results:
                all_samples.extend(chunk_samples)
                for sample in chunk_samples:
                    collection_samples[sample.collection_id].append(sample)
        else:
            # 小数据量串行处理
            for item_index, item in enumerate(items):
                item_id = item.dataId
                collection_id = item.collectionId

                # 构建正样本：每个indexes中的[q1, q2]对
                for pair_index, pair in enumerate(item.indexes):
                    if len(pair) < 2:
                        continue

                    q1, q2 = pair[0], pair[1]

                    # 负样本采样
                    negatives = self._sample_negatives_optimized(
                        precomputed=precomputed,
                        q1=q1,
                        q2=q2,
                        item_id=item_id,
                        collection_id=collection_id,
                        collection_stats=collection_stats,
                        min_negative_samples=min_negative_samples,
                        max_negative_samples=max_negative_samples,
                        worker_id=item_index % len(self._random_generators),
                    )

                # 创建样本
                sample = self._create_fine_tune_sample(
                    query=q1,
                    positive=q2,
                    negatives=negatives,
                    source_id=item_id,
                    collection_id=collection_id,
                    original_q=item.q if include_original_q else None,
                    original_a=item.a if include_original_q else None,
                    metadata={
                        "pair_index": pair_index,
                        "source_type": "index_pair",
                        "negative_count": len(negatives),
                    },
                )
                all_samples.append(sample)
                collection_samples[collection_id].append(sample)

        # 4. 性能统计和监控
        processing_time = time.time() - start_time
        logger.info(
            f"样本生成完成：{len(all_samples)} 个样本，耗时: {processing_time:.3f}s，速度: {len(all_samples) / processing_time:.1f} 样本/秒"
        )

        # 基础统计信息
        base_statistics = {
            "unique_questions": len(precomputed.all_questions),
            "total_index_pairs": total_index_pairs,
            "average_negatives_per_sample": sum(
                len(sample.negatives) for sample in all_samples
            )
            / max(len(all_samples), 1),
            "samples_per_item": len(all_samples) / max(len(items), 1),
            "processing_speed": len(all_samples) / max(processing_time, 0.001),
            "concurrent_processing": len(items) > self.chunk_size
            and self.max_workers > 1,
        }

        # 知识库统计信息
        collection_statistics: Dict[str, Dict[str, Any]] = {}
        for collection_id, stats in collection_stats.items():
            collection_samples_count = len(collection_samples.get(collection_id, []))
            collection_statistics[collection_id] = {
                "data_count": stats["data_count"],
                "index_pairs": stats["index_pairs"],
                "percentage": round(stats["percentage"], 2),
                "actual_samples": collection_samples_count,
                "samples_per_item": collection_samples_count
                / max(stats["data_count"], 1),
            }

        # 合并统计信息
        total_actual_samples = sum(
            stats["actual_samples"] for stats in collection_statistics.values()
        )
        merged_statistics = {
            **base_statistics,
            "collections": collection_statistics,
            "total_collections": len(collection_stats),
            "total_actual_samples": total_actual_samples,
            "collection_distribution": {
                cid: {
                    "count": stats["data_count"],
                    "percentage": round(stats["percentage"], 2),
                }
                for cid, stats in collection_stats.items()
            },
        }

        return {
            "total_items": len(items),
            "total_samples": len(all_samples),
            "positive_samples": len(all_samples),  # 是正样本
            "negative_samples": sum(
                len(sample.negatives) for sample in all_samples
            ),  # 总负样本数量
            "processing_time": processing_time,
            "samples": all_samples,
            "statistics": merged_statistics,
            "collection_stats": collection_statistics,  # 单独返回知识库统计以便于使用
        }

    def _create_fine_tune_sample(
        self,
        query: str,
        positive: str,
        negatives: List[str],
        source_id: str,
        collection_id: str,
        original_q: Optional[str] = None,
        original_a: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FineTuneSample:
        """创建微调样本"""
        return FineTuneSample(
            query=query,
            positive=[positive],
            negatives=negatives,
            source_id=source_id,
            collection_id=collection_id,
            original_q=original_q,
            original_a=original_a,
            metadata=metadata or {},
        )

    def clear_cache(self) -> None:
        """清理预计算缓存"""
        self._precomputed_cache.clear()
        logger.info("预计算缓存已清理")

    def optimize_for_dataset_size(self, dataset_size: int) -> None:
        """根据数据集大小动态优化参数"""
        if dataset_size < 100:
            self.chunk_size = 50
            self.max_workers = min(2, mp.cpu_count())
        elif dataset_size < 1000:
            self.chunk_size = 100
            self.max_workers = min(4, mp.cpu_count())
        elif dataset_size < 10000:
            self.chunk_size = 200
            self.max_workers = min(8, mp.cpu_count())
        else:
            self.chunk_size = 500
            self.max_workers = mp.cpu_count()

        logger.info(
            f"根据数据集大小({dataset_size})优化参数: chunk_size={self.chunk_size}, max_workers={self.max_workers}"
        )

    def __del__(self):
        """清理资源"""
        try:
            if hasattr(self, "executor") and self.executor:
                self.executor.shutdown(wait=False)
        except Exception as e:
            logger.warning(f"清理执行器时出错: {e}")

        try:
            self.clear_cache()
        except Exception as e:
            logger.warning(f"清理缓存时出错: {e}")
