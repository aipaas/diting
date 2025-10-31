import asyncio
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from diting_core.callbacks.base import Callbacks
from diting_core.cases.llm_case import LLMCase, LLMCaseParams
from diting_core.metrics import BaseMetric, MetricValue
from diting_optimizer.target.prompt_config import PromptConfig
from diting_optimizer.datasets.base_dataset import BaseDataset


class TestResult(BaseModel):
    __test__ = False  # 关键：阻止pytest将其识别为测试类
    test_case: LLMCase
    metric_value: MetricValue


class ExperimentResult(BaseModel):
    experiment_name: Optional[str]
    test_results: List[TestResult]

    @property
    def avg_score(self) -> float:
        """
        计算所有 MetricValue 中有效 score 的平均值

        Returns:
            平均值（float）；若没有有效 score，返回 None
        """
        # 收集所有非 None 的 score
        scores = []
        for test_result in self.test_results:
            if test_result.metric_value.score is not None:  # 只考虑有效分数
                scores.append(test_result.metric_value.score)

        # 计算平均值（处理空列表情况）
        if not scores:
            raise ValueError(
                f"Experiment '{self.experiment_name}' has no valid scores to calculate average. "
                "Check if metric_values contain non-None 'score' fields."
            )
        return sum(scores) / len(scores)


def sort_test_results_by_failure(
    test_results: list[TestResult], ascending: bool = True, in_place: bool = True
) -> list[TestResult]:
    """Sort a list of TestResult objects by failure severity based on metric scores.

    Sorts test results primarily by their `metric_value.score` (lower scores indicate
    more severe failures). Handles `None` scores by treating them as the most severe
    failures (equivalent to a score of 0.0).

    Args:
        test_results: List of TestResult objects to be sorted.
        ascending: If True, sort in ascending order (more severe failures first,
            lower scores first). If False, sort in descending order (less severe
            failures first, higher scores first). Defaults to True.
        in_place: If True, sorts the list in-place (modifies the original list and
            uses less memory). If False, returns a new sorted list without modifying
            the original. Defaults to True.

    Returns:
        The sorted list of TestResult objects. If `in_place=True`, this is the same
        list object passed in (modified). If `in_place=False`, this is a new list.

    Notes:
        - TestResult objects with `metric_value.score is None` are treated as having
          a score of 0.0 (most severe failure).
        - Uses Python's Timsort algorithm, which is stable (preserves relative order
          of elements with equal scores).
        - In-place sorting has O(1) additional memory complexity, while non-in-place
          sorting has O(n) memory complexity (where n is the length of `test_results`).
    """

    def _get_score_key(test_result: TestResult) -> float:
        """Helper to extract the sorting key (metric score, handling None)."""
        return (
            test_result.metric_value.score
            if test_result.metric_value.score is not None
            else 0.0
        )

    if in_place:
        test_results.sort(key=_get_score_key, reverse=not ascending)
        return test_results
    else:
        return sorted(test_results, key=_get_score_key, reverse=not ascending)


def evaluate_prompt_sync(
    prompt_config: PromptConfig,
    dataset: BaseDataset,
    metric: BaseMetric,
    max_concurrency: int = 5,
    n_samples: Optional[int] = None,
    callbacks: Optional[Callbacks] = None,
    **kwargs: Any,
) -> ExperimentResult:
    """Blocking wrapper around the async evaluator."""

    async def _runner() -> ExperimentResult:
        return await evaluate_prompt(
            prompt_config,
            dataset,
            metric,
            max_concurrency,
            n_samples=n_samples,
            callbacks=callbacks,
        )

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
    max_concurrency: int = 5,
    n_samples: Optional[int] = None,
    callbacks: Optional[Callbacks] = None,
    **kwargs: Any,
) -> ExperimentResult:
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
        n_samples: 数据集单次采样数据
        callbacks: 注册给评估的回调

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
    samples = dataset.get_items(n_samples=n_samples)
    if not samples:
        raise ValueError(f"Dataset '{dataset.name}' has no items")

    experiment_name = dataset.name + ">|" + metric.name + "|"
    semaphore = asyncio.Semaphore(max_concurrency)
    test_results: List[TestResult] = []

    async def _evaluate_single(
        sample: Dict[str, Any], final_results: List[TestResult]
    ) -> None:
        async with semaphore:
            user_input = sample.get(LLMCaseParams.USER_INPUT.value, "")
            expected_output = sample.get(LLMCaseParams.EXPECTED_OUTPUT.value, "")
            context = sample.get(LLMCaseParams.CONTEXT.value)
            actual_output = await prompt_config.execute(sample)

            test_case = LLMCase(
                user_input=user_input,
                actual_output=actual_output,
                expected_output=expected_output,
                context=context if isinstance(context, list) else None,
                metadata={"dataset_item_id": sample.get("id")},
            )
            metric_value = await metric.compute(test_case, callbacks=callbacks)
            final_results.append(
                TestResult(test_case=test_case, metric_value=metric_value)
            )

    await asyncio.gather(
        *(_evaluate_single(sample, test_results) for sample in samples)
    )
    # sort_test_results_by_failure(test_results)
    return ExperimentResult(experiment_name=experiment_name, test_results=test_results)
