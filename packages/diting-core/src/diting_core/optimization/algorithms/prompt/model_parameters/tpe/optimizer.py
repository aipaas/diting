"""Simple Optuna-based optimizer_name for model model_parameters tuning.

Adapted from Opik's ParameterOptimizer with minimal changes for Diting.
"""

import copy
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import optuna
from optuna.trial import Trial, TrialState

from diting_core.callbacks.base import Callbacks
from diting_core.callbacks.manager import new_group
from diting_core.metrics.base_metric import BaseMetric
from diting_core.optimization.algorithms.prompt.model_parameters.tpe.search_space import (
    ParameterSearchSpace,
    ParameterType,
)
from diting_core.optimization.base_optimizer import BaseOptimizer
from diting_core.optimization.datasets.base_dataset import BaseDataset
from diting_core.optimization.optimization_result import OptimizationResult
from diting_core.optimization.target.base_config import BaseConfig
from diting_core.optimization.target.prompt_config import PromptConfig
from diting_core.optimization.infra.eval_task import (
    evaluate_prompt_sync,
    evaluate_prompt,
)

logger = logging.getLogger(__name__)


class ParameterOptimizer(BaseOptimizer):
    """Optimizer that tunes model call parameters (temperature, top_p, etc.)."""

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
        # 验证配置类型
        if not isinstance(config, PromptConfig):
            raise ValueError(
                f"ParameterOptimizer requires PromptConfig, got {type(config).__name__}"
            )

        # Get model_parameters space
        parameter_space = kwargs.get("parameter_space")
        if parameter_space is None:
            raise ValueError(
                "ParameterOptimizer requires parameter_space argument. "
                "Example: optimizer_name.optimize_prompt(..., parameter_space={...})"
            )

        if not isinstance(parameter_space, ParameterSearchSpace):
            parameter_space = ParameterSearchSpace.model_validate(parameter_space)

        prompt_config = config
        history: List[Dict[str, Any]] = []

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
        history.append(
            {
                "iteration": 0,
                "timestamp": datetime.utcnow().isoformat(),
                "stage": "baseline",
                "config": copy.deepcopy(prompt_config.model_params or {}),
                "score": baseline_score,
                "experiment_result": experiment_result,
                "parameters": {},
            }
        )

        await eval_baseline_rm.on_chain_end(
            outputs={
                "baseline_score": baseline_score,
                "experiment_result": experiment_result,
            }
        )

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

        current_space = parameter_space
        current_stage = "global"
        search_ranges: Dict[str, Dict[str, Any]] = {}

        # Objective function
        def objective(trial: Trial) -> float:
            sampled_values = current_space.suggest(trial)
            tuned_prompt = parameter_space.apply(
                prompt_config,
                sampled_values,
                base_model_params=copy.deepcopy(prompt_config.model_params or {}),
            )

            # Use synchronous evaluation
            _experiment_result = evaluate_prompt_sync(
                tuned_prompt,
                dataset,
                metric,
                self.num_eval_threads,
                n_samples=n_samples,
                callbacks=parameter_search_grp,
            )

            trial.set_user_attr("parameters", sampled_values)
            trial.set_user_attr(
                "model_params", copy.deepcopy(tuned_prompt.model_params)
            )
            trial.set_user_attr("experiment_result", _experiment_result)
            trial.set_user_attr("stage", current_stage)
            return _experiment_result.avg_score

        # Global search
        global_range = parameter_space.describe()
        search_ranges["global"] = global_range

        if global_trials > 0:
            logger.info(f"Starting global search: {global_trials} trials")
            study.optimize(objective, n_trials=global_trials, show_progress_bar=False)

        # Record global search history
        for trial in study.trials:
            if trial.state != TrialState.COMPLETE or trial.value is None:
                continue
            timestamp = (
                trial.datetime_complete or trial.datetime_start or datetime.utcnow()
            )
            history.append(
                {
                    "iteration": trial.number + 1,
                    "timestamp": timestamp.isoformat(),
                    "stage": trial.user_attrs.get("stage", "global"),
                    "config": trial.user_attrs.get("model_params"),
                    "score": float(trial.value),
                    "experiment_result": trial.user_attrs.get("experiment_result", {}),
                    "parameters": trial.user_attrs.get("parameters", {}),
                }
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
            if best_trial.value:
                # Even if score didn't improve, record best trial parameters
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
            current_stage = "local"
            current_space = parameter_space.narrow_around(
                best_parameters, self.local_search_scale
            )
            local_range = current_space.describe()
            search_ranges["local"] = local_range

            study.optimize(objective, n_trials=local_trials, show_progress_bar=False)

            # Update best results
            completed_trials = [
                t
                for t in study.trials
                if t.state == TrialState.COMPLETE and t.value is not None
            ]
            if completed_trials:
                new_best = max(completed_trials, key=lambda t: t.value)  # type: ignore
                if new_best.value and new_best.value > best_score:
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
            initial_prompt=prompt_config,
            initial_score=baseline_score,
            improvement=final_improvement,
            history=history,
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
