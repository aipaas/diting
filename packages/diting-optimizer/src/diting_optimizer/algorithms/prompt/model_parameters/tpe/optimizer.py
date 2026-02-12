"""Simple Optuna-based optimizer for model parameter tuning.

Adapted from Opik's ParameterOptimizer with minimal changes for Diting.
Enhanced with basic error handling and code quality improvements.
"""

from __future__ import annotations

import asyncio
import copy
import logging
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor
import optuna
from optuna.trial import Trial, TrialState

from diting_core.callbacks.base import Callbacks
from diting_core.callbacks.manager import new_group
from diting_core.metrics.base_metric import BaseMetric
from diting_optimizer.algorithms.prompt.model_parameters.tpe.search_space import (
    ParameterSearchSpace,
    ParameterType,
)
from diting_optimizer.base_optimizer import BaseOptimizer
from diting_optimizer.datasets.base_dataset import BaseDataset
from diting_optimizer.optimization_result import OptimizationResult, HistoryRecord
from diting_optimizer.target.base_config import BaseConfig
from diting_optimizer.target.prompt_config import PromptConfig
from diting_optimizer.infra.eval_task import (
    evaluate_prompt_sync,
    evaluate_prompt,
)

logger = logging.getLogger(__name__)


def run_async(coro):
    """
    Safely run async coroutine in sync context.
    - If no event loop is running, create and close one.
    - If current event loop is running (e.g., outer async context),
      run asyncio.run() in a separate thread to avoid nesting.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No event loop running
        return asyncio.run(coro)
    else:
        # Current event loop running -> run new loop in separate thread
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()


# Objective function factory
def make_objective(
    stage: str,
    current_space: ParameterSearchSpace,  # Current sampling space
    parameter_space: ParameterSearchSpace,  # Global space for apply operations
    prompt_config: PromptConfig,
    dataset: BaseDataset,
    metric: BaseMetric,
    num_eval_threads: int,
    n_samples: Optional[int],
    histories: List[HistoryRecord],
    callbacks: Optional[Callbacks] = None,
    optimizer_name: str = "ParameterOptimizer (TPE)",
):
    """
    Return a synchronous objective function for Optuna.
    Each trial triggers a new chain group:
      - rm: Root manager for the current trial
      - grp_cb: Child callback manager, passed to evaluate_prompt_sync
    """

    def _objective(trial: Trial) -> float:
        """Objective function for Optuna optimization."""
        # Sample parameters
        sampled_values = current_space.suggest(trial)

        # Apply parameters to prompt
        tuned_prompt = parameter_space.apply(
            prompt_config,
            sampled_values,
            base_model_params=copy.deepcopy(prompt_config.model_params or {}),
        )

        # Create new trial group
        run_name = f"{stage}_trial_{trial.number}"
        rm, grp_cb = run_async(
            new_group(
                name=run_name,
                inputs={"stage": stage, "trial": trial.number},
                callbacks=callbacks,
            )
        )

        # Execute evaluation
        experiment_result = evaluate_prompt_sync(
            tuned_prompt,
            dataset,
            metric,
            num_eval_threads,
            n_samples=n_samples,
            callbacks=grp_cb,
        )

        # Build HistoryRecord
        cur_config = prompt_config.deep_copy()
        cur_config.model_params = tuned_prompt.model_params

        history = HistoryRecord(
            iteration=trial.number,
            stage=stage,
            score=experiment_result.avg_score,
            optimizer_name=optimizer_name,
            metric_name=metric.__class__.__name__,
            config=cur_config,
            experiment_result=experiment_result,
            metadata={"parameters": sampled_values},
        )
        histories.append(history)

        # Trigger chain end & history callback
        run_async(rm.on_chain_end(outputs={"history": history}))

        # Record trial attributes
        trial.set_user_attr("parameters", sampled_values)
        trial.set_user_attr("model_params", tuned_prompt.model_params)

        return experiment_result.avg_score

    return _objective


class ParameterOptimizer(BaseOptimizer):
    """Optimizer that tunes model call parameters (temperature, top_p, etc.).

    Uses Tree-structured Parzen Estimator (TPE) from Optuna for efficient
    hyperparameter optimization with basic error handling.

    Attributes:
        max_iterations: Maximum number of optimization iterations
        seed: Random seed for reproducible results
        local_search_ratio: Ratio of trials allocated to local search (0.0-1.0)
        local_search_scale: Scale factor for local search range reduction
        num_eval_threads: Number of parallel threads for evaluation
    """

    DEFAULT_MAX_ITERATIONS = 20

    def __init__(
        self,
        *,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        seed: int = 42,
        local_search_ratio: float = 0.3,
        local_search_scale: float = 0.2,
        num_eval_threads: int = 12,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.max_iterations = max_iterations
        self.seed = seed
        self.local_search_ratio = max(0.0, min(local_search_ratio, 1.0))
        self.local_search_scale = max(0.0, local_search_scale)
        self.num_eval_threads = num_eval_threads

    async def _optimize(
        self,
        config: BaseConfig,
        dataset: BaseDataset,
        metric: BaseMetric,
        n_samples: Optional[int] = None,
        n_trials: int = 0,
        callbacks: Optional[Callbacks] = None,
        **kwargs: Any,
    ) -> OptimizationResult:
        # Validate configuration type
        if not isinstance(config, PromptConfig):
            raise ValueError(
                f"ParameterOptimizer requires PromptConfig, got {type(config).__name__}"
            )

        # Get model_parameters space
        parameter_space = kwargs.get("parameter_space")
        if parameter_space is None:
            raise ValueError(
                "ParameterOptimizer requires parameter_space argument. "
                "Example: optimizer.optimize_prompt(..., parameter_space={...})"
            )

        if not isinstance(parameter_space, ParameterSearchSpace):
            parameter_space = ParameterSearchSpace.model_validate(parameter_space)

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
            optimizer_name=self.__class__.__name__,
            metric_name=metric.__class__.__name__,
            config=prompt_config,
            experiment_result=experiment_result,
        )
        histories.append(history)

        await eval_baseline_rm.on_chain_end(outputs={"history": history})

        parameter_search_rm, parameter_search_grp = await new_group(
            name="parameter_search",
            inputs={
                "num_eval_threads": self.num_eval_threads,
            },
            callbacks=grp_cb,
        )

        # Configure Optuna logging
        try:
            optuna.logging.disable_default_handler()
            optuna_logger = logging.getLogger("optuna")
            optuna_logger.setLevel(logger.getEffectiveLevel())
            optuna_logger.propagate = False
        except Exception as exc:  # pragma: no cover - defensive safety
            logger.warning("Could not configure Optuna logging: %s", exc)

        # Create Optuna study
        sampler = optuna.samplers.TPESampler(seed=self.seed)
        study = optuna.create_study(direction="maximize", sampler=sampler)

        # Calculate global and local trial counts
        total_trials = n_trials if n_trials > 0 else self.max_iterations
        local_trials = int(total_trials * self.local_search_ratio)
        global_trials = total_trials - local_trials

        if global_trials <= 0 < total_trials:
            global_trials = 1
            local_trials = total_trials - 1

        # Initialize search ranges with both global and local entries
        search_ranges: Dict[str, Dict[str, Any]] = {}

        # Global search
        global_range = parameter_space.describe()
        search_ranges["global"] = global_range
        search_ranges[
            "local"
        ] = {}  # Initialize local range, will be updated if local search runs

        if global_trials > 0:
            logger.info(f"Starting global search: {global_trials} trials")
            study.optimize(
                make_objective(
                    "global",
                    parameter_space,
                    parameter_space,
                    prompt_config,
                    dataset,
                    metric,
                    self.num_eval_threads,
                    n_samples,
                    histories,
                    parameter_search_grp,
                    self.__class__.__name__,
                ),
                n_trials=global_trials,
                show_progress_bar=False,
            )

        # Find current best parameters
        completed_trials = [
            t
            for t in study.trials
            if t.state == TrialState.COMPLETE and t.value is not None
        ]
        best_score = baseline_score
        best_parameters: Dict[str, Any] = {}
        best_model_params = copy.deepcopy(prompt_config.model_params or {})

        if completed_trials:
            best_trial = max(completed_trials, key=lambda t: t.value)  # type: ignore
            # Update best score if improved
            if best_trial.value > best_score:
                best_score = float(best_trial.value)
            # Always record best trial parameters (even if score didn't improve)
            best_parameters = best_trial.user_attrs.get("parameters", {})
            best_model_params = best_trial.user_attrs.get("model_params", {})

        # Local search
        if (
            local_trials > 0
            and completed_trials
            and best_parameters
            and any(
                spec.distribution in {ParameterType.FLOAT, ParameterType.INT}
                for spec in parameter_space.parameters
            )
        ):
            logger.info(f"Starting local search: {local_trials} trials")
            local_space = parameter_space.narrow_around(
                best_parameters, self.local_search_scale
            )
            local_range = local_space.describe()
            search_ranges["local"] = local_range

            study.optimize(
                make_objective(
                    "local",
                    local_space,
                    parameter_space,
                    prompt_config,
                    dataset,
                    metric,
                    self.num_eval_threads,
                    n_samples,
                    histories,
                    parameter_search_grp,
                    self.__class__.__name__,
                ),
                n_trials=local_trials,
                show_progress_bar=False,
            )

            # Update best results - refresh completed_trials since new trials were added
            completed_trials = [
                t
                for t in study.trials
                if t.state == TrialState.COMPLETE and t.value is not None
            ]
            if completed_trials:
                new_best = max(completed_trials, key=lambda t: t.value)  # type: ignore
                if new_best.value > best_score:
                    best_score = float(new_best.value)
                    best_parameters = new_best.user_attrs.get("parameters", {})
                    best_model_params = new_best.user_attrs.get("model_params", {})

        # Compute model_parameters importance
        try:
            from optuna.importance import get_param_importances

            importance = get_param_importances(study)
        except Exception:
            importance = {}

        await parameter_search_rm.on_chain_end(
            outputs={"best_parameters": best_parameters, "importance": importance}
        )
        # Build final prompt config
        best_prompt = parameter_space.apply(
            prompt_config,
            best_parameters,
            base_model_params=copy.deepcopy(prompt_config.model_params or {}),
        )
        # Build result
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
                "optimized_parameters": best_parameters,
                "optimized_model_params": best_model_params,
                "parameter_space": parameter_space.model_dump(),
                "n_trials": total_trials,
                "global_trials": global_trials,
                "local_trials": local_trials,
                "search_ranges": search_ranges,
                "parameter_importance": importance,
                "max_iterations": self.max_iterations,
            },
            iterations=len(completed_trials),
        )

        await run_manager.on_chain_end(
            outputs={"optimization_result": optimization_result}
        )

        return optimization_result
