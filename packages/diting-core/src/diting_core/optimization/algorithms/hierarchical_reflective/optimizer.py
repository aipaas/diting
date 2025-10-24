"""Hierarchical Reflective Optimizer.

Adapted from Opik's HierarchicalReflectiveOptimizer with minimal changes for Diting.
Main adaptations:
- Uses Diting's BaseOptimizer, PromptConfig, BaseDataset, BaseMetric interfaces
- Uses Diting's LLM for structured outputs
- Simplified reporting (removed Rich console outputs)
- Async-first design aligned with Diting conventions
"""

import logging
import copy
from datetime import datetime
from typing import Any, Optional, List, Dict

from diting_core.models.llms.base_model import BaseLLM, PydanticClass
from diting_core.optimization.base_optimizer import BaseOptimizer
from diting_core.optimization.target.prompt_config import PromptConfig
from diting_core.optimization.target.base_config import BaseConfig
from diting_core.optimization.datasets.base_dataset import BaseDataset
from diting_core.metrics.base_metric import BaseMetric
from diting_core.optimization.optimization_result import OptimizationResult

from .root_cause_analyzer import HierarchicalRootCauseAnalyzer
from .types import (
    FailureMode,
    ImprovedPrompt,
    HierarchicalRootCauseAnalysis,
)
from .prompts import IMPROVE_PROMPT_TEMPLATE
from diting_core.optimization.infra.eval_task import evaluate_prompt_with_detail

logger = logging.getLogger(__name__)


