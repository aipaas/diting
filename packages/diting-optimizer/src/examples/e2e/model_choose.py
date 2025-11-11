from diting_core.callbacks.stdout import StdOutCallbackHandler
from diting_core.models.llms.factory import llm_factory
from diting_optimizer.algorithms.prompt.prompt_messages.hierarchical_reflective.optimizer import (
    HierarchicalReflectiveOptimizer,
)
from diting_optimizer.algorithms.prompt.prompt_messages.hierarchical_reflective.prompts import (
    IMPROVE_PROMPT_TEMPLATE,
)
from diting_optimizer.algorithms.prompt.prompt_messages.hierarchical_reflective.types import (
    ImprovedPrompt,
    FailureMode,
)
from diting_optimizer.target.prompt_config import PromptConfig
from examples.e2e.customer_robot import FASTGPT_PROMPT


async def test_call_optimize():
    prompt_config = PromptConfig(
        messages=[
            {"role": "system", "content": FASTGPT_PROMPT},
            {"role": "user", "content": "{user_input}"},
        ],
    )
    # optimize_llm = llm_factory(
    #     model="qwen/qwen3-next-80b-a3b-instruct",
    #     base_url="https://integrate.api.nvidia.com/v1",
    #     api_key="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",
    # ) 9s

    # optimize_llm = llm_factory(
    #     model="openai/gpt-oss-120b",
    #     base_url="https://integrate.api.nvidia.com/v1",
    #     api_key="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",
    # )

    optimize_llm = llm_factory(
        model="openai/gpt-oss-20b",
        base_url="https://integrate.api.nvidia.com/v1",
        api_key="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",
    )

    # optimize_llm = llm_factory(
    #     model="glm-4.6",
    #     base_url="https://open.bigmodel.cn/api/paas/v4/",
    #     api_key="7f08f66caad549708238a57e0f7f33f7.EfQ9HoYpYZqBCRFX",
    # ) 38s

    # optimize_llm = llm_factory(
    #     model="qwen/qwen3-next-80b-a3b-instruct",
    #     base_url="https://integrate.api.nvidia.com/v1",
    #     api_key="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",
    # )

    current_messages = prompt_config.messages or []
    if not current_messages and prompt_config.system:
        current_messages = [{"role": "system", "content": prompt_config.system}]
        if prompt_config.user:
            current_messages.append({"role": "user", "content": prompt_config.user})
    root_cause = FailureMode(
        name="Missing Critical Details",
        description="The answer omits important information that is present in the reference output, such as specific eligibility conditions, quantitative limits, or category definitions. This makes the response incomplete even though the presented facts are correct.",
        root_cause="The model prioritizes brevity and often truncates the response after the most obvious points, reflecting insufficient training on the need to include all mandatory details from policy documents.",
    )
    improve_prompt_prompt = IMPROVE_PROMPT_TEMPLATE.format(
        current_prompt=current_messages,
        failure_mode_name=root_cause.name,
        failure_mode_description=root_cause.description,
        failure_mode_root_cause=root_cause.root_cause,
    )
    optimizer = HierarchicalReflectiveOptimizer(
        llm=optimize_llm, num_eval_threads=min(20, 10)
    )
    improve_prompt_response = await optimizer._call_model(
        messages=[{"role": "user", "content": improve_prompt_prompt}],
        seed=42,
        response_model=ImprovedPrompt,
        callbacks=[StdOutCallbackHandler()],
    )
    print(ImprovedPrompt.model_validate(improve_prompt_response))
