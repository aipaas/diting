import asyncio
import json
from dataclasses import field, dataclass
from typing import cast, Optional, List, Any

from diting_core.callbacks.base import Callbacks
from diting_core.callbacks.manager import new_group
from diting_core.cases.llm_case import LLMCaseParams, LLMCase
from diting_core.metrics import AnswerSimilarity, BaseMetric, MetricValue
from diting_core.metrics.answer_correctness.schema import LenientCorrectnessResult
from diting_core.metrics.custom_metric.schema import CustomMetricVerdict
from diting_core.models.embeddings.factory import embedding_factory
from diting_core.models.llms.base_model import BaseLLM
from diting_core.models.llms.factory import llm_factory
from diting_core.optimization.algorithms.prompt.model_parameters.tpe.optimizer import (
    ParameterOptimizer,
)
from diting_core.optimization.algorithms.prompt.model_parameters.tpe.search_space import (
    ParameterSearchSpace,
    ParameterSpec,
    ParameterType,
)
from diting_core.optimization.algorithms.prompt.prompt_messages.hierarchical_reflective.optimizer import (
    HierarchicalReflectiveOptimizer,
)
from diting_core.optimization.algorithms.prompt.prompt_messages.hierarchical_reflective.prompts import (
    BATCH_ANALYSIS_PROMPT,
)
from diting_core.optimization.datasets.hotpot_qa import hotpot_300
from diting_core.optimization.target.prompt_config import PromptConfig


def display_format_test_results_batch():
    from diting_core.cases.llm_case import LLMCase
    from diting_core.metrics.base_metric import MetricValue
    from diting_core.optimization.infra.eval_task import TestResult
    from diting_core.optimization.algorithms.prompt.prompt_messages.hierarchical_reflective.root_cause_analyzer import (
        HierarchicalRootCauseAnalyzer,
    )

    case1 = LLMCase(
        user_input="What is AI?",
        actual_output="Artificial intelligence",
        metadata={"dataset_item_id": "case_001"},
    )
    mv1 = MetricValue(metric_name="accuracy", score=0.85, reason="Matches core concept")
    tr1 = TestResult(test_case=case1, metric_value=mv1)

    case2 = LLMCase(
        user_input="2+2=",
        actual_output="5",
        expected_output="4",
        metadata={"dataset_item_id": "case_002"},
    )
    mv2 = MetricValue(metric_name="accuracy", score=0.0, reason="Incorrect calculation")
    tr2 = TestResult(test_case=case2, metric_value=mv2)

    batch = [tr1, tr2]
    formatted_batch = HierarchicalRootCauseAnalyzer._format_test_results_batch(
        batch, batch_start=0, batch_end=2
    )
    # print(formatted_batch)

    batch_analysis_prompt = BATCH_ANALYSIS_PROMPT.format(
        formatted_batch=formatted_batch,
    )
    print(batch_analysis_prompt)


async def parameter_optimize(n_samples: int):
    dataset = hotpot_300()

    # prepare optimize target
    generate_llm = llm_factory(
        model="THUDM/GLM-4-9B-0414",
        base_url="https://api.siliconflow.cn/v1/",
        api_key="sk-xypapgifezpiclqwvjxicqtzizarklpownliqpkdlgvzkkwh",
    )
    prompt_config = PromptConfig(
        messages=[
            {"role": "system", "content": "Provide an answer to the question"},
            {"role": "user", "content": "{user_input}"},
        ],
        llm=generate_llm,
    )

    # prepare metric for eval
    embedding = embedding_factory(
        model="BAAI/bge-m3",
        base_url="https://api.siliconflow.cn/v1/",
        api_key="sk-xypapgifezpiclqwvjxicqtzizarklpownliqpkdlgvzkkwh",
    )

    metric = AnswerSimilarity(embedding_model=embedding)

    # secondly, optimize the prompt related model params using ParameterOptimizer
    optimizer = ParameterOptimizer(
        num_eval_threads=5,
        max_iterations=10,
    )

    parameter_space = ParameterSearchSpace(
        parameters=[
            ParameterSpec(
                name="temperature",
                distribution=ParameterType.FLOAT,
                low=0.0,
                high=1.0,
            ),
            ParameterSpec(
                name="max_tokens",
                distribution=ParameterType.INT,
                low=10,
                high=100,
            ),
        ]
    )

    optimization_result = await optimizer.optimize(
        prompt_config,
        dataset,
        metric,
        parameter_space=parameter_space,
        n_samples=n_samples,
        verbose=False,
    )
    optimization_result.display()