class HierarchicalReflectiveOptimizer(BaseOptimizer):
    """
    分层反思优化器，使用分层根因分析改进提示词

    此算法使用两阶段分层方法：批量分析失败模式，然后综合结果识别统一失败模式。
    适用于复杂提示词的系统性改进。

    重构改进：
    - 适配新的 BaseOptimizer 通用接口
    - 支持 PromptConfig 自包含执行逻辑

    Args:
        llm: Diting LLM 实例，用于生成结构化输出
        seed: 随机种子，用于可重现性 (默认: 42)
        max_parallel_batches: 分层根因分析期间并发处理的最大批次数 (默认: 5)
        batch_size: 根因分析的每批测试用例数 (默认: 25)
        max_iterations: 最大优化迭代次数 (默认: 5)
        convergence_threshold: 相对改进低于此阈值时停止 (默认: 0.01)
        max_retries: 每个失败模式的最大重试次数 (默认: 2)
        num_eval_threads: Number of parallel threads for evaluation (default: 12)
    """

    DEFAULT_MAX_ITERATIONS = 5
    DEFAULT_CONVERGENCE_THRESHOLD = 0.01  # 改进小于1%时停止

    def __init__(
        self,
        llm: Optional[BaseLLM] = None,
        seed: int = 42,
        max_parallel_batches: int = 5,
        batch_size: int = 25,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        convergence_threshold: float = DEFAULT_CONVERGENCE_THRESHOLD,
        max_retries: int = 2,
        num_eval_threads: int = 12,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.llm = llm
        # TODO Integrate with callbacks
        self.llm_call_count = 0
        self.seed = seed
        self.max_parallel_batches = max_parallel_batches
        self.batch_size = batch_size
        self.max_iterations = max_iterations
        self.convergence_threshold = convergence_threshold
        self.max_retries = max_retries
        self.num_eval_threads = num_eval_threads

        # Initialize hierarchical analyzer
        self._hierarchical_analyzer = HierarchicalRootCauseAnalyzer(
            call_model_fn=self._call_model_async,
            seed=self.seed,
            max_parallel_batches=self.max_parallel_batches,
            batch_size=self.batch_size,
        )

    async def _call_model_async(
        self,
        messages: list[dict[str, str]],
        seed: int,
        response_model: Optional[PydanticClass] = None,  # noqa: UP006,
    ) -> Any:
        """
        调用LLM生成结构化输出

        Args:
            messages: 消息字典列表
            seed: 随机种子，用于可重现性
            response_model: 用于结构化输出的Pydantic模型

        Returns:
            response_model的实例

        Raises:
            ValueError: 如果LLM未配置
        """
        if self.llm is None:
            raise ValueError(
                "LLM not configured. "
                "Provide 'llm' parameter when creating the optimizer_name. "
                "\n\nExample:"
                "\n  from diting_core.models.llms import SomeLLM"
                "\n  llm = SomeLLM(...)"
                "\n  optimizer_name = HierarchicalReflectiveOptimizer(llm=llm)"
            )

        prompt_str = PromptConfig.format_messages(messages)

        # 使用LLM的结构化输出方法
        return await self.llm.generate_structured_output(
            prompt=prompt_str,
            schema=response_model,
            seed=seed,
        )

    @staticmethod
    def _calculate_improvement(current_score: float, previous_score: float) -> float:
        """Calculate the improvement percentage between scores."""
        return (
            (current_score - previous_score) / previous_score
            if previous_score > 0
            else 0
        )

    async def _hierarchical_root_cause_analysis(
        self, test_results: list[dict[str, Any]]
    ) -> HierarchicalRootCauseAnalysis:
        """
        Perform hierarchical root cause analysis on test results.

        Args:
            test_results: List of test results from evaluation

        Returns:
            HierarchicalRootCauseAnalysis with unified failure modes
        """
        logger.debug("Performing hierarchical root cause analysis...")
        return await self._hierarchical_analyzer.analyze_async(test_results)

    async def _improve_prompt(
        self,
        prompt_config: PromptConfig,
        root_cause: FailureMode,
        attempt: int = 1,
    ) -> ImprovedPrompt:
        """
        Improve the prompt based on the root cause analysis.

        Args:
            prompt_config: Current prompt to improve
            root_cause: The failure mode to address
            attempt: Attempt number (1-indexed). Used to vary seed for retries.

        Returns:
            ImprovedPrompt with reasoning and improved messages
        """
        # Format current prompt for improvement
        current_messages = prompt_config.messages or []
        if not current_messages and prompt_config.system:
            current_messages = [{"role": "system", "content": prompt_config.system}]
            if prompt_config.user:
                current_messages.append({"role": "user", "content": prompt_config.user})

        improve_prompt_prompt = IMPROVE_PROMPT_TEMPLATE.format(
            current_prompt=current_messages,
            failure_mode_name=root_cause.name,
            failure_mode_description=root_cause.description,
            failure_mode_root_cause=root_cause.root_cause,
        )

        # Vary seed based on attempt to avoid cache hits
        attempt_seed = self.seed + (attempt - 1) * 1000

        if attempt > 1:
            logger.debug(
                f"Retry attempt {attempt}: Using seed {attempt_seed} (base seed: {self.seed})"
            )

        improve_prompt_response = await self._call_model_async(
            messages=[{"role": "user", "content": improve_prompt_prompt}],
            seed=attempt_seed,
            response_model=ImprovedPrompt,
        )

        return improve_prompt_response

    async def _generate_and_evaluate_improvement(
        self,
        root_cause: FailureMode,
        best_prompt: PromptConfig,
        best_score: float,
        dataset: BaseDataset,
        metric: BaseMetric,
        attempt: int,
        max_attempts: int,
        n_samples: Optional[int] = None,
    ) -> tuple[PromptConfig, float, list[dict[str, Any]]]:
        """
        Generate and evaluate a single improvement attempt for a failure mode.

        Args:
            root_cause: The failure mode to address
            best_prompt: The current best prompt to improve upon
            best_score: The current best score (for comparison)
            dataset: Dataset to evaluate on
            metric: Metric function
            attempt: Current attempt number (1-indexed)
            max_attempts: Total number of attempts

        Returns:
            Tuple of (improved_prompt, improved_score, improved_test_results)
        """
        # Generate improvement
        logger.info(
            f"Generating improvement for failure mode '{root_cause.name}' (attempt {attempt}/{max_attempts})"
        )

        improved_prompt_response = await self._improve_prompt(
            prompt_config=best_prompt, root_cause=root_cause, attempt=attempt
        )

        logger.debug(f"Improvement reasoning: {improved_prompt_response.reasoning}")

        # Convert to PromptConfig
        improved_prompt = PromptConfig(
            name=best_prompt.name,
            messages=[
                {"role": msg.role, "content": msg.content}
                for msg in improved_prompt_response.messages
            ],
            model_params=copy.deepcopy(best_prompt.model_params),
            llm=best_prompt.llm,
        )

        # Evaluate improved prompt
        logger.info(f"Evaluating improved prompt (attempt {attempt}/{max_attempts})")
        improved_score, improved_test_results = await evaluate_prompt_with_detail(
            prompt_config=improved_prompt,
            dataset=dataset,
            metric=metric,
            max_concurrency=self.num_eval_threads,
            n_samples=n_samples,
        )

        logger.info(
            f"Improved score: {improved_score:.4f} (baseline: {best_score:.4f})"
        )

        return improved_prompt, improved_score, improved_test_results

    async def _optimize(
        self,
        config: BaseConfig,
        dataset: BaseDataset,
        metric: BaseMetric,
        n_samples: Optional[int] = None,
        **kwargs: Any,
    ) -> OptimizationResult:
        """
        分层反思优化的主要逻辑

        Args:
            config: 初始配置（必须是PromptConfig）
            dataset: 要优化的数据集
            metric: 要优化的指标
            **kwargs: 附加参数

        Returns:
            包含优化提示和元数据的OptimizationResult
        """
        # 验证配置类型
        if not isinstance(config, PromptConfig):
            raise ValueError(
                f"HierarchicalReflectiveOptimizer requires PromptConfig, "
                f"got {type(config).__name__}"
            )

        prompt_config = config
        history: List[Dict[str, Any]] = []

        logger.info(
            f"Starting HierarchicalReflectiveOptimizer with max_iterations={self.max_iterations}"
        )

        # Evaluate baseline
        logger.info("Evaluating baseline prompt...")
        baseline_score, test_results = await evaluate_prompt_with_detail(
            prompt_config=prompt_config,
            dataset=dataset,
            metric=metric,
            max_concurrency=self.num_eval_threads,
            n_samples=n_samples,
        )
        history.append(
            {
                "iteration": 0,
                "timestamp": datetime.utcnow().isoformat(),
                "prompt": prompt_config.model_dump(),
                "score": baseline_score,
                "test_results": test_results,
                "stage": "baseline",
            }
        )

        logger.info(f"Baseline score: {baseline_score:.4f}")

        # Track baseline and best
        best_score = baseline_score
        best_prompt = prompt_config

        # Multi-iteration optimization loop
        iteration = 0
        previous_iteration_score = baseline_score

        for iteration in range(1, self.max_iterations + 1):
            logger.info(f"Starting iteration {iteration}/{self.max_iterations}")

            # Perform hierarchical root cause analysis
            logger.info("Performing hierarchical root cause analysis...")
            hierarchical_analysis = await self._hierarchical_root_cause_analysis(
                test_results
            )

            logger.info(
                f"Identified {len(hierarchical_analysis.unified_failure_modes)} unified failure modes"
            )
            logger.debug(f"Synthesis notes: {hierarchical_analysis.synthesis_notes}")

            # Address each failure mode
            for idx, root_cause in enumerate(
                hierarchical_analysis.unified_failure_modes, 1
            ):
                logger.info(
                    f"Addressing failure mode {idx}/{len(hierarchical_analysis.unified_failure_modes)}: {root_cause.name}"
                )

                # Try multiple attempts if needed
                max_attempts = self.max_retries + 1
                improved_prompt = None
                improved_score = None
                improved_test_results = None

                for attempt in range(1, max_attempts + 1):
                    # Generate and evaluate improvement
                    (
                        improved_prompt,
                        improved_score,
                        improved_test_results,
                    ) = await self._generate_and_evaluate_improvement(
                        root_cause=root_cause,
                        best_prompt=best_prompt,
                        best_score=best_score,
                        dataset=dataset,
                        metric=metric,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        n_samples=n_samples,
                    )
                    history.append(
                        {
                            "iteration": iteration,
                            "sub_iteration": attempt,
                            "timestamp": datetime.utcnow().isoformat(),
                            "root_cause": root_cause.model_dump(),
                            "prompt": improved_prompt.model_dump(),
                            "score": improved_score,
                            "test_results": improved_test_results,
                            "stage": "optimizing",
                        }
                    )

                    # Check if we got improvement
                    if improved_score > best_score:
                        logger.info(
                            f"Improvement found for '{root_cause.name}' on attempt {attempt}"
                        )
                        break

                    # No improvement - should we retry?
                    if attempt < max_attempts:
                        logger.info(
                            f"Retry attempt {attempt + 1}/{max_attempts} for failure mode '{root_cause.name}'"
                        )
                    else:
                        logger.debug(
                            f"No improvement after {attempt} attempts for '{root_cause.name}'"
                        )

                # Check if final result is an improvement
                if (
                    improved_score is not None
                    and improved_prompt is not None
                    and improved_score > best_score
                ):
                    improvement = self._calculate_improvement(
                        improved_score, best_score
                    )
                    logger.info(
                        f"Updated best prompt: score {improved_score:.4f} (+{improvement:.2%})"
                    )

                    # Update best
                    best_score = improved_score
                    best_prompt = improved_prompt
                    test_results = improved_test_results
                else:
                    logger.debug(
                        f"Keeping previous best prompt, no improvement from '{root_cause.name}'"
                    )

            # Check for convergence after iteration
            iteration_improvement = self._calculate_improvement(
                best_score, previous_iteration_score
            )

            logger.info(
                f"Iteration {iteration} complete. Score: {best_score:.4f}, "
                f"Improvement: {iteration_improvement:.2%}"
            )

            # Stop if improvement is below convergence threshold
            if abs(iteration_improvement) < self.convergence_threshold:
                logger.info(
                    f"Convergence achieved: improvement ({iteration_improvement:.2%}) "
                    f"below threshold ({self.convergence_threshold:.2%}). "
                    f"Stopping after {iteration} iterations."
                )
                break

            # Update previous score for next iteration
            previous_iteration_score = best_score

        # Calculate final improvement
        final_improvement = self._calculate_improvement(best_score, baseline_score)
        logger.info(
            f"Optimization complete: final score {best_score:.4f} "
            f"(+{final_improvement:.2%} from baseline)"
        )

        # Create result
        return OptimizationResult(
            optimizer_name=self.__class__.__name__,
            best_prompt=best_prompt,
            best_score=best_score,
            metric_name=metric.__class__.__name__,
            initial_prompt=prompt_config,
            initial_score=baseline_score,
            improvement=final_improvement,
            history=history,
            details={
                "optimize_model": config.llm or self.llm,
                "max_iterations": self.max_iterations,
                "convergence_threshold": self.convergence_threshold,
                "max_retries": self.max_retries,
            },
            total_llm_calls=self.llm_call_count,
            iterations=iteration,
        )
