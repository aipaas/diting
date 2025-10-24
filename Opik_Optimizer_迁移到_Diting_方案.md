# Opik Optimizer 迁移到 Diting 评估框架方案

## 项目概述

本文档详细说明了将 Opik Optimizer 的核心优化算法迁移到 Diting 评估框架的技术方案。目标是最大化复用 Diting 现有架构（包括 Langchain LLM 集成、llm_factory 等），仅迁移核心算法逻辑。

## 技术架构对比分析

### Diting 评估框架技术架构

**核心组件：**
1. **LLM 抽象层**：
   - `BaseLLM` 接口，标准化 `generate()` 和 `generate_structured_output()` 方法
   - `LangchainLLMWrapper` 基于 Langchain 的实现
   - `llm_factory` 工厂方法统一创建 LLM 实例

2. **评估指标系统**：
   - `BaseMetric` 抽象基类，标准化 `compute()` 接口
   - `MetricValue` 结果容器，包含分数、原因、日志
   - `LLMCase` 测试用例格式


**技术栈特点：**
- **LLM 后端**：Langchain (vs Opik 的 LiteLLM)
- **数据验证**：Pydantic
- **异步支持**：完整的 async/await 架构
- **回调机制**：内置 callback 管理器用于追踪和日志

### 关键技术差异对比

| 组件 | Opik Optimizer | Diting 框架 | 迁移策略 |
|------|---------------|-------------|----------|
| **LLM 后端** | LiteLLM (统一接口) | Langchain (ChatOpenAI等) | 适配现有 `llm_factory` |
| **提示配置** | `ChatPrompt` | 需新建 | 设计兼容的提示配置类 |
| **优化结果** | `OptimizationResult` | 需新建 | 适配 `MetricValue` 格式 |
| **数据集** | Opik Dataset | 需新建 | 适配语料库接口 |
| **评估指标** | 函数式接口 | `BaseMetric` 类 | 包装为指标类 |
| **实验追踪** | Comet ML 集成 | 回调机制 | 利用现有回调系统 |
| **缓存** | diskcache | 需实现 | 可选：添加缓存层 |

## 核心算法迁移方案

Opik Optimizer 提供 **7 种**优化算法，根据实际测试效果和 Diting AI 节点优化需求，建议的迁移优先级如下：

### 第一优先级算法（强烈建议优先迁移）⭐

1. **HierarchicalReflectiveOptimizer** - **经测试效果最好**
   - **核心逻辑**：两阶段层次化根因分析 + 多轮迭代优化
     1. 批次分析：将失败案例分批独立分析
     2. 综合分析：提取统一失败模式
     3. 针对性改进：为每个失败模式生成改进方案
     4. 迭代优化：重复评估直到收敛
   - **迁移难度**：中高，需要实现完整的根因分析框架
   - **应用场景**：复杂提示词的系统化优化，需要深入理解失败原因
   - **技术亮点**：
     - 异步并行批次分析（可配置 max_parallel_batches）
     - 智能收敛检测（convergence_threshold）
     - 自动重试机制（max_retries）
     - 结构化输出解析（需要适配 Pydantic 模型）
   - **关键依赖**：
     - HierarchicalRootCauseAnalyzer（核心分析器，需完整迁移）
     - 结构化输出支持（LiteLLM 的 response_format）
     - 异步评估框架

2. **ParameterOptimizer** - **AI 节点优化必备**
   - **核心逻辑**：使用贝叶斯优化调整 LLM 参数
   - **迁移难度**：低，最容易迁移
   - **优化对象**：temperature、top_p、top_k、max_tokens 等
   - **应用场景**：AI 节点优化不仅要优化提示词，还要优化模型参数
   - **技术依赖**：Optuna（贝叶斯优化库）
   - **优势**：可与提示词优化器组合使用，实现全面优化

### 第二优先级算法