@dataclass
class AccuracyMetric(BaseMetric):
    model: Optional[BaseLLM] = None
    _required_params: List[LLMCaseParams] = field(
        default_factory=lambda: [
            LLMCaseParams.USER_INPUT,
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

    def generate_verdict(self, test_case: LLMCase) -> str:
        pass


async def my_accuracy():
    eval_llm = llm_factory(
        model="deepseek-ai/deepseek-v3.1",
        base_url="https://integrate.api.nvidia.com/v1",
        api_key="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",
    )
    metric = AccuracyMetric(
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


async def prompt_optimize(n_samples: int):
    # prepare dataset for eval and optimize
    dataset = hotpot_300()
    # prepare optimize target
    # generate_llm = llm_factory(
    #     model="THUDM/GLM-4-9B-0414",
    #     base_url="https://api.siliconflow.cn/v1/",
    #     api_key="sk-xypapgifezpiclqwvjxicqtzizarklpownliqpkdlgvzkkwh",
    # )
    generate_llm = llm_factory(
        model="qwen/qwen2.5-7b-instruct",
        base_url="https://integrate.api.nvidia.com/v1",
        api_key="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",
    )

    prompt_config = PromptConfig(
        messages=[
            {"role": "system", "content": "Provide an answer to the question"},
            {"role": "user", "content": "{user_input}"},
        ],
        llm=generate_llm,
    )

    # prepare metric for eval
    # embedding = embedding_factory(
    #     model="Qwen/Qwen3-Embedding-4B",
    #     base_url="https://api.siliconflow.cn/v1/",
    #     api_key="sk-xypapgifezpiclqwvjxicqtzizarklpownliqpkdlgvzkkwh",
    # )

    # metric = AnswerSimilarity(embedding_model=embedding)
    eval_llm = llm_factory(
        model="deepseek-ai/deepseek-v3.1",
        base_url="https://integrate.api.nvidia.com/v1",
        api_key="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",
    )
    metric = AccuracyMetric(
        model=eval_llm,
    )

    # config the optimizer
    # optimize_llm = llm_factory(
    #     model="Qwen/Qwen2.5-32B-Instruct",
    #     base_url="https://api.siliconflow.cn/v1/",
    #     api_key="sk-xypapgifezpiclqwvjxicqtzizarklpownliqpkdlgvzkkwh",
    # )
    optimize_llm = llm_factory(
        model="openai/gpt-oss-120b",
        base_url="https://integrate.api.nvidia.com/v1",
        api_key="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",
    )

    # firstly, optimize the prompt str using HierarchicalReflectiveOptimizer
    optimizer = HierarchicalReflectiveOptimizer(llm=optimize_llm, num_eval_threads=20)
    optimization_result = await optimizer.optimize(
        prompt_config, dataset, metric, n_samples=n_samples, verbose=True
    )

    optimization_result.display()
    # best_config = optimization_result.best_config
    # best_config = cast(PromptConfig, best_config)
    # from diting_core.optimization.infra.eval_task import evaluate_prompt
    # await evaluate_prompt(
    #     best_config,
    #     dataset,
    #     metric,
    #     max_concurrency=20,
    # )


if __name__ == "__main__":
    # display_format_test_results_batch()
    # asyncio.run(my_accuracy())
    asyncio.run(prompt_optimize(10))
