"""Hierarchical Reflective Optimizer.

Adapted from Opik's HierarchicalReflectiveOptimizer with minimal changes for Diting.
Enhanced with basic error handling and code quality improvements.

Main adaptations:
- Uses Diting's BaseOptimizer, PromptConfig, BaseDataset, BaseMetric interfaces
- Uses Diting's LLM for structured outputs
- Simplified reporting (removed Rich console outputs)
- Async-first design aligned with Diting conventions
- Added basic error handling and code standardization
"""

import copy
import logging
from typing import Any, Optional, List

from diting_core.callbacks.base import Callbacks
from diting_core.callbacks.manager import new_group
from diting_core.metrics.base_metric import BaseMetric
from diting_core.models.llms.base_model import BaseLLM, PydanticClass
from diting_optimizer.algorithms.prompt.prompt_messages.hierarchical_reflective.prompts import (
    IMPROVE_PROMPT_TEMPLATE,
)
from diting_optimizer.algorithms.prompt.prompt_messages.hierarchical_reflective.root_cause_analyzer import (
    HierarchicalRootCauseAnalyzer,
)
from diting_optimizer.algorithms.prompt.prompt_messages.hierarchical_reflective.types import (
    FailureMode,
    ImprovedPrompt,
)
from diting_optimizer.base_optimizer import BaseOptimizer
from diting_optimizer.datasets.base_dataset import BaseDataset
from diting_optimizer.infra.eval_task import evaluate_prompt, ExperimentResult
from diting_optimizer.optimization_result import OptimizationResult, HistoryRecord
from diting_optimizer.target.base_config import BaseConfig
from diting_optimizer.target.prompt_config import PromptConfig

logger = logging.getLogger(__name__)


