import asyncio
from typing import Any, Dict, List

from diting_core.cases.llm_case import LLMCase
from diting_core.metrics import BaseMetric
from diting_core.optimization import PromptConfig
from diting_core.optimization.datasets import BaseDataset


def evaluate_prompt_sync(
    prompt_config: PromptConfig,
    dataset: BaseDataset,
    metric: BaseMetric,
    max_concurrency: int,
    **kwargs: Any,
) -> float:
    """Blocking wrapper around the async evaluator."""

    async def _runner() -> float:
        return await evaluate_prompt(prompt_config, dataset, metric, max_concurrency)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Running inside an event loop (e.g., pytest-asyncio); spawn a thread
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _runner())
                return future.result()
        return loop.run_until_complete(_runner())
    except RuntimeError:
        # No running loop
        return asyncio.run(_runner())


async def evaluate_prompt(
    prompt_config: PromptConfig,
    dataset: BaseDataset,
    metric: BaseMetric,
    max_concurrency: int,
    **kwargs: Any,
) -> float:
    """Shared async implementation with bounded concurrency."""
    samples = dataset.get_items()
    if not samples:
        raise ValueError(f"Dataset '{dataset.name}' has no items")

    semaphore = asyncio.Semaphore(max_concurrency)

    async def _evaluate_single(sample: Dict[str, Any]) -> float:
        async with semaphore:
            user_input = sample.get("input", "")
            expected_output = sample.get("expected_output", "")
            context = sample.get("context")
            retrieval_context = sample.get("retrieval_context")

            actual_output = await prompt_config.execute(user_input)

            test_case = LLMCase(
                user_input=user_input,
                actual_output=actual_output,
                expected_output=expected_output,
                context=context if isinstance(context, list) else None,
                retrieval_context=retrieval_context
                if isinstance(retrieval_context, list)
                else None,
            )

            metric_value = await metric.compute(test_case)
            return metric_value.score if metric_value.score is not None else 0.0

    scores = await asyncio.gather(*(_evaluate_single(sample) for sample in samples))
    return sum(scores) / len(scores) if scores else 0.0


async def evaluate_prompt_with_detail(
    prompt_config: PromptConfig,
    dataset: BaseDataset,
    metric: BaseMetric,
    max_concurrency: int,
    **kwargs: Any,
) -> tuple[float, list[dict[str, Any]]]:
    """
    在数据集上评估提示词

    此方法：
    1. 从数据集采样测试用例
    2. 为每个测试用例生成LLM响应
    3. 计算指标分数并收集详细原因
    4. 返回平均分数和测试结果（包含原因）

    Args:
        prompt_config: 要评估的提示配置
        dataset: 评估数据集
        metric: 评估指标
        max_concurrency: 评估并发

    Returns:
        (平均分数, 测试结果) 的元组
        其中 test_results 是包含以下键的字典列表：
        - input: str - 输入文本
        - output: str - 模型输出
        - expected: str - 期望输出
        - score: float - 分数值
        - reason: str - 详细原因（根因分析必需）

    Raises:
        ValueError: 如果提示配置未正确设置LLM
    """
    samples = dataset.get_items()
    if not samples:
        raise ValueError(f"Dataset '{dataset.name}' has no items")

    semaphore = asyncio.Semaphore(max_concurrency)
    results: List[Dict[str, Any]] = []

    async def _evaluate_single(
        sample: Dict[str, Any], final_results: List[Dict[str, Any]]
    ) -> None:
        async with semaphore:
            user_input = sample.get("input", "")
            expected_output = sample.get("expected_output", "")
            context = sample.get("context")
            retrieval_context = sample.get("retrieval_context")

            actual_output = await prompt_config.execute(user_input)

            test_case = LLMCase(
                user_input=user_input,
                actual_output=actual_output,
                expected_output=expected_output,
                context=context if isinstance(context, list) else None,
                retrieval_context=retrieval_context
                if isinstance(retrieval_context, list)
                else None,
            )

            metric_value = await metric.compute(test_case)
            final_results.append(
                {
                    "input": user_input,
                    "output": actual_output,
                    "expected": expected_output,
                    "score": metric_value.score
                    if metric_value.score is not None
                    else 0.0,
                    "reason": metric_value.reason or "No reason provided",
                }
            )

    await asyncio.gather(*(_evaluate_single(sample, results) for sample in samples))
    avg_score = sum(r["score"] for r in results) / len(results) if results else 0.0
    return avg_score, results