3. **FewShotBayesianOptimizer** - 实用性强
   - **核心逻辑**：生成少样本示例 + 贝叶斯优化选择
   - **迁移难度**：中等，主要是适配接口
   - **应用场景**：明确定义的任务，需要通过示例引导 LLM

4. **EvolutionaryOptimizer** - 效果显著但成本高
   - **核心逻辑**：遗传算法的变异、交叉、选择、评估
   - **迁移难度**：高，需要完整的进化算法框架
   - **特点**：时间消耗较大，成本较高，但效果显著
   - **技术依赖**：DEAP（进化算法库）

### 第三优先级算法（可选）

5. **MetaPromptOptimizer** - 功能全面
   - **核心逻辑**：元提示技术优化
   - **迁移难度**：中等，需要适配工具调用
   - **特点**：支持真正的工具优化（MCP）- Beta 功能

6. **GepaOptimizer** - 遗传-帕累托优化器
   - **核心逻辑**：基于 GEPA（Genetic-Pareto）优化方法
   - **适用场景**：需要优化使用工具的代理系统

7. **MiproOptimizer** - 多输入提示优化器
   - **核心逻辑**：实现 MIPRO（Multi-Input Prompt Optimization）算法
   - **适用场景**：针对多输入场景的专门优化

## 适配 Diting 架构概述

详细的代码实现方案请参阅：**[Opik_Optimizer_适配_Diting_实现方案.md](./Opik_Optimizer_适配_Diting_实现方案.md)**

### 核心适配组件

#### 1. 基础组件
- **PromptConfig**：提示配置类，适配 Opik 的 ChatPrompt
- **OptimizationResult**：优化结果类，兼容 Diting 的 MetricValue 格式
- **BaseOptimizer**：优化器抽象基类，集成 Diting 回调机制

#### 2. LLM 适配层
- **OptimizerLLMAdapter**：将 Diting 的 LLM 接口适配为优化器所需格式

#### 3. 评估数据集系统（重要更新）
- **BaseDataset**：数据集基类，提供 `get_items(n_samples)` 接口
- **InMemoryDataset**：内存数据集实现
- **通用数据集**：
  - hotpot_300：HotpotQA 前 300 个样本
  - hotpot_500：HotpotQA 前 500 个样本
  - tiny_test：微型测试数据集（3个样本）
  - 其他：gsm8k, truthful_qa, ai2_arc 等（待实现）

#### 4. HierarchicalReflectiveOptimizer（Phase 3 核心）
- **类型定义**：FailureMode、BatchAnalysis、HierarchicalRootCauseAnalysis 等
- **HierarchicalRootCauseAnalyzer**：层次化根因分析器
  - 批次分析：并行分析多个批次
  - 综合分析：提取统一失败模式
  - 异步并发控制：使用 Semaphore 限制并发数
- **HierarchicalReflectiveOptimizer**：完整优化器实现
  - 多轮迭代优化
  - 收敛检测
  - 自动重试机制

### 关键技术点

#### 结构化输出 ⭐
Diting 原生支持结构化输出，无需适配器：
```python
# 直接使用 generate_structured_output
result = await llm.generate_structured_output(
    prompt=prompt,
    schema=ResponseModel,  # Pydantic 类
)
# result 已经是 ResponseModel 实例
```

#### 异步并发控制
```python
semaphore = asyncio.Semaphore(max_parallel_batches)
async def bounded_task(task):
    async with semaphore:
        return await task
results = await asyncio.gather(*[bounded_task(task) for task in tasks])
```

#### 需要迁移的提示词模板
- `BATCH_ANALYSIS_PROMPT`：批次根因分析
- `SYNTHESIS_PROMPT`：综合分析
- `IMPROVE_PROMPT_TEMPLATE`：提示词改进

## 目录结构建议

遵循 Diting-core 的目录结构规范："目录即作用域"，base 类文件使用 `base_*.py` 命名。

