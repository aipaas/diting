"""
任务执行器 - 支持并发和串行执行
"""

import asyncio
from enum import Enum
from typing import List, Dict, Any, Callable, Optional

from .logging_config import get_logger

logger = get_logger(__name__)


class ExecutionMode(Enum):
    """执行模式枚举"""

    SEQUENTIAL = "sequential"  # 串行执行
    PARALLEL = "parallel"  # 并发执行
    BATCH = "batch"  # 批量执行（分批并发）


class TaskExecutor:
    """任务执行器"""

    def __init__(
        self, max_workers: int = 4, mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    ):
        self.max_workers = max_workers
        self.mode = mode
        self.semaphore = asyncio.Semaphore(max_workers)

    async def execute(
        self, tasks: List[Any], run_func: Callable, batch_size: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        执行任务列表

        Args:
            tasks: 任务列表
            run_func: 运行单个任务的函数
            batch_size: 批量模式下的批次大小

        Returns:
            任务结果列表
        """
        if not tasks:
            return []

        if self.mode == ExecutionMode.SEQUENTIAL:
            return await self._execute_sequential(tasks, run_func)
        elif self.mode == ExecutionMode.PARALLEL:
            return await self._execute_parallel(tasks, run_func)
        elif self.mode == ExecutionMode.BATCH:
            batch_size = batch_size or min(4, len(tasks))
            return await self._execute_batch(tasks, run_func, batch_size)
        else:
            raise ValueError(f"不支持的执行模式: {self.mode}")

    async def _execute_sequential(
        self, tasks: List[Any], run_func: Callable
    ) -> List[Dict[str, Any]]:
        """串行执行任务"""
        results = []

        for i, task in enumerate(tasks, 1):
            logger.info(f"[进度 {i}/{len(tasks)}] 串行执行任务: {task.name}")
            try:
                result = await run_func(task)
                results.append(result)
            except Exception as e:
                logger.error(f"任务 {task.name} 执行失败: {str(e)}")
                # 记录失败的任务，但继续执行后续任务
                results.append(
                    {"task_name": task.name, "error": str(e), "status": "failed"}
                )

        return results

    async def _execute_parallel(
        self, tasks: List[Any], run_func: Callable
    ) -> List[Dict[str, Any]]:
        """并发执行任务"""

        async def run_with_semaphore(task):
            async with self.semaphore:
                logger.info(f"[并发] 开始执行任务: {task.name}")
                return await run_func(task)

        # 创建所有任务
        coroutines = [run_with_semaphore(task) for task in tasks]

        # 并发执行
        results = await asyncio.gather(*coroutines, return_exceptions=True)

        # 处理异常
        processed_results = []
        for task, result in zip(tasks, results):
            if isinstance(result, Exception):
                logger.error(f"任务 {task.name} 执行失败: {str(result)}")
                processed_results.append(
                    {"task_name": task.name, "error": str(result), "status": "failed"}
                )
            else:
                processed_results.append(result)

        return processed_results

    async def _execute_batch(
        self, tasks: List[Any], run_func: Callable, batch_size: int
    ) -> List[Dict[str, Any]]:
        """批量执行任务（分批并发）"""
        results = []
        total_batches = (len(tasks) + batch_size - 1) // batch_size

        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(tasks))
            batch_tasks = tasks[start_idx:end_idx]

            logger.info(
                f"[批次 {batch_idx + 1}/{total_batches}] 执行 {len(batch_tasks)} 个任务"
            )

            # 并发执行当前批次
            batch_results = await self._execute_parallel(batch_tasks, run_func)
            results.extend(batch_results)

            # 批次间延迟
            if batch_idx < total_batches - 1:
                logger.debug("批次间等待 2 秒...")
                await asyncio.sleep(2)

        return results
