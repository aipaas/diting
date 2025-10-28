# 多指标优化使用指南

## 概述

本指南介绍了如何在DiTing优化框架中使用多个指标进行优化。通过复合指标（CompositeMetric）功能，用户可以同时使用多个评估指标来指导优化过程，从而获得更全面的优化结果。

## 复合指标（CompositeMetric）介绍

复合指标类允许用户组合多个基础指标，并为每个指标分配权重，以创建一个综合评估指标。该类继承自BaseMetric，因此可以像任何其他指标一样在优化器中使用。

### 主要特性

1. **多指标组合**：可以组合任意数量的基础指标
2. **权重分配**：为每个指标分配权重，控制其在综合评分中的重要性
3. **兼容性**：与现有的优化器和评估框架完全兼容
4. **灵活性**：支持任何继承自BaseMetric的指标类

## 使用方法

### 1. 创建复合指标

```python
from diting_core.metrics.composite import CompositeMetric
from diting_core.metrics.context_recall.context_recall import ContextRecall
from diting_core.metrics.context_precision.context_precision import ContextPrecision

# 创建基础指标实例
context_recall_metric = ContextRecall(model=your_llm_model)
context_precision_metric = ContextPrecision(model=your_llm_model)

# 创建复合指标
composite_metric = CompositeMetric(
    metrics=[context_recall_metric, context_precision_metric],
    weights=[0.6, 0.4]  # context_recall占60%，context_precision占40%
)
```

### 2. 在优化器中使用复合指标

```python
from diting_core.optimization.retrieval.semantic_search.optimizer import SemanticSearchExhaustiveOptimizer
from diting_core.optimization.target.semantic_search_config import SemanticSearchConfig

# 创建优化器
optimizer = SemanticSearchExhaustiveOptimizer(
    similarity_threshold_range=(0.3, 0.9),
    similarity_threshold_step=0.1,
    context_recall_tokens_range=(500, 3000),
    context_recall_tokens_step=500
)

# 创建配置
config = SemanticSearchConfig.create_default(your_retriever)

# 执行优化，使用复合指标
result = await optimizer.optimize(
    config=config,
    dataset=your_dataset,
    metric=composite_metric,  # 使用复合指标
    n_samples=10
)
```

### 3. 权重配置说明

权重参数控制每个基础指标在综合评分中的重要性：

- 如果不提供权重参数，所有指标将被平均加权
- 权重会被自动归一化，因此不需要加和为1
- 权重值越大，对应指标在综合评分中的影响越大

```python
# 等权重（默认）
composite_metric = CompositeMetric(
    metrics=[metric1, metric2, metric3]
    # 等价于 weights=[1, 1, 1]，自动归一化为 [0.33, 0.33, 0.33]
)

# 自定义权重
composite_metric = CompositeMetric(
    metrics=[metric1, metric2],
    weights=[0.7, 0.3]  # metric1权重70%，metric2权重30%
)
```

## 实际应用示例

以下是一个完整的使用示例，展示了如何使用复合指标优化语义搜索参数：

```python
import asyncio
from diting_core.metrics.composite import CompositeMetric
from diting_core.metrics.context_recall.context_recall import ContextRecall
from diting_core.metrics.context_precision.context_precision import ContextPrecision
from diting_core.optimization.retrieval.semantic_search.optimizer import SemanticSearchExhaustiveOptimizer
from diting_core.optimization.target.semantic_search_config import SemanticSearchConfig
from diting_core.optimization.datasets.base_dataset import InMemoryDataset

async def optimize_with_composite_metric():
    # 1. 创建基础指标
    context_recall = ContextRecall(model=your_llm_model)
    context_precision = ContextPrecision(model=your_llm_model)
    
    # 2. 创建复合指标
    composite_metric = CompositeMetric(
        metrics=[context_recall, context_precision],
        weights=[0.5, 0.5]
    )
    
    # 3. 创建优化器
    optimizer = SemanticSearchExhaustiveOptimizer()
    
    # 4. 创建配置和数据集
    config = SemanticSearchConfig.create_default(your_retriever)
    dataset = InMemoryDataset("test_dataset", your_test_data)
    
    # 5. 执行优化
    result = await optimizer.optimize(
        config=config,
        dataset=dataset,
        metric=composite_metric,
        n_samples=5
    )
    
    # 6. 查看结果
    print(f"最佳评分: {result.best_score}")
    print(f"最佳参数: {result.details['best_params']}")

# 运行优化
asyncio.run(optimize_with_composite_metric())
```

## 注意事项

1. **指标兼容性**：确保所有基础指标都能处理优化器传递的数据格式
2. **权重设置**：根据业务需求合理设置权重，避免某一指标主导优化过程
3. **性能考虑**：使用多个指标会增加计算时间，合理设置并发数
4. **错误处理**：如果某个指标计算失败，其得分将被设为0，不影响其他指标的计算

## 扩展功能

复合指标类设计为可扩展的，您可以：

1. 继承CompositeMetric类创建自定义的多指标组合逻辑
2. 实现自己的权重计算方法
3. 添加指标间的依赖关系处理

通过使用复合指标，您可以更全面地评估模型性能，实现更平衡的优化结果。