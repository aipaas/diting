import asyncio

from diting_core.metrics import AnswerSimilarity
from diting_core.models.embeddings.factory import embedding_factory
from diting_core.models.llms.factory import llm_factory
from diting_optimizer.algorithms.prompt.model_parameters.tpe.optimizer import (
    ParameterOptimizer,
)
from diting_optimizer.algorithms.prompt.model_parameters.tpe.search_space import (
    ParameterSearchSpace,
    ParameterSpec,
    ParameterType,
)
from diting_optimizer.algorithms.prompt.prompt_messages.hierarchical_reflective.optimizer import (
    HierarchicalReflectiveOptimizer,
)
from diting_optimizer.algorithms.prompt.prompt_messages.hierarchical_reflective.prompts import (
    BATCH_ANALYSIS_PROMPT,
)
from diting_optimizer.datasets.hotpot_qa import hotpot_300
from diting_optimizer.target.prompt_config import PromptConfig
from examples.metric.accuracy_metric import AccuracyAndConciseMetric


def display_format_test_results_batch():
    from diting_core.cases.llm_case import LLMCase
    from diting_core.metrics.base_metric import MetricValue
    from diting_optimizer.infra.eval_task import TestResult
    from diting_optimizer.algorithms.prompt.prompt_messages.hierarchical_reflective.root_cause_analyzer import (
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
    formatted_batch = HierarchicalRootCauseAnalyzer._format_test_results_batch(  # pyright: ignore
        batch, batch_start=0, batch_end=2
    )
    # print(formatted_batch)

    batch_analysis_prompt = BATCH_ANALYSIS_PROMPT.format(
        formatted_batch=formatted_batch,
    )
    print(batch_analysis_prompt)


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
    metric = AccuracyAndConciseMetric(
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
    optimizer = HierarchicalReflectiveOptimizer(
        llm=optimize_llm, num_eval_threads=min(20, n_samples)
    )
    optimization_result = await optimizer.optimize(
        prompt_config,
        dataset,
        metric,
        n_samples=n_samples,
        verbose=False,
    )

    optimization_result.display()
    # best_config = optimization_result.best_config
    # best_config = cast(PromptConfig, best_config)
    # from diting_optimizer.infra.eval_task import evaluate_prompt
    # await evaluate_prompt(
    #     best_config,
    #     dataset,
    #     metric,
    #     max_concurrency=20,
    # )


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
        num_eval_threads=min(20, n_samples),
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


if __name__ == "__main__":
    # display_format_test_results_batch()
    # asyncio.run(my_accuracy())
    asyncio.run(prompt_optimize(10))
    # asyncio.run(parameter_optimize(2))
