import asyncio
import logging
from typing import Any, Optional

import gepa
from gepa.proposer.reflective_mutation.base import LanguageModel

from diting_core.cases.llm_case import LLMCaseParams
from diting_core.metrics import BaseMetric
from diting_core.models.llms.base_model import BaseLLM
from diting_optimizer.base_optimizer import BaseOptimizer
from diting_optimizer.datasets.base_dataset import BaseDataset, InMemoryDataset
from diting_optimizer.infra.eval_task import evaluate_prompt
from diting_optimizer.optimization_result import OptimizationResult, HistoryRecord
from diting_optimizer.target.base_config import BaseConfig
from diting_optimizer.target.prompt_config import PromptConfig
from .adapter import DTDataInst, OpikGEPAAdapter

logger = logging.getLogger(__name__)


def wrap_gepa_llm_sync(llm: BaseLLM) -> LanguageModel:
    """
    将 BaseLLM 包装成一个同步的 LanguageModel。
    内部使用线程池来避免嵌套事件循环问题。
    """

    class LocalSyncLLM:
        def __call__(self, prompt: str, *args, **kwargs) -> str:
            async def _runner():
                return await llm.generate(prompt, *args, **kwargs)

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures

                    # 如果已有运行的循环，使用线程池来运行新的 asyncio.run
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, _runner())
                        return future.result()
                else:
                    # 如果没有循环，直接在当前线程运行
                    return loop.run_until_complete(_runner())
            except RuntimeError:
                # 如果连循环都没有，创建一个新的
                return asyncio.run(_runner())

    return LocalSyncLLM()


