#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from dataclasses import field, dataclass
from typing import Type, Tuple, Any, List, Dict

from diting.cases.llm_case import LLMCase, LLMCaseParams
from diting.metrics.answer_relevancy.schema import (
    AnswerRelevancyVerdict,
    Verdicts,
    Statements,
    Reason,
)
from diting.metrics.answer_relevancy.template import AnswerRelevancyTemplate
from diting.metrics.base_metric import BaseMetric, MetricValue
from diting.models.base_model import BaseLLM
from diting.models.factory import llm_factory


def _calculate_score(verdicts: List[AnswerRelevancyVerdict]) -> float:
    number_of_verdicts = len(verdicts)
    if number_of_verdicts == 0:
        return 1

    relevant_count = 0
    for verdict in verdicts:
        if verdict.verdict.strip().lower() != "no":
            relevant_count += 1

    score = relevant_count / number_of_verdicts
    return score


@dataclass
class AnswerRelevancyMetric(BaseMetric):
    """
    The answer relevancy metric uses LLM-as-a-judge to measure
    the quality of your RAG pipeline's generator by evaluating
    how relevant the actual_output of your LLM application is compared to the provided input.

    Constraints:
        To use the AnswerRelevancyMetric, you'll have to provide the following arguments when creating an LLMTestCase:
        - input
        - actual_output
        The input and actual_output are required to create an LLMCase (and hence required by all metrics)
        even though they might not be used for metric calculation.

    Attributes:
        model (BaseLLM): The judge model using in compute this metric.
        evaluation_template (AnswerRelevancyTemplate): The prompt template using in the compute this metric
    """

    model: BaseLLM = field(default_factory=llm_factory)
    _required_params: List[LLMCaseParams] = field(
        default_factory=lambda: [
            LLMCaseParams.USER_INPUT,
            LLMCaseParams.ACTUAL_OUTPUT,
        ]
    )

    evaluation_template: Type[AnswerRelevancyTemplate] = AnswerRelevancyTemplate

    async def _compute(
        self, test_case: LLMCase, *args: Tuple[Any], **kwargs: Dict[str, Any]
    ) -> MetricValue:
        assert test_case.user_input
        assert test_case.actual_output
        assert test_case.expected_output
        statements: List[str] = await self._a_generate_statements(
            test_case.actual_output
        )
        verdicts: List[AnswerRelevancyVerdict] = await self._a_generate_verdicts(
            test_case.user_input, statements
        )
        score = _calculate_score(verdicts)
        reason = None
        if self.include_reason:
            reason = await self._a_generate_reason(
                test_case.user_input, score, verdicts
            )

        return MetricValue(
            score=score,
            reason=reason,
            run_logs={
                "statements": statements,
                "verdicts": verdicts,
            },
        )

    async def _a_generate_statements(
        self,
        actual_output: str,
    ) -> List[str]:
        prompt = self.evaluation_template.generate_statements(
            actual_output=actual_output,
        )
        res: Statements = await self.model.generate_structured_output(
            prompt, schema=Statements
        )
        return res.statements

    async def _a_generate_verdicts(
        self, user_input: str, statements: List[str]
    ) -> List[AnswerRelevancyVerdict]:
        if len(statements) == 0:
            return []

        prompt = self.evaluation_template.generate_verdicts(
            user_input=user_input,
            statements=statements,
        )

        res = await self.model.generate_structured_output(prompt, schema=Verdicts)
        return res.verdicts

    async def _a_generate_reason(
        self, user_input: str, score: float, verdicts: List[AnswerRelevancyVerdict]
    ) -> str:
        irrelevant_statements = []
        for verdict in verdicts:
            if verdict.verdict.strip().lower() == "no":
                irrelevant_statements.append(verdict.reason)

        prompt = self.evaluation_template.generate_reason(
            irrelevant_statements=irrelevant_statements,
            input=user_input,
            score=round(score, 2),
        )
        res = await self.model.generate_structured_output(prompt, schema=Reason)
        return res.reason
