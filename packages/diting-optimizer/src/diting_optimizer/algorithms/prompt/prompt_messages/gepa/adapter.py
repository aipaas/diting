from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any
from gepa.core.adapter import EvaluationBatch, GEPAAdapter
from pydantic import BaseModel
from diting_core.metrics import BaseMetric
from diting_optimizer.datasets.base_dataset import InMemoryDataset
from diting_optimizer.infra.eval_task import evaluate_prompt_sync
from diting_optimizer.target.prompt_config import PromptConfig

logger = logging.getLogger(__name__)


class DTDataInst(BaseModel):
    """Data instance handed to GEPA.

    We keep the original DiTing dataset item so metrics and prompt formatting can use it
    directly without duplicated bookkeeping.
    """

    user_input: str
    expected_output: str
    context: list[str]


def _extract_system_text(candidate: dict[str, str], fallback: str) -> str:
    for key in ("system_prompt", "system", "prompt"):
        value = candidate.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return fallback


def _apply_system_text(prompt_obj: PromptConfig, system_text: str) -> PromptConfig:
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


class OpikGEPAAdapter(GEPAAdapter[DTDataInst, dict[str, Any], dict[str, Any]]):
    """Minimal GEPA adapter that routes evaluation through Opik's metric."""

    def __init__(
        self,
        base_prompt: PromptConfig,
        optimizer: Any,
        metric: BaseMetric,
        system_fallback: str,
    ) -> None:
        self._base_prompt = base_prompt
        self._optimizer = optimizer
        self._metric = metric
        self._system_fallback = system_fallback

    def evaluate(
        self,
        batch: list[DTDataInst],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[dict[str, Any], dict[str, Any]]:
        system_text = _extract_system_text(candidate, self._system_fallback)
        prompt_variant = _apply_system_text(self._base_prompt, system_text)

        outputs: list[dict[str, Any]] = []
        scores: list[float] = []
        trajectories: list[dict[str, Any]] | None = [] if capture_traces else None

        data_items = [data.model_dump() for data in batch]
        dataset = InMemoryDataset("train", data_items)
        experiment_result = evaluate_prompt_sync(
            prompt_config=prompt_variant,
            dataset=dataset,
            metric=self._metric,
        )
        self._optimizer._gepa_live_metric_calls += len(batch)
        for test_result in experiment_result.test_results:
            raw_output = test_result.test_case.actual_output
            score = test_result.metric_value.score
            reason = test_result.metric_value.reason

            outputs.append({"output": raw_output})
            scores.append(score)
            if trajectories is not None:
                dataset_item = {
                    "user_input": test_result.test_case.user_input,
                    "expected_output": test_result.test_case.expected_output,
                    "context": test_result.test_case.context,
                }
                trajectories.append(
                    {
                        "input": dataset_item,
                        "output": raw_output,
                        "score": score,
                        "reason": reason,
                    }
                )

        return EvaluationBatch(
            outputs=outputs, scores=scores, trajectories=trajectories
        )

    def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch[dict[str, Any], dict[str, Any]],
        components_to_update: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        components = components_to_update or ["system_prompt"]
        trajectories = eval_batch.trajectories or []

        def _records() -> Iterable[dict[str, Any]]:
            for traj in trajectories:
                dataset_item = traj.get("input", {})
                output_text = traj.get("output", "")
                score = traj.get("score", 0.0)
                reason = traj.get("reason", "")
                feedback = f"Observed score={score:.4f}. Expected answer: {dataset_item.get('expected_output', '')}, score reason: {reason}"
                yield {
                    "Inputs": {
                        "user_input": dataset_item.get("user_input"),
                        "context": dataset_item.get("context"),
                    },
                    "Generated Outputs": output_text,
                    "Feedback": feedback,
                }

        reflective_records = list(_records())
        if not reflective_records:
            logger.debug(
                "No trajectories captured for candidate; returning empty reflective dataset"
            )
            reflective_records = []

        return {component: reflective_records for component in components}
