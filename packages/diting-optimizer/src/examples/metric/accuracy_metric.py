import json
from dataclasses import dataclass, field
from typing import Optional, List, Any, cast

from diting_core.callbacks.base import Callbacks
from diting_core.callbacks.manager import new_group
from diting_core.cases.llm_case import LLMCaseParams, LLMCase
from diting_core.metrics import BaseMetric, MetricValue
from diting_core.metrics.answer_correctness.schema import LenientCorrectnessResult
from diting_core.metrics.custom_metric.schema import CustomMetricVerdict
from diting_core.models.llms.base_model import BaseLLM
from diting_core.models.llms.factory import llm_factory


@dataclass
class AccuracyAndConciseMetric(BaseMetric):
    model: Optional[BaseLLM] = None
    _required_params: List[LLMCaseParams] = field(
        default_factory=lambda: [
            LLMCaseParams.USER_INPUT,
            LLMCaseParams.EXPECTED_OUTPUT,
            LLMCaseParams.ACTUAL_OUTPUT,
        ]
    )

    @staticmethod
    def generate_lenient_correctness_evaluation(
        user_input: str,
        expected_output: str,
        actual_output: str,
    ) -> str:
        template_en = f"""You are a professional data annotator responsible for evaluating the factual correctness and conciseness of model outputs. Your task is to give a score according to the following rubric:

<Rubric>
  A perfectly correct answer should:
  - Provide accurate and complete information.
  - Contain no factual errors.
  - Address all parts of the question.
  - Be logically consistent.
  - Use precise and accurate terminology.
    
  A perfectly concise answer:
  - Contains only the exact information requested.
  - Uses the minimum number of words necessary to convey the complete answer.
  - Omits pleasantries, hedging language, and unnecessary context.
  - Excludes meta-commentary about the answer or the model's capabilities.
  - Avoids redundant information or restatements.
  - Does not include explanations unless explicitly requested.
 
  When scoring, you should deduct points for:
    - Factual errors or inaccuracies
    - Incomplete or partial answers
    - Misleading or ambiguous statements
    - Incorrect terminology
    - Logical inconsistencies
    - Missing key information
    - Introductory phrases like "I believe," "I think," or "The answer is."
    - Hedging language like "probably," "likely," or "as far as I know."
    - Unnecessary context or background information.
    - Explanations when not requested.
    - Follow-up questions or offers for more information.
    - Redundant information or restatements.
    - Polite phrases like "hope this helps" or "let me know if you need anything else."
    
</Rubric>

<Instructions>
  - Carefully read the input and output
  - Check for factual accuracy and completeness
  - Focus on correctness of information rather than style or verbosity
  - Check for any unnecessary elements, particularly those mentioned in the <Rubric> above.
  - The score should reflect how close the response comes to containing only the essential information requested based on the rubric above.
</Instructions>

<Reminder>
  The goal is to evaluate factual correctness and completeness and concise of the response.
</Reminder>

<input>
{user_input}
</input>

<output>
{actual_output}
</output>

<reference_output>
{expected_output}
</reference_output>

Please return the output in JSON format complying with the following schema:
{json.dumps(LenientCorrectnessResult.model_json_schema())}

--------Example Output--------
{{
  "score": 0.7,
  "reason": "The answer is mostly correct but lacks precision in expression, using uncertain language."
}}

{{
  "score": 0.6,
  "reason": "The answer is mostly correct but contains some unnecessary description about the question, not concise like the reference_output."
}}

Please provide a score between 0-1 and explain your reasoning.
**IMPORTANT**: Do not mention specific numeric scores in your reasoning. Use natural language to explain the evaluation rationale."""

        return template_en

    async def _compute(
        self,
        test_case: LLMCase,
        *args: Any,
        callbacks: Optional[Callbacks] = None,
        **kwargs: Any,
    ) -> MetricValue:
        assert self.model is not None, "llm is not set"
        assert test_case.user_input, "user_input cannot be empty"
        assert test_case.actual_output, "actual_output cannot be empty"
        assert test_case.expected_output, "expected_output cannot be empty"

        run_mgt, grp_cb = await new_group(
            name="_compute",
            inputs={"user_input": test_case.user_input},
            callbacks=callbacks,
        )
        try:
            prompt = self.generate_lenient_correctness_evaluation(
                user_input=test_case.user_input,
                expected_output=test_case.expected_output,
                actual_output=test_case.actual_output,
            )
            verdict = cast(
                CustomMetricVerdict,
                await self.model.generate_structured_output(
                    prompt, schema=LenientCorrectnessResult, callbacks=grp_cb
                ),
            )
        except Exception as e:
            await run_mgt.on_chain_error(e)
            raise e

        metric_value = MetricValue(
            score=verdict.score,
            reason=verdict.reason,
        )
        await run_mgt.on_chain_end(outputs={"metric_value": metric_value})
        return metric_value


async def my_accuracy():
    eval_llm = llm_factory(
        model="deepseek-ai/deepseek-v3.1",
        base_url="https://integrate.api.nvidia.com/v1",
        api_key="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",
    )
    metric = AccuracyAndConciseMetric(
        model=eval_llm,
    )

    metric_value = await metric.compute(
        test_case=LLMCase(
            user_input="Are Smyrnium and Nymania both types of plant?",
            expected_output="yes",
            actual_output="Yes, both Smyrnium and Nymania are genera (taxonomic groups) of plants, though they belong to different families and have distinct characteristics",
        ),
        verbose=True,
    )
    print(metric_value)