class GepaOptimizer(BaseOptimizer):
    """Minimal integration against the upstream GEPA engine."""

    def __init__(
        self,
        llm: Optional[BaseLLM] = None,
        seed: int = 42,
        num_eval_threads: int = 12,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.llm = llm
        self.seed = seed
        self.num_eval_threads = num_eval_threads
        self._gepa_live_metric_calls = 0
        self._adapter = None  # Will be set during optimization

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_data_insts(
        self,
        dataset: BaseDataset,
    ) -> tuple[list[DTDataInst], list[DTDataInst]]:
        train_set, test_set = dataset.split()

        train_data_insts: list[DTDataInst] = []
        test_data_insts: list[DTDataInst] = []
        for sample in train_set.get_items():
            user_input = sample.get(LLMCaseParams.USER_INPUT.value, "")
            expected_output = sample.get(LLMCaseParams.EXPECTED_OUTPUT.value, "")
            context = sample.get(LLMCaseParams.CONTEXT.value)

            train_data_insts.append(
                DTDataInst(
                    user_input=user_input,
                    expected_output=expected_output,
                    context=context,
                )
            )

        for sample in test_set.get_items():
            user_input = sample.get(LLMCaseParams.USER_INPUT.value, "")
            expected_output = sample.get(LLMCaseParams.EXPECTED_OUTPUT.value, "")
            context = sample.get(LLMCaseParams.CONTEXT.value)

            test_data_insts.append(
                DTDataInst(
                    user_input=user_input,
                    expected_output=expected_output,
                    context=context,
                )
            )
        return train_data_insts, test_data_insts

    def _apply_system_text(
        self, prompt_obj: PromptConfig, system_text: str
    ) -> PromptConfig:
        updated = prompt_obj.deep_copy()
        if updated.messages is not None:
            messages = updated.get_messages()
            if messages and messages[0].get("role") == "system":
                messages[0]["content"] = system_text
            else:
                messages.insert(0, {"role": "system", "content": system_text})
            updated.set_messages(messages)
        else:
            updated.system = system_text
        return updated

    # ------------------------------------------------------------------
    # Base optimizer overrides
    # ------------------------------------------------------------------
    async def _optimize(
        self,
        config: BaseConfig,
        dataset: BaseDataset,
        metric: BaseMetric,
        n_samples: Optional[int] = None,
        experiment_config: dict | None = None,
        auto_continue: bool = False,
        **kwargs: Any,
    ) -> OptimizationResult:
        """
        Optimize a prompt using GEPA (Genetic-Pareto) algorithm.

        Args:
            prompt: The prompt to optimize
            dataset: Opik Dataset to optimize on
            metric: Metric function to evaluate on
            experiment_config: Optional configuration for the experiment
            n_samples: Optional number of items to test in the dataset
            auto_continue: Whether to auto-continue optimization
            agent_class: Optional agent class to use
            **kwargs: GEPA-specific parameters:
                max_metric_calls (int | None): Maximum number of metric evaluations (default: 30)
                reflection_minibatch_size (int): Size of reflection minibatches (default: 3)
                candidate_selection_strategy (str): Strategy for candidate selection (default: "pareto")
                skip_perfect_score (bool): Skip candidates with perfect scores (default: True)
                perfect_score (float): Score considered perfect (default: 1.0)
                use_merge (bool): Enable merge operations (default: False)
                max_merge_invocations (int): Maximum merge invocations (default: 5)
                run_dir (str | None): Directory for run outputs (default: None)
                track_best_outputs (bool): Track best outputs during optimization (default: False)
                display_progress_bar (bool): Display progress bar (default: False)
                seed (int): Random seed for reproducibility (default: 42)
                raise_on_exception (bool): Raise exceptions instead of continuing (default: True)
                mcp_config (MCPExecutionConfig | None): MCP tool calling configuration (default: None)

        Returns:
            OptimizationResult: Result of the optimization
        """

        # Extract GEPA-specific parameters from kwargs
        max_metric_calls: int | None = kwargs.get("max_metric_calls", 30)
        reflection_minibatch_size: int = int(kwargs.get("reflection_minibatch_size", 3))
        candidate_selection_strategy: str = str(
            kwargs.get("candidate_selection_strategy", "pareto")
        )
        skip_perfect_score: bool = kwargs.get("skip_perfect_score", True)
        perfect_score: float = float(kwargs.get("perfect_score", 1.0))
        use_merge: bool = kwargs.get("use_merge", False)
        max_merge_invocations: int = int(kwargs.get("max_merge_invocations", 5))
        run_dir: str | None = kwargs.get("run_dir", None)
        track_best_outputs: bool = kwargs.get("track_best_outputs", False)
        display_progress_bar: bool = kwargs.get("display_progress_bar", False)
        seed: int = int(kwargs.get("seed", 42))
        raise_on_exception: bool = kwargs.get("raise_on_exception", True)
        kwargs.pop("mcp_config", None)  # Added for MCP support (for future use)

        initial_config = PromptConfig.model_validate(config)

        seed_prompt_text = self._extract_system_text(initial_config)

        samples = dataset.get_items(n_samples=n_samples)
        dataset_optimize = InMemoryDataset("gepa-train", samples)
        trainset, valset = self._build_data_insts(dataset_optimize)

        self._gepa_live_metric_calls = 0

        base_prompt = initial_config

        # Baseline evaluation
        _, test_dataset = dataset_optimize.split()
        baseline_experiment_result = await evaluate_prompt(
            initial_config, test_dataset, metric, self.num_eval_threads, n_samples
        )
        baseline_score = baseline_experiment_result.avg_score

        adapter_prompt = self._apply_system_text(base_prompt, seed_prompt_text)
        adapter = OpikGEPAAdapter(
            base_prompt=adapter_prompt,
            optimizer=self,
            metric=metric,
            system_fallback=seed_prompt_text,
        )

        kwargs_gepa: dict[str, Any] = {
            "seed_candidate": {"system_prompt": seed_prompt_text},
            "trainset": trainset,
            "valset": valset,
            "adapter": adapter,
            "task_lm": None,
            "reflection_lm": wrap_gepa_llm_sync(self.llm),
            "candidate_selection_strategy": candidate_selection_strategy,
            "skip_perfect_score": skip_perfect_score,
            "reflection_minibatch_size": reflection_minibatch_size,
            "perfect_score": perfect_score,
            "use_merge": use_merge,
            "max_merge_invocations": max_merge_invocations,
            "max_metric_calls": max_metric_calls,
            "run_dir": run_dir,
            "track_best_outputs": track_best_outputs,
            "display_progress_bar": display_progress_bar,
            "seed": seed,
            "raise_on_exception": raise_on_exception,
        }

        gepa_result = gepa.optimize(**kwargs_gepa)

        # ------------------------------------------------------------------
        # Rescoring & result assembly
        # ------------------------------------------------------------------

        candidates: list[dict[str, str]] = getattr(gepa_result, "candidates", []) or []
        val_scores: list[float] = list(getattr(gepa_result, "val_aggregate_scores", []))

        rescored: list[float] = []
        candidate_rows: list[dict[str, Any]] = []
        histories: list[HistoryRecord] = []

        for idx, candidate in enumerate(candidates):
            candidate_prompt = self._extract_system_text_from_candidate(
                candidate, seed_prompt_text
            )
            prompt_variant = self._apply_system_text(initial_config, candidate_prompt)

            experiment_result = await evaluate_prompt(
                prompt_variant,
                dataset_optimize,
                metric,
                self.num_eval_threads,
                n_samples,
            )
            score = experiment_result.avg_score

            rescored.append(score)
            candidate_rows.append(
                {
                    "iteration": idx + 1,
                    "system_prompt": candidate_prompt,
                    "gepa_score": val_scores[idx] if idx < len(val_scores) else None,
                    "opik_score": score,
                    "source": self.__class__.__name__,
                }
            )
            histories.append(
                HistoryRecord(
                    iteration=idx + 1,
                    stage="train",
                    score=score,
                    optimizer_name=self.__class__.__name__,
                    metric_name=metric.__class__.__name__,
                    config=prompt_variant,
                    experiment_result=experiment_result,
                    metadata={},
                )
            )

        if rescored:
            best_idx = max(range(len(rescored)), key=lambda i: rescored[i])
            best_score = rescored[best_idx]
        else:
            best_idx = getattr(gepa_result, "best_idx", 0) or 0
            best_score = float(val_scores[best_idx]) if val_scores else 0.0

        best_candidate = (
            candidates[best_idx] if candidates else {"system_prompt": seed_prompt_text}
        )
        best_prompt_text = self._extract_system_text_from_candidate(
            best_candidate, seed_prompt_text
        )

        final_prompt = self._apply_system_text(initial_config, best_prompt_text)

        details: dict[str, Any] = {
            "optimizer": self.__class__.__name__,
            "num_candidates": getattr(gepa_result, "num_candidates", None),
            "total_metric_calls": getattr(gepa_result, "total_metric_calls", None),
            "parents": getattr(gepa_result, "parents", None),
            "val_scores": val_scores,
            "opik_rescored_scores": rescored,
            "candidate_summary": candidate_rows,
            "best_candidate_iteration": (
                candidate_rows[best_idx]["iteration"] if candidate_rows else 0
            ),
            "selected_candidate_index": best_idx,
            "selected_candidate_gepa_score": (
                val_scores[best_idx] if best_idx < len(val_scores) else None
            ),
            "selected_candidate_opik_score": best_score,
            "gepa_live_metric_used": True,
            "gepa_live_metric_call_count": self._gepa_live_metric_calls,
        }
        if experiment_config:
            details["experiment"] = experiment_config

        return OptimizationResult(
            optimizer_name=self.__class__.__name__,
            best_config=final_prompt,
            best_score=best_score,
            metric_name=metric.name,
            initial_config=initial_config,
            initial_score=baseline_score,
            histories=histories,
            details=details,
            iterations=len(histories),
        )

    # ------------------------------------------------------------------
    # Helpers used by BaseOptimizer.evaluate_prompt
    # ------------------------------------------------------------------

    def _extract_system_text(self, prompt: PromptConfig) -> str:
        messages = prompt.get_messages()
        for message in messages:
            if message.get("role") == "system":
                return str(message.get("content", "")).strip()
        for message in messages:
            if message.get("role") == "user":
                return f"You are a helpful assistant. Respond to: {message.get('content', '')}"
        return "You are a helpful assistant."

    def _extract_system_text_from_candidate(
        self, candidate: dict[str, Any], fallback: str
    ) -> str:
        for key in ("system_prompt", "system", "prompt"):
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return fallback
