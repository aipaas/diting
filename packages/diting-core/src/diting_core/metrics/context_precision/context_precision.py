#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from dataclasses import field, dataclass
from typing import Type, Any, List, Optional, cast

from diting_core.callbacks.base import Callbacks
from diting_core.callbacks.manager import new_group
from diting_core.cases.llm_case import LLMCase, LLMCaseParams
from diting_core.metrics.base_metric import BaseMetric, MetricValue
from diting_core.models.llms.base_model import BaseLLM
from diting_core.metrics.context_precision.template import ContextPrecisionTemplate
from diting_core.metrics.context_precision.schema import Verdict


@dataclass
class ContextPrecision(BaseMetric):
    """
    The context-precision metric leverages an LLM as a judge to evaluate how precisely the chunks retrieved by your RAG
    pipeline’s retriever support the expected answer. It measures the proportion of the retrieved context that is truly
    useful for answering the user’s query. Specifically, it assesses how early in the ranking the retrieved text chunks
    that contain the correct answer appear. The higher the proportion of relevant chunks at the top of the list, the
    higher the score will be. Conversely, if relevant chunks are scattered towards the end of the list, the score will
    be significantly lower.

    Constraints:
    To use ContextPrecision, you must provide the following arguments when creating an LLMTestCase:
        - user_input
        - expected_output
        - retrieval_context

     Attributes:
        model (BaseLLM): The model used to compute this metric.
        evaluation_template (ContextPrecisionTemplate): The prompt template used for generating verdicts.
    """

    model: Optional[BaseLLM] = None
    _required_params: List[LLMCaseParams] = field(
        default_factory=lambda: [
            LLMCaseParams.USER_INPUT,
            LLMCaseParams.EXPECTED_OUTPUT,
            LLMCaseParams.RETRIEVAL_CONTEXT,
        ]
    )
    evaluation_template: Type[ContextPrecisionTemplate] = ContextPrecisionTemplate

    @staticmethod
    def _calculate_average_precision(verdicts: List[Verdict]) -> float:
        verdict_list = [1 if verdict.verdict else 0 for verdict in verdicts]
        denominator = sum(verdict_list) + 1e-10
        numerator = sum(
            [
                (sum(verdict_list[: i + 1]) / (i + 1)) * verdict_list[i]
                for i in range(len(verdict_list))
            ]
        )
        score = numerator / denominator
        return score

    async def _a_generate_verdicts(
        self,
        user_input: str,
        expected_output: str,
        context: str,
        callbacks: Optional[Callbacks] = None,
    ) -> Verdict:
        assert self.model is not None, "llm is not set"
        prompt = self.evaluation_template.generate_verdict(
            user_input=user_input, expected_output=expected_output, context=context
        )
        run_mgt, grp_cb = await new_group(
            name="a_generate_verdicts",
            inputs={
                "user_input": user_input,
                "expected_output": expected_output,
                "context": context,
            },
            callbacks=callbacks,
        )
        try:
            verdict = cast(
                Verdict,
                await self.model.generate_structured_output(
                    prompt, schema=Verdict, callbacks=grp_cb
                ),
            )
        except Exception as e:
            await run_mgt.on_chain_error(e)
            raise e
        await run_mgt.on_chain_end(outputs={"verdict": verdict})
        return verdict

    async def _compute(
        self,
        test_case: LLMCase,
        *args: Any,
        callbacks: Optional[Callbacks] = None,
        **kwargs: Any,
    ) -> MetricValue:
        assert test_case.user_input, "user_input cannot be empty"
        assert test_case.expected_output, "expected_output cannot be empty"
        assert test_case.retrieval_context, "retrieval_context cannot be empty"
        verdicts: List[Verdict] = []
        for context in test_case.retrieval_context:
            verdict = await self._a_generate_verdicts(
                user_input=test_case.user_input,
                expected_output=test_case.expected_output,
                context=context,
                callbacks=callbacks,
            )
            verdicts.append(verdict)
        score = self._calculate_average_precision(verdicts)
        metric_value = MetricValue(score=score, run_logs={"verdicts": verdicts})
        return metric_value