```
diting-core/src/diting_core/
├── optimization/                                # 优化器模块 ⭐ 新增
│   ├── __init__.py
│   ├── base_optimizer.py                        # 优化器基类
│   ├── result.py                                # 优化结果
│   │
│   ├── target/                                  # 优化目标（作用域）⭐ 扩展性设计
│   │   ├── __init__.py
│   │   ├── prompt_config.py                     # 提示词配置
│   │   ├── parameter_config.py                  # 模型参数配置（未来）
│   │   └── tool_config.py                       # 工具配置（未来）
│   │
│   ├── infra/                                   # 基础设施（作用域）⭐ 扩展性设计
│   │   ├── __init__.py
│   │   ├── llm_adapter.py                       # LLM 适配器
│   │   ├── cache.py                             # 缓存机制（未来）
│   │   └── rate_limiter.py                      # 速率限制（未来）
│   │
│   ├── datasets/                                # 评估数据集（作用域） ⭐ 新增
│   │   ├── __init__.py
│   │   ├── base_dataset.py                      # 数据集基类（遵循 base_*.py 规范）
│   │   ├── hotpot_qa.py                         # hotpot_300, hotpot_500 实现
│   │   ├── tiny_test.py                         # 微型测试数据集
│   │   ├── gsm8k.py                             # 数学推理数据集（未来）
│   │   ├── truthful_qa.py                       # 真实性评估（未来）
│   │   ├── ai2_arc.py                           # 科学常识（未来）
│   │   └── data/                                # 数据文件（放在作用域内）
│   │       ├── hotpot-500.json
│   │       └── ...
│   │
│   ├── algorithms/                              # 优化算法（作用域）
│   │   ├── __init__.py
│   │   │
│   │   ├── parameter/                          # 参数优化器（优先级1）
│   │   │   ├── __init__.py
│   │   │   ├── optimizer.py                    # 主优化器实现
│   │   │   └── bayesian_search.py              # 贝叶斯搜索实现
│   │   │
│   │   ├── hierarchical_reflective/            # 层次化反思优化器（优先级1）⭐
│   │   │   ├── __init__.py
│   │   │   ├── optimizer.py                    # 主优化器实现
│   │   │   ├── root_cause_analyzer.py          # 根因分析器
│   │   │   ├── types.py                        # Pydantic 类型定义
│   │   │   ├── prompts.py                      # 提示词模板
│   │   │   └── reporting.py                    # 报告和可视化
│   │   │
│   │   ├── few_shot_bayesian/                  # 少样本贝叶斯优化器（优先级2）
│   │   │   ├── __init__.py
│   │   │   ├── optimizer.py                    # 主优化器实现
│   │   │   ├── template_generator.py           # 模板生成器
│   │   │   └── bayesian_selector.py            # 贝叶斯选择器
│   │   │
│   │   ├── evolutionary/                       # 进化算法优化器（优先级2）
│   │   │   ├── __init__.py
│   │   │   ├── optimizer.py                    # 主优化器实现
│   │   │   ├── genetic_operators.py            # 遗传算子（变异、交叉、选择）
│   │   │   └── population.py                   # 种群管理
│   │   │
│   │   ├── meta_prompt/                        # 元提示优化器（优先级3）
│   │   │   ├── __init__.py
│   │   │   └── optimizer.py                    # 主优化器实现
│   │   │
│   │   ├── gepa/                               # GEPA 优化器（优先级3）
│   │   │   ├── __init__.py
│   │   │   └── optimizer.py                    # 主优化器实现
│   │   │
│   │   └── mipro/                              # MIPRO 优化器（优先级3）
│   │       ├── __init__.py
│   │       └── optimizer.py                    # 主优化器实现
│   │
│   └── utils/                                   # 工具函数（作用域）
│       ├── __init__.py
│       ├── prompt_utils.py                     # 提示工具函数
│       ├── optimization_utils.py               # 优化工具函数
│       ├── mutation_operators.py               # 变异操作符（进化算法用）
│       └── selection_operators.py              # 选择操作符（进化算法用）
```

