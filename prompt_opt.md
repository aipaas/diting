# Diting Prompt优化算法调用方式说明

## 概述

Diting项目提供了多种Prompt优化算法，主要包括：
1. **Model Parameters优化算法**：用于优化模型参数（如temperature、top_p等）
2. **Prompt Messages优化算法**：用于优化提示词内容本身

两种算法都遵循统一的调用接口，便于集成和使用。

## 1. Model Parameters优化算法 (TPE)

### 调用方式

```python
from diting_core.optimization.algorithms.prompt.model_parameters.tpe.optimizer import ParameterOptimizer
from diting_core.optimization.algorithms.prompt.model_parameters.tpe.search_space import ParameterSearchSpace, ParameterSpec, ParameterType

# 创建优化器
optimizer = ParameterOptimizer(
    max_iterations=20,
    seed=42,
    local_search_ratio=0.3
)

# 定义参数搜索空间
parameter_space = ParameterSearchSpace(
    parameters=[
        ParameterSpec(
            name="temperature",
            distribution=ParameterType.FLOAT,
            low=0.0,
            high=1.0,
        ),
        ParameterSpec(
            name="top_p",
            distribution=ParameterType.FLOAT,
            low=0.0,
            high=1.0,
        )
    ]
)

# 执行优化
result = await optimizer.optimize(
    config=prompt_config,  # PromptConfig实例
    dataset=dataset,       # BaseDataset实例
    metric=metric,         # BaseMetric实例
    n_trials=20,
    parameter_space=parameter_space
)
```

### 工作原理

1. 使用Optuna的TPE采样器进行贝叶斯优化
2. 采用两阶段优化：全局搜索(70% trials) + 局部搜索(30% trials)
3. 通过evaluate_prompt函数评估每组参数的性能
4. 返回包含最佳参数和优化历史的OptimizationResult

## 2. Prompt Messages优化算法 (Hierarchical Reflective)

### 调用方式

```python
from diting_core.optimization.algorithms.prompt.prompt_messages.hierarchical_reflective.optimizer import HierarchicalReflectiveOptimizer

# 创建优化器
optimizer = HierarchicalReflectiveOptimizer(
    llm=llm,  # BaseLLM实例
    max_iterations=5,
    convergence_threshold=0.01
)

# 执行优化
result = await optimizer.optimize(
    config=prompt_config,  # PromptConfig实例
    dataset=dataset,       # BaseDataset实例
    metric=metric,         # BaseMetric实例
    n_samples=None
)
```

### 工作原理

1. 首先评估基线提示词性能
2. 通过分层根因分析识别失败模式
3. 针对每个失败模式生成改进的提示词
4. 评估改进后的提示词，如果性能提升则采用
5. 重复迭代直到达到最大迭代次数或收敛阈值

## 3. 通用调用模式

### 基本接口

所有优化器都遵循统一的调用接口：

```python
# 所有优化器都继承自BaseOptimizer基类
result = await optimizer.optimize(
    config=prompt_config,  # PromptConfig实例
    dataset=dataset,       # BaseDataset实例
    metric=metric,         # BaseMetric实例
    n_samples=None,        # 可选，样本数量
    **kwargs               # 其他参数
)
```

### 参数说明

- config: PromptConfig实例，包含待优化的提示词配置
- dataset: BaseDataset实例，用于评估优化效果的数据集
- metric: BaseMetric实例，用于评估优化效果的指标
- n_samples: 可选参数，指定评估时使用的样本数量
- **kwargs: 其他特定于优化器的参数

## 4. 评估机制

### 核心评估函数

- evaluate_prompt: 用于评估PromptConfig的性能
- evaluate_prompt_with_detail: 用于详细评估，返回测试结果细节
- evaluate_prompt_sync: 同步版本的评估函数

### 使用示例

```python
from diting_core.optimization.infra.eval_task import evaluate_prompt

# 评估PromptConfig性能
score = await evaluate_prompt(
    prompt_config=prompt_config,
    dataset=dataset,
    metric=metric,
    max_concurrency=12,
    n_samples=None
)
```

## 5. 优化结果

所有优化算法都返回标准化的OptimizationResult对象，包含以下信息：

- best_config: 优化后的最佳配置
- best_score: 最佳评分
- initial_prompt: 初始提示词配置
- initial_score: 初始评分
- improvement: 性能提升百分比
- history: 优化过程历史记录
- details: 优化器特定的详细信息
- iterations: 迭代次数

## 6. 完整示例

```python
import asyncio
from diting_core.optimization.target.prompt_config import PromptConfig
from diting_core.optimization.datasets.base_dataset import InMemoryDataset
from diting_core.metrics.base_metric import BaseMetric
from diting_core.models.llms.base_model import BaseLLM

from diting_core.optimization.algorithms.prompt.model_parameters.tpe.optimizer import ParameterOptimizer
from diting_core.optimization.algorithms.prompt.model_parameters.tpe.search_space import ParameterSearchSpace, ParameterSpec, ParameterType

# 创建提示词配置
prompt_config = PromptConfig(
    system="You are a helpful assistant.",
    user="Answer the following question: {question}",
    llm=llm  # BaseLLM实例
)

# 创建数据集
dataset = InMemoryDataset(
    name="test_dataset",
    items=[
        {"question": "What is AI?", "expected_output": "Artificial Intelligence"},
        {"question": "What is machine learning?", "expected_output": "A subset of AI"}
    ]
)

# 创建评估指标
metric = YourCustomMetric()  # 继承自BaseMetric的自定义指标

# 创建优化器
optimizer = ParameterOptimizer(max_iterations=10)

# 定义参数搜索空间
parameter_space = ParameterSearchSpace(
    parameters=[
        ParameterSpec(
            name="temperature",
            distribution=ParameterType.FLOAT,
            low=0.0,
            high=1.0,
        )
    ]
)

# 执行优化
result = await optimizer.optimize(
    config=prompt_config,
    dataset=dataset,
    metric=metric,
    n_trials=10,
    parameter_space=parameter_space
)

# 输出结果
print(f"初始评分: {result.initial_score}")
print(f"最佳评分: {result.best_score}")
print(f"性能提升: {result.improvement:.2%}")
```

通过以上方式，可以方便地调用Diting项目中的Prompt优化算法，实现自动化的提示词优化。