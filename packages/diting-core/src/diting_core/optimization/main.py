import asyncio

from diting_core.metrics import AnswerSimilarity
from diting_core.models.embeddings.factory import embedding_factory
from diting_core.models.llms.factory import llm_factory
from diting_core.optimization.target.prompt_config import PromptConfig
from diting_core.optimization.algorithms.prompt.prompt_messages.hierarchical_reflective.optimizer import (
    HierarchicalReflectiveOptimizer,
)

from diting_core.optimization.algorithms.prompt.model_parameters.tpe.optimizer import (
    ParameterOptimizer,
)
from diting_core.optimization.algorithms.prompt.model_parameters.tpe.search_space import (
    ParameterSearchSpace,
    ParameterSpec,
    ParameterType,
)

from diting_core.optimization.datasets.hotpot_qa import hotpot_300


async def async_main():
    # prepare dataset for eval and optimize
    dataset = hotpot_300()
    datas = dataset.get_items()
    print(len(datas))
    # 300
    data = datas[0]
    print(data)
    # {'id': 'hotpot_0', 'input': 'Are Smyrnium and Nymania both types of plant?', 'expected_output': 'yes', 'context': [], 'question': 'Are Smyrnium and Nymania both types of plant?', 'answer': 'yes'}

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
    # case = LLMCase(**data)
    # case.actual_output = await prompt_config.execute(data)
    # print(case)

    # prepare metric for eval
    embedding = embedding_factory(
        model="BAAI/bge-m3",
        base_url="https://api.siliconflow.cn/v1/",
        api_key="sk-xypapgifezpiclqwvjxicqtzizarklpownliqpkdlgvzkkwh",
    )

    metric = AnswerSimilarity(embedding_model=embedding)
    # metric_value = await metric.compute(case)
    # print(metric_value)

    # config the optimizer
    optimize_llm = llm_factory(
        model="Qwen/Qwen2.5-32B-Instruct",
        base_url="https://api.siliconflow.cn/v1/",
        api_key="sk-xypapgifezpiclqwvjxicqtzizarklpownliqpkdlgvzkkwh",
    )
    # firstly, optimize the prompt str using HierarchicalReflectiveOptimizer
    prompt_str_optimizer = HierarchicalReflectiveOptimizer(
        llm=optimize_llm, num_eval_threads=5
    )
    prompt_str_optimization_result = await prompt_str_optimizer.optimize(
        prompt_config, dataset, metric, n_samples=2, verbose=False
    )

    prompt_str_optimization_result.display()
    improved_prompt_config = prompt_str_optimization_result.best_config

    # secondly, optimize the prompt related model params using ParameterOptimizer
    optimizer = ParameterOptimizer(
        # llm=optimize_llm,
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
        improved_prompt_config,
        dataset,
        metric,
        parameter_space=parameter_space,
        n_samples=2,
        verbose=False,
    )
    optimization_result.display()

    print("FINAL PROMPT CONFIG:")
    print(optimization_result.best_config.model_dump())


if __name__ == "__main__":
    asyncio.run(async_main())