### 目录结构设计原则

参考 Diting-core 现有模块（`metrics/`, `synthesis/` 等）的设计：

1. **base 类命名规范**：`base_*.py`（如 `base_dataset.py`, `base_optimizer.py`）
2. **目录即作用域**：数据文件放在 `datasets/data/` 内，而不是顶层 `data/`
3. **算法包组织**：所有优化算法统一使用子目录包的形式
   - 每个算法一个独立目录（如 `parameter/`, `hierarchical_reflective/`）
   - 主实现统一命名为 `optimizer.py`
   - 相关组件放在同一目录下（如 `root_cause_analyzer.py`, `types.py`）
4. **文件命名简洁**：避免冗余前缀（如 `optimizer.py` 而非 `hierarchical_reflective_optimizer.py`）
5. **扩展性设计**：
   - `target/` 目录：存放所有优化目标配置（提示词、参数、工具等），为未来扩展预留空间
     - 当前：`prompt_config.py`（提示词优化）
     - 未来：`parameter_config.py`（温度、top_p 等参数优化）
     - 未来：`tool_config.py`（工具调用优化）
   - `infra/` 目录：存放基础设施组件（适配器、缓存、限流等），集中管理底层依赖
     - 当前：`llm_adapter.py`
     - 未来：`cache.py`（优化结果缓存）
     - 未来：`rate_limiter.py`（API 速率限制）

### 使用示例

统一的包组织方式使得导入和使用更加一致：

```python
# 导入不同的优化器
from diting_core.optimization.algorithms.model_parameter import ParameterOptimizer
from diting_core.optimization.algorithms.hierarchical_reflective import HierarchicalReflectiveOptimizer
from diting_core.optimization.algorithms.evolutionary import EvolutionaryOptimizer

# 导入配置类
from diting_core.optimization.target.prompt_config import PromptConfig
from diting_core.optimization.datasets import hotpot_300
from diting_core.metrics import ExactMatch

# 使用优化器
optimizer = HierarchicalReflectiveOptimizer()
result = await optimizer.optimize_prompt(
    prompt_config=PromptConfig(...),
    dataset=hotpot_300(),
    metric=ExactMatch(),
    n_trials=10
)
```

## 依赖管理

需要在 `diting-core/pyproject.toml` 中添加：

```toml
dependencies = [
    # 现有依赖...
    "optuna>=3.0.0",           # 贝叶斯优化
    "deap>=1.4.0",            # 进化算法 (可选)
    "scipy>=1.9.0",           # 科学计算
    "numpy>=1.21.0",          # 数值计算
]

[project.optional-dependencies]
evolutionary = [
    "deap>=1.4.0",            # 进化算法优化器
]
meta-prompt = [
    "langchain-experimental",  # 实验性功能
]
```

## 分阶段实施策略

基于实际测试效果和 Diting AI 节点优化需求，调整实施优先级，优先迁移效果最好的算法。

### Phase 1: 基础架构 (1-2 周)

**目标：** 建立核心抽象和适配层

**任务：**
1. 实现 `PromptConfig`, `OptimizationResult` 等核心数据结构
2. 开发 `LLMAdapter`, `MetricAdapter`, `CorpusAdapter` 适配层
3. 建立基础的 `BaseOptimizer` 抽象
4. **新增**：实现结构化输出支持（适配 Pydantic 模型）
5. 编写单元测试验证适配层功能

**交付物：**
- 完整的基础架构代码
- 适配层单元测试（包括结构化输出测试）
- 基础文档

### Phase 2: 参数优化器 (1 周)

**目标：** 迁移最简单的算法验证架构，为 AI 节点提供参数优化能力

**任务：**
1. 迁移 `ParameterOptimizer`（最简单，优先验证架构）
2. 集成 Optuna 贝叶斯优化
3. 适配 Langchain LLM 参数配置
4. 验证整体架构可行性
5. 完善错误处理和日志

