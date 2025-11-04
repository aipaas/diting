import json
from datetime import datetime, timezone

from diting_optimizer.optimization_result import HistoryRecord, OptimizationResult
from diting_optimizer.target.prompt_config import PromptConfig
from diting_optimizer.infra.eval_task import ExperimentResult, TestResult
from diting_core.callbacks.usage import Usage, ModelType
from diting_core.metrics.base_metric import MetricValue
from diting_core.cases.llm_case import LLMCase
from diting_core.models.llms.factory import llm_factory

if __name__ == "__main__":
    # 使用 llm_factory 创建真实的LLM实例
    # 注意：在实际使用中，你需要提供相应的 API key 和 base_url
    # 这里我们创建一个LLM实例用于演示，但在实际运行时需要设置环境变量 OPENAI_API_KEY
    llm = llm_factory(
        model="gpt-4o-mini",  # 或其他模型如 "gpt-4", "gpt-3.5-turbo" 等
        api_key="your-api-key",  # 如果需要，可以提供 API key 或设置环境变量 OPENAI_API_KEY
        temperature=0.7,
    )

    # 创建一个示例 PromptConfig
    config = PromptConfig(
        name="demo-prompt",
        system="你是一个专业的AI助手，请根据用户的问题提供准确、有用的回答。",
        user="请回答以下问题：{question}",
        model_params={"temperature": 0.7, "max_tokens": 1000, "top_p": 0.9},
        llm=llm,  # 注入真实的LLM实例
    )
    # 使用内置的序列化（自动排除llm字段）
    config_json = json.dumps(config.model_dump(), ensure_ascii=False, indent=2)
    print(config_json)

    # 创建一个示例 HistoryRecord
    record = HistoryRecord(
        iteration=0,
        stage="initialization",
        timestamp=datetime.now(timezone.utc),
        score=0.75,
        optimizer_name="demo-optimizer",
        metric_name="answer-relevancy",
        config=config,
        experiment_result=ExperimentResult(
            experiment_name="demo-experiment",
            test_results=[
                TestResult(
                    test_case=LLMCase(
                        user_input="什么是人工智能？",
                        actual_output="人工智能是模拟人类智能的计算机系统。",
                        expected_output="人工智能是指由机器展现的智能，特别是计算机系统模拟人类智能的过程。",
                        metadata={"dataset_item_id": "test_001"},
                    ),
                    metric_value=MetricValue(
                        metric_name="answer-relevancy",
                        score=0.75,
                        reason="回答基本正确，但缺少详细说明",
                    ),
                )
            ],
        ),
        metadata={
            "sub_iteration": 0,
            "execution_time": 2.5,
            "optimization_strategy": "gradient_descent",
        },
    )
    # 使用record的to_json方法
    record_json = record.to_json()
    print(record_json)

    # 创建一个示例 OptimizationResult
    result = OptimizationResult(
        optimizer_name="demo-optimizer",
        metric_name="answer-relevancy",
        best_config=config,
        best_score=0.85,
        initial_config=config,
        initial_score=0.65,
        improvement=0.3077,  # (0.85 - 0.65) / 0.65 ≈ 30.77%
        histories=[record],
        details={
            "optimized_parameters": {"temperature": 0.65, "max_tokens": 1200},
            "parameter_importance": {"temperature": 0.6, "max_tokens": 0.4},
            "search_ranges": {
                "initialization": {
                    "temperature": {"min": 0.1, "max": 1.0, "step": 0.1},
                    "max_tokens": {"min": 100, "max": 2000, "step": 100},
                }
            },
            "search_stages": [
                {
                    "stage": "initialization",
                    "description": "Initial parameter exploration",
                }
            ],
        },
        total_llm_calls=10,
        total_embedding_calls=5,
        total_usages=[
            Usage(
                model_type=ModelType.LLM,
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
            )
        ],
        tool_calls=3,
        iterations=5,
    )

    # 使用result的to_json方法
    result_json = result.to_json()
    print(result_json)