class HierarchicalReflectiveOptimizer(BaseOptimizer):
    """Hierarchical Reflective Optimizer using layered root cause analysis to improve prompts.

    This algorithm uses a two-stage hierarchical approach: batch analysis of failure modes,
    then comprehensive result analysis to identify unified failure patterns.
    Suitable for systematic improvement of complex prompts.

    Attributes:
        llm: Diting LLM instance for generating structured outputs
        seed: Random seed for reproducibility (default: 42)
        max_parallel_batches: Maximum concurrent batches during root cause analysis (default: 5)
        batch_size: Number of test cases per batch for root cause analysis (default: 25)
        max_iterations: Maximum optimization iterations (default: 5)
        convergence_threshold: Stop when relative improvement below this threshold (default: 0.01)
        max_retries: Maximum retry attempts per failure mode (default: 2)
        num_eval_threads: Number of parallel threads for evaluation (default: 12)
    """

    DEFAULT_MAX_ITERATIONS = 5
    DEFAULT_CONVERGENCE_THRESHOLD = 0.01  # Stop when improvement < 1%

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
        self.seed = seed
        self.max_parallel_batches = max_parallel_batches
        self.batch_size = batch_size
        self.max_iterations = max_iterations
        self.convergence_threshold = convergence_threshold
        self.max_retries = max_retries
        self.num_eval_threads = num_eval_threads

        # Initialize hierarchical analyzer
        self._hierarchical_analyzer = HierarchicalRootCauseAnalyzer(
            call_model_fn=self._call_model,
            seed=self.seed,
            max_parallel_batches=self.max_parallel_batches,
            batch_size=self.batch_size,
        )

    async def _call_model(
        self,
        messages: List[dict[str, str]],
        seed: int,
        response_model: Optional[PydanticClass] = None,  # noqa: UP006,
        callbacks: Optional[Callbacks] = None,
    ) -> Any:
        """
        Call LLM to generate structured output.

        Args:
            messages: List of message dictionaries
            seed: Random seed for reproducibility
            response_model: Pydantic model for structured output
            callbacks: Callback handlers

        Returns:
            Instance of response_model

        Raises:
            ValueError: If LLM is not configured
        """
        if self.llm is None:
            raise ValueError(
                "LLM not configured. "
                "Provide 'llm' parameter when creating the optimizer. "
                "\n\nExample:"
                "\n  from diting_core.models.llms import SomeLLM"
                "\n  llm = SomeLLM(...)"
                "\n  optimizer = HierarchicalReflectiveOptimizer(llm=llm)"
            )

        prompt_str = PromptConfig.format_messages(messages)

        # Use LLM's structured output method
        return await self.llm.generate_structured_output(
            prompt=prompt_str, schema=response_model, seed=seed, callbacks=callbacks
        )

    async def _improve_prompt(
        self,
        prompt_config: PromptConfig,
        root_cause: FailureMode,
        attempt: int = 1,
        callbacks: Optional[Callbacks] = None,
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

        improve_prompt_response = await self._call_model(
            messages=[{"role": "user", "content": improve_prompt_prompt}],
            seed=attempt_seed,
            response_model=ImprovedPrompt,
            callbacks=callbacks,
        )

        return ImprovedPrompt.model_validate(improve_prompt_response)

    async def _generate_and_evaluate_improvement(
        self,
        root_cause: FailureMode,
        best_prompt: PromptConfig,
        dataset: BaseDataset,
        metric: BaseMetric,
        attempt: int,
        n_samples: Optional[int] = None,
        callbacks: Optional[Callbacks] = None,
    ) -> tuple[PromptConfig, ExperimentResult]:
        """
        Generate and evaluate a single improvement attempt for a failure mode.

        Args:
            root_cause: The failure mode to address
            best_prompt: The current best prompt to improve upon
            dataset: Dataset to evaluate on
            metric: Metric function
            attempt: Current attempt number (1-indexed)

        Returns:
            Tuple of (improved_prompt, improved_experiment_result)
        """
        run_manager, grp_cb = await new_group(
            name=f"generate_and_evaluate_improvement_attempt_{attempt}",
            inputs={
                "root_cause": root_cause,
                "current_prompt": best_prompt,
                "n_samples": n_samples,
            },
            callbacks=callbacks,
        )

        gen_improve_rm, gen_improve_grp = await new_group(
            name="generate_improvement_prompt",
            inputs={
                "root_cause": root_cause,
                "current_prompt": best_prompt,
                "n_samples": n_samples,
            },
            callbacks=grp_cb,
        )
        # Generate improvement
        improved_prompt_response = await self._improve_prompt(
            prompt_config=best_prompt,
            root_cause=root_cause,
            attempt=attempt,
            callbacks=gen_improve_grp,
        )

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
        await gen_improve_rm.on_chain_end(outputs={"improved_prompt": improved_prompt})

        eval_improve_rm, eval_improve_grp = await new_group(
            name="eval_improvement_prompt",
            inputs={
                "improved_prompt": improved_prompt,
                "dataset": dataset.name,
                "n_samples": n_samples,
            },
            callbacks=grp_cb,
        )

        # Evaluate improved prompt
        improved_experiment_result = await evaluate_prompt(
            prompt_config=improved_prompt,
            dataset=dataset,
            metric=metric,
            max_concurrency=self.num_eval_threads,
            n_samples=n_samples,
            callbacks=eval_improve_grp,
        )
        await eval_improve_rm.on_chain_end(
            outputs={"improved_experiment_result": improved_experiment_result}
        )

        return improved_prompt, improved_experiment_result

    async def _optimize(
        self,
        config: BaseConfig,
        dataset: BaseDataset,
        metric: BaseMetric,
        n_samples: Optional[int] = None,
        callbacks: Optional[Callbacks] = None,
        **kwargs: Any,
    ) -> OptimizationResult:
        """
        Main logic for hierarchical reflective optimization.

        Parameters
        ----------
        config : BaseConfig
            Initial configuration (must be PromptConfig)
        dataset : BaseDataset
            Dataset to optimize
        metric : BaseMetric
            Metric to optimize
        **kwargs : Any
            Additional parameters

        Returns
        -------
        OptimizationResult
            Result containing optimized prompt and metadata
        """
        # Validate configuration type
        if not isinstance(config, PromptConfig):
            raise ValueError(
                f"HierarchicalReflectiveOptimizer requires PromptConfig, "
                f"got {type(config).__name__}"
            )

        prompt_config = config
        histories: List[HistoryRecord] = []

        run_manager, grp_cb = await new_group(
            name="optimize",
            inputs={
                "max_iterations": self.max_iterations,
            },
            callbacks=callbacks,
        )

        # Evaluate baseline
        eval_baseline_rm, eval_baseline_grp = await new_group(
            name="eval_baseline",
            inputs={
                "num_eval_threads": self.num_eval_threads,
            },
            callbacks=grp_cb,
        )

        experiment_result = await evaluate_prompt(
            prompt_config=prompt_config,
            dataset=dataset,
            metric=metric,
            max_concurrency=self.num_eval_threads,
            n_samples=n_samples,
            callbacks=eval_baseline_grp,
        )
        baseline_score = experiment_result.avg_score
        history = HistoryRecord(
            iteration=0,
            stage="baseline",
            score=baseline_score,
            config=prompt_config,
            experiment_result=experiment_result,
            optimizer_name=self.__class__.__name__,
            metric_name=metric.__class__.__name__,
        )
        logger.info(
            f"Updated history: {history.model_dump_json(exclude={'experiment_result'})}"
        )
        histories.append(history)
        await eval_baseline_rm.on_chain_end(outputs={"history": history})

        # Track baseline and best
        best_score = baseline_score
        best_prompt = prompt_config
        current_experiment_result = (
            experiment_result  # Separate variable for current iteration result
        )

        # Multi-iteration optimization loop
        previous_iteration_score = baseline_score

        iteration: int = 0
        for iteration in range(1, self.max_iterations + 1):
            optimize_iter_rm, optimize_iter_grp = await new_group(
                name=f"optimization_iter_{iteration}",
                inputs={
                    "iteration": iteration,
                },
                callbacks=grp_cb,
            )

            # Perform hierarchical root cause analysis
            root_cause_analyze_rm, root_cause_analyze_grp = await new_group(
                name="hierarchical_root_cause_analysis",
                inputs={
                    "experiment_result": current_experiment_result,
                },
                callbacks=optimize_iter_grp,
            )

            hierarchical_analysis = await self._hierarchical_analyzer.analyze(
                current_experiment_result, root_cause_analyze_grp
            )

            await root_cause_analyze_rm.on_chain_end(
                outputs={"hierarchical_analysis": hierarchical_analysis}
            )

            # Address each failure mode
            if not hierarchical_analysis.unified_failure_modes:
                logger.warning(
                    "No failure modes detected in hierarchical analysis, skipping iteration"
                )
                continue  # Skip to next iteration

            for idx, root_cause in enumerate(
                hierarchical_analysis.unified_failure_modes, 1
            ):
                gen_and_eval_improve_rm, gen_and_eval_improve_grp = await new_group(
                    name="generate_and_evaluate_improvement",
                    inputs={
                        "root_cause": root_cause,
                        "current_prompt": best_prompt,
                        "current_score": best_score,
                        "max_retries": self.max_retries,
                    },
                    callbacks=optimize_iter_grp,
                )

                # Try multiple attempts if needed
                max_attempts = self.max_retries + 1
                improved_prompt = None
                improved_score = None
                improved_experiment_result = None

                for attempt in range(1, max_attempts + 1):
                    # Generate and evaluate improvement
                    (
                        improved_prompt,
                        improved_experiment_result,
                    ) = await self._generate_and_evaluate_improvement(
                        root_cause=root_cause,
                        best_prompt=best_prompt,
                        dataset=dataset,
                        metric=metric,
                        attempt=attempt,
                        n_samples=n_samples,
                        callbacks=gen_and_eval_improve_grp,
                    )

                    improved_score = improved_experiment_result.avg_score

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

                # Validate we have all required data for history record
                if improved_prompt is None:
                    improved_prompt = best_prompt
                if improved_experiment_result is None:
                    improved_experiment_result = current_experiment_result
                if improved_score is None:
                    improved_score = best_score

                history = HistoryRecord(
                    iteration=iteration,
                    stage="optimizing",
                    score=improved_score,
                    optimizer_name=self.__class__.__name__,
                    metric_name=metric.__class__.__name__,
                    config=improved_prompt,
                    experiment_result=improved_experiment_result,
                    metadata={
                        "root_cause": root_cause,
                        "sub_iteration": idx,
                    },
                )
                logger.info(
                    f"Updated history: {history.model_dump_json(exclude={'experiment_result'})}"
                )
                histories.append(history)
                await gen_and_eval_improve_rm.on_chain_end(outputs={"history": history})

                # Check if final result is an improvement (variables already validated above)
                if improved_score > best_score:
                    improvement = self.calculate_improvement(improved_score, best_score)
                    logger.info(
                        f"Updated best prompt: score {improved_score:.4f} (+{improvement:.2%})"
                    )

                    # Update best
                    best_score = improved_score
                    best_prompt = improved_prompt
                    current_experiment_result = (
                        improved_experiment_result  # Update current iteration result
                    )
                else:
                    logger.debug(
                        f"Keeping previous best prompt, no improvement from '{root_cause.name}'"
                    )

            # Check for convergence after iteration
            iteration_improvement = self.calculate_improvement(
                best_score, previous_iteration_score
            )

            await optimize_iter_rm.on_chain_end(
                outputs={
                    "best_score": best_score,
                    "best_config": best_prompt,
                    "iteration_improvement": iteration_improvement,
                }
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
        final_improvement = self.calculate_improvement(best_score, baseline_score)

        optimization_result = OptimizationResult(
            optimizer_name=self.__class__.__name__,
            best_config=best_prompt,
            best_score=best_score,
            metric_name=metric.__class__.__name__,
            initial_config=prompt_config,
            initial_score=baseline_score,
            improvement=final_improvement,
            histories=histories,
            details={
                "model": self.llm,
                "max_iterations": self.max_iterations,
                "convergence_threshold": self.convergence_threshold,
                "max_retries": self.max_retries,
            },
            iterations=iteration,
        )

        await run_manager.on_chain_end(
            outputs={"optimization_result": optimization_result}
        )

        # Create result
        return optimization_result
