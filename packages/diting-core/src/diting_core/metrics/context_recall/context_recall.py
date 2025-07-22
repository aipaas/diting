#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from dataclasses import field, dataclass
from typing import Type, Any, List, Optional, cast

from diting_core.callbacks.base import Callbacks
from diting_core.callbacks.manager import new_group
from diting_core.cases.llm_case import LLMCase, LLMCaseParams
from diting_core.metrics.base_metric import BaseMetric, MetricValue
from diting_core.metrics.context_recall.template import ContextRecallTemplate
from diting_core.metrics.context_recall.schema import Verdicts
from diting_core.models.llms.base_model import BaseLLM


@dataclass
class ContextRecall(BaseMetric):
    """
    The ContextRecall metric uses LLM-as-a-judge to measure how effectively your language model utilizes the provided
    retrieval_context to generate the expected_output in a RAG pipeline setting.

    Constraints:
        To use the ContextRecall metric, you'll need to provide the following arguments when creating an LLMTestCase:
        - user_input: The input provided to the model.
        - expected_output: The correct output that the model is expected to generate.
        - retrieval_context: The contextual information retrieved to assist the model in generating the expected output.

    Attributes:
        model (BaseLLM): The model used to compute this metric.
        evaluation_template (Type[ContextRecallTemplate]): The prompt template used for generating verdicts.
    """

    model: Optional[BaseLLM] = None
    _required_params: List[LLMCaseParams] = field(
        default_factory=lambda: [
            LLMCaseParams.USER_INPUT,
            LLMCaseParams.EXPECTED_OUTPUT,
            LLMCaseParams.RETRIEVAL_CONTEXT,
        ]
    )
    evaluation_template: Type[ContextRecallTemplate] = ContextRecallTemplate

    @staticmethod
    def _compute_score(verdicts: Verdicts) -> float:
        verdict_list = verdicts.verdicts
        attribution_flags = [1 if item.attributed else 0 for item in verdict_list]

        total_count = len(attribution_flags)
        positive_count = sum(attribution_flags)

        try:
            import numpy as np
        except ImportError:
            raise ImportError(
                "This function requires 'numpy'. Install it with: pip install numpy"
            )

        score = positive_count / total_count if total_count > 0 else np.nan

        return score

    async def _a_generate_verdicts(
        self,
        user_input: str,
        expected_output: str,
        retrieval_context: List[str],
        callbacks: Optional[Callbacks] = None,
    ) -> Verdicts:
        assert self.model is not None, "llm is not set"
        prompt = self.evaluation_template.generate_verdicts(
            user_input=user_input,
            expected_output=expected_output,
            retrieval_context=retrieval_context,
        )
        run_mgt, grp_cb = await new_group(
            name="generate_verdicts",
            inputs={
                "user_input": user_input,
                "expected_output": expected_output,
                "retrieval_context": retrieval_context,
            },
            callbacks=callbacks,
        )
        try:
            verdicts = cast(
                Verdicts,
                await self.model.generate_structured_output(
                    prompt, schema=Verdicts, callbacks=grp_cb
                ),
            )
        except Exception as e:
            await run_mgt.on_chain_error(e)
            raise e
        await run_mgt.on_chain_end(outputs={"verdicts": verdicts})
        return verdicts

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

        verdicts = await self._a_generate_verdicts(
            user_input=test_case.user_input,
            expected_output=test_case.expected_output,
            retrieval_context=test_case.retrieval_context,
        )
        score = self._compute_score(verdicts)
        metric_value = MetricValue(
            score=score,
            run_logs={
                "verdicts": verdicts,
            },
        )
        return metric_value


# if __name__ == "__main__":
#     from diting_core.models.llms.factory import llm_factory
#     # from diting_core.metrics.answer_correctness.data import (
#     #     query,
#     #     answer,
#     #     expect_answer,
#     #     retrive_context,
#     # )
#     import asyncio
#
#     llm = llm_factory(
#         model="Qwen2.5-72B-Instruct-GPTQ-Int4",
#         base_url="http://10.72.1.16:3454/v1",
#         api_key="j77GLdbQejCKvItUAOzqg994bijpXyT4123",
#         is_guided_json_support=True
#     )
#     test_case = LLMCase(
#         user_input="你好",
#         actual_output="你好",
#         expected_output="你好",
#         retrieval_context=["你好", "你好"],
#     )
#     context_recall = ContextRecall(model=llm)
#     context_recall_score = asyncio.run(context_recall.compute(test_case))
#     print(context_recall_score)