**交付物：**
- 可工作的 ParameterOptimizer
- 端到端测试用例
- 性能基准测试
- AI 节点参数优化示例

### Phase 3: 层次化反思优化器 (3-4 周) ⭐ **核心阶段**

**目标：** 迁移效果最好的算法，提供高质量提示词优化能力

**任务：**
1. 迁移 `HierarchicalReflectiveOptimizer` 核心逻辑
2. 实现 `HierarchicalRootCauseAnalyzer` 根因分析器
   - 批次分析逻辑
   - 综合分析逻辑
   - 失败模式提取
3. 实现类型定义（`FailureMode`, `ImprovedPrompt`, `HierarchicalRootCauseAnalysis`）
4. 适配异步并行评估
5. 实现多轮迭代和收敛检测
6. 实现重试机制
7. 添加详细的进度报告和可视化

**交付物：**
- 完整的 HierarchicalReflectiveOptimizer
- HierarchicalRootCauseAnalyzer 分析器
- 多轮迭代优化流程
- 详细的使用文档和最佳实践
- 真实场景的端到端测试

### Phase 4: 少样本优化器 (2-3 周)

**目标：** 迁移实用性强的少样本学习算法

**任务：**
1. 迁移 `FewShotBayesianOptimizer`
2. 实现少样本示例生成逻辑
3. 集成贝叶斯优化选择最佳示例组合
4. 添加缓存机制提高性能
5. 完善文档和示例

**交付物：**
- 完整的 FewShotBayesianOptimizer
- 缓存系统
- 使用示例和文档

### Phase 5: 进化算法优化器 (3-4 周)（可选）

**目标：** 迁移效果显著但成本较高的算法

**任务：**
1. 迁移 `EvolutionaryOptimizer`
2. 集成 DEAP 进化算法库
3. 实现变异、交叉、选择操作符
4. 性能优化和并行化
5. 成本控制和预算管理

**交付物：**
- 完整的 EvolutionaryOptimizer
- 性能优化的并行执行
- 高级配置选项
- 成本分析报告

### Phase 6: 扩展功能 (2-3 周)（可选）

**目标：** 迁移剩余算法和高级功能

**任务：**
1. 迁移 `MetaPromptOptimizer`（支持工具优化）
2. 可选：迁移 GepaOptimizer 和 MiproOptimizer
3. 优化器组合使用（如 HierarchicalReflective + Parameter）
4. 实验追踪和可视化增强
5. 全面的性能测试和对比

**交付物：**
- 全套优化算法（7种）
- 优化器组合使用指南
- 实验追踪和可视化功能
- 性能基准报告和算法对比

## 关键优势

1. **最大化复用**：充分利用 Diting 现有的 LLM、指标、回调系统
2. **渐进式迁移**：分阶段实施，每个阶段都有可用成果
3. **架构兼容**：设计与 Diting 风格一致的 API
4. **依赖最小化**：优先使用 Langchain 生态，减少外部依赖
5. **可扩展性**：为未来新算法提供标准化的扩展接口
6. **性能优化**：利用异步机制和批量处理提高效率

## 风险评估与缓解

### 主要风险

1. **LLM 接口差异**：Langchain 与 LiteLLM 在参数和行为上可能有差异
   - **缓解措施**：完善的适配层和充分的测试

2. **性能问题**：大量 LLM 调用可能导致性能瓶颈
   - **缓解措施**：实现缓存、批量处理和并行执行

3. **算法复杂度**：进化算法等复杂算法迁移难度较高
   - **缓解措施**：分阶段实施，从简单算法开始

### 质量保证

1. **单元测试**：每个组件都要有充分的单元测试
2. **集成测试**：端到端的优化流程测试
3. **性能测试**：与原始实现的性能对比
4. **文档完善**：详细的 API 文档和使用示例

这个迁移方案既保留了 Opik Optimizer 的核心算法价值，又充分利用了 Diting 框架的技术优势，实现了最佳的技术融合效果。