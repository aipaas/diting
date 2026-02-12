import asyncio

from diting_core.models.llms.factory import llm_factory
from diting_optimizer.algorithms.prompt.prompt_messages.gepa.optimizer import (
    GepaOptimizer,
)
from diting_optimizer.datasets.hotpot_qa import hotpot_300
from diting_optimizer.target.prompt_config import PromptConfig
from examples.metric.accuracy_metric import AccuracyAndConciseMetric


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
        model="qwen/qwen3-next-80b-a3b-instruct",
        base_url="https://integrate.api.nvidia.com/v1",
        api_key="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",
    )

    # firstly, optimize the prompt str using HierarchicalReflectiveOptimizer
    optimizer = GepaOptimizer(llm=optimize_llm, num_eval_threads=min(20, n_samples))
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


if __name__ == "__main__":
    asyncio.run(prompt_optimize(10))
