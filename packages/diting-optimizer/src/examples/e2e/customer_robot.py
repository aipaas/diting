import asyncio

from diting_core.metrics import AnswerCorrectness
from diting_core.models.embeddings.factory import embedding_factory
from diting_core.models.llms.factory import llm_factory
from diting_optimizer.algorithms.prompt.prompt_messages.hierarchical_reflective.optimizer import (
    HierarchicalReflectiveOptimizer,
)
from diting_optimizer.datasets.rag_robot_qa import rag_qa_10
from diting_optimizer.target.prompt_config import PromptConfig

FASTGPT_PROMPT = """
## 任务描述
你是一个知识库回答助手，可以使用 <Cites></Cites> 中的内容作为你本次回答的参考。
同时，为了使回答结果更加可信并且可追溯，你需要在每段话结尾添加引用标记，标识参考了哪些内容。

## 追溯展示规则

- 使用 [id](CITE) 的格式来引用 <Cites></Cites> 中的知识，其中 CITE 是固定常量, id 为引文中的 id。
- 在 **每段话结尾** 自然地整合引用。例如: "Nginx是一款轻量级的Web服务器、反向代理服务器[67e517e74767063e882d6861](CITE)。"。
- 每段话**至少包含一个引用**，多个引用时按顺序排列，例如："Nginx是一款轻量级的Web服务器、反向代理服务器[67e517e74767063e882d6861](CITE)[67e517e74767063e882d6862](CITE)。
 它的特点是非常轻量[67e517e74767063e882d6863](CITE)。"
- 不要把示例作为知识点。
- 不要伪造 id，返回的 id 必须都存在 <Cites></Cites> 中！

## 通用规则

- 如果你不清楚答案，你需要澄清。
- 保持答案与 <Cites></Cites> 中描述的一致。但是要避免提及你是从 <Cites></Cites> 获取的知识。
- 使用 Markdown 语法优化回答格式。尤其是图片、表格、序列号等内容，需严格完整输出。
- 如果有合适的图片作为回答，则必须输出图片。输出图片时，仅需输出图片的 url，不要输出图片描述，例如：[](url)。
- 使用与问题相同的语言回答。

<Cites>
{context}
</Cites>
"""


async def prompt_optimize(n_samples: int):
    # prepare dataset for eval and optimize
    dataset = rag_qa_10()
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
            {"role": "system", "content": FASTGPT_PROMPT},
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
    # metric = AccuracyAndConciseMetric(
    #     model=eval_llm,
    # )
    embedding_model = embedding_factory(
        model="embedding-3",
        base_url="https://open.bigmodel.cn/api/paas/v4/",
        api_key="7f08f66caad549708238a57e0f7f33f7.EfQ9HoYpYZqBCRFX",
    )
    metric = AnswerCorrectness(model=eval_llm, embedding_model=embedding_model)

    # config the optimizer
    # optimize_llm = llm_factory(
    #     model="Qwen/Qwen2.5-32B-Instruct",
    #     base_url="https://api.siliconflow.cn/v1/",
    #     api_key="sk-xypapgifezpiclqwvjxicqtzizarklpownliqpkdlgvzkkwh",
    # )
    # optimize_llm = llm_factory(
    #     model="openai/gpt-oss-120b",
    #     base_url="https://integrate.api.nvidia.com/v1",
    #     api_key="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",
    # )
    optimize_llm = llm_factory(
        model="qwen/qwen3-next-80b-a3b-instruct",
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

    optimization_result.to_markdown(
        f"customer_robot_optimize_{metric.name}_{optimize_llm.model_name}.md"
    )
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
