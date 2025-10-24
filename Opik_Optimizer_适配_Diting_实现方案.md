# Opik Optimizer 适配 Diting 架构实现方案

本文档详细说明如何将 Opik Optimizer 的核心算法适配到 Diting 评估框架的技术实现细节。

## 文档说明

本文档是 `Opik_Optimizer_迁移到_Diting_方案.md` 的配套技术文档，主要关注：
- 核心组件的代码实现
- 适配层的详细设计
- HierarchicalReflectiveOptimizer 的完整实现
- 技术难点和解决方案

建议先阅读主方案文档，了解整体迁移策略和优先级。

## 目录结构设计

遵循 Diting-core 的扩展性设计原则：

```
optimization/
├── target/         # 优化目标配置（提示词、参数、工具等）
├── infra/          # 基础设施（适配器、缓存、限流等）
├── datasets/       # 评估数据集
├── algorithms/     # 优化算法
└── utils/          # 工具函数
```

**设计理念**：
- `target/` 目录为未来多样化的优化目标预留空间（不仅限于提示词）
- `infra/` 目录集中管理底层依赖，便于维护和扩展
- `algorithms/` 目录下所有优化器统一使用子目录包形式组织：
  ```
  algorithms/
  ├── parameter/              # 参数优化器包
  │   ├── optimizer.py        # 主实现
  │   └── bayesian_search.py  # 相关组件
  ├── hierarchical_reflective/
  │   ├── optimizer.py
  │   ├── root_cause_analyzer.py
  │   └── types.py
  └── evolutionary/
      ├── optimizer.py
      ├── genetic_operators.py
      └── population.py
  ```

---

## 1. 核心组件设计

### 1.1 提示配置类

```python
# diting_core/optimization/target/prompt_config.py
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class PromptConfig(BaseModel):
    """提示配置类，适配 Opik 的 ChatPrompt

    存放在 target/ 目录下，与未来的 parameter_config.py、tool_config.py 等并列，
    体现优化目标的扩展性设计。
    """
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    messages: Optional[List[Dict[str, str]]] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    model_params: Optional[Dict[str, Any]] = None
```

### 1.2 优化结果类

```python
# diting_core/optimization/optimization_result.py
class OptimizationResult(BaseModel):
    """优化结果，兼容 MetricValue 格式"""
    best_prompt: PromptConfig
    best_score: float
    improvement: float
    optimization_history: List[Dict[str, Any]]
    experiment_metadata: Optional[Dict[str, Any]] = None
    total_llm_calls: int = 0
    total_cost: Optional[float] = None
```

### 1.3 优化器基类

```python
# diting_core/optimization/base_optimizer.py
from abc import ABC, abstractmethod
from diting_core.callbacks.manager import new_group
from diting_core.metrics.base_metric import BaseMetric
from diting_core.synthesis.base_corpus import BaseCorpus

class BaseOptimizer(ABC):
    """优化器基类，复用 Diting 的回调机制"""

    def __init__(self, llm_factory_func=None):
        self.llm_factory = llm_factory_func or llm_factory
        self.llm_call_count = 0
        self.optimization_history = []

    async def optimize_prompt(
        self,
        prompt_config: PromptConfig,
        dataset: BaseDataset,
        metric: BaseMetric,
        n_trials: int = 10,
        **kwargs
    ) -> OptimizationResult:
        """标准化的优化接口

        Args:
            prompt_config: 提示配置
            dataset: 评估数据集（使用 BaseDataset，而不是 BaseCorpus）
            metric: 评估指标（直接使用 BaseMetric，不需要适配器）
            n_trials: 优化试验次数
            **kwargs: 其他优化参数
        """
        # 使用 Diting 的回调系统进行追踪
        run_manager, grp_cb = await new_group(
            name=self.__class__.__name__,
            inputs={
                "prompt_config": prompt_config,
                "dataset": dataset.name,
                "n_trials": n_trials
            },
            callbacks=kwargs.pop("callbacks", None),
            verbose=kwargs.get("verbose", False),
            chain_type="OPTIMIZER"
        )

        try:
            result = await self._optimize(
                prompt_config, dataset, metric, n_trials,
                callbacks=grp_cb, **kwargs
            )
        except Exception as e:
            await run_manager.on_chain_error(e)
            raise e

        await run_manager.on_chain_end({"optimization_result": result})
        return result

    @abstractmethod
    async def _optimize(
        self,
        prompt_config: PromptConfig,
        dataset: BaseDataset,
        metric: BaseMetric,
        n_trials: int,
        **kwargs
    ) -> OptimizationResult:
        """子类实现的具体优化逻辑"""
        raise NotImplementedError
```

---

## 2. LLM 适配层

```python
# diting_core/optimization/infra/llm_adapter.py
import asyncio
from typing import List, Optional, Any
from diting_core.models.llms.base_model import BaseLLM
from diting_core.models.llms.factory import llm_factory


class OptimizerLLMAdapter:
    """将 Diting 的 LLM 接口适配为优化器所需的格式

    存放在 infra/ 目录下，与未来的 cache.py、rate_limiter.py 等并列，
    集中管理基础设施组件。
    """

    def __init__(self, llm: BaseLLM):
        self.llm = llm
        self.call_count = 0

    async def generate_single(
            self,
            prompt: str,
            temperature: Optional[float] = None,
            **kwargs
    ) -> str:
        """单次生成"""
        self.call_count += 1
        result = await self.llm.generate(
            prompt,
            temperature=temperature,
            **kwargs
        )
        return result if isinstance(result, str) else result[0]

    async def generate_batch(
            self,
            prompts: List[str],
            n: int = 1,
            temperature: Optional[float] = None,
            **kwargs
    ) -> List[str]:
        """批量生成，适配优化算法需求"""
        self.call_count += len(prompts) * n

        tasks = []
        for prompt in prompts:
            task = self.llm.generate(
                prompt,
                n=n,
                temperature=temperature,
                **kwargs
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # 展平结果
        flattened = []
        for result in results:
            if isinstance(result, list):
                flattened.extend(result)
            else:
                flattened.append(result)

        return flattened

    async def generate_with_config(
            self,
            prompt_config: PromptConfig,
            user_input: str = "",
            **kwargs
    ) -> str:
        """使用配置生成响应"""
        if prompt_config.messages:
            prompt = self._format_messages(prompt_config.messages, user_input)
        else:
            prompt = self._format_prompt(
                prompt_config.system,
                prompt_config.user,
                user_input
            )

        return await self.generate_single(
            prompt,
            temperature=prompt_config.temperature,
            **kwargs
        )

    def _format_messages(self, messages: List[Dict[str, str]], user_input: str) -> str:
        """将消息格式转换为字符串提示"""
        formatted_parts = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if "{user_input}" in content:
                content = content.format(user_input=user_input)
            formatted_parts.append(f"{role}: {content}")
        return "\n\n".join(formatted_parts)

    def _format_prompt(
            self,
            system_prompt: Optional[str],
            user_prompt: Optional[str],
            user_input: str
    ) -> str:
        """格式化系统提示和用户提示"""
        parts = []
        if system_prompt:
            parts.append(f"System: {system_prompt}")
        if user_prompt:
            formatted_user = user_prompt.format(user_input=user_input) if "{user_input}" in user_prompt else user_prompt
            parts.append(f"User: {formatted_user}")
        elif user_input:
            parts.append(f"User: {user_input}")

        return "\n\n".join(parts)
```

---

## 3. 评估数据集系统

### 3.1 数据集基类

```python
# diting_core/optimization/datasets/base_dataset.py
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

class BaseDataset(ABC):
    """优化器数据集基类

    参考 Opik Dataset 的设计，提供标准的数据集接口
    """

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def get_items(self, n_samples: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取数据集项目

        Args:
            n_samples: 可选，限制返回的项目数量

        Returns:
            数据项列表，每个项目是一个字典，通常包含：
            - id: 唯一标识
            - input: 输入数据
            - expected_output: 期望输出（如果有）
            - context: 上下文信息（如果有）
        """
        raise NotImplementedError

    def __len__(self) -> int:
        """返回数据集大小"""
        return len(self.get_items())


class InMemoryDataset(BaseDataset):
    """内存数据集实现"""

    def __init__(self, name: str, items: List[Dict[str, Any]]):
        super().__init__(name)
        self._items = items

    def get_items(self, n_samples: Optional[int] = None) -> List[Dict[str, Any]]:
        if n_samples is None:
            return self._items
        return self._items[:n_samples]
```

### 3.2 通用数据集实现

```python
# diting_core/optimization/datasets/hotpot_qa.py
import json
from pathlib import Path
from typing import Optional
from .base_dataset import BaseDataset, InMemoryDataset

def hotpot_300(test_mode: bool = False) -> BaseDataset:
    """HotpotQA 数据集前 300 个样本

    参考 Opik 的实现：
    - 从 JSON 文件加载数据
    - 支持 test_mode（仅5个样本用于测试）

    Returns:
        BaseDataset 实例
    """
    nb_items = 300 if not test_mode else 5
    dataset_name = f"hotpot_300{'_test' if test_mode else ''}"

    # 加载数据文件
    data_file = Path(__file__).parent / "data" / "hotpot-500.json"
    with open(data_file, 'r', encoding='utf-8') as f:
        all_data = json.load(f)

    # 取前 nb_items 个样本
    items = all_data[:nb_items]

    # 标准化数据格式
    formatted_items = []
    for idx, item in enumerate(items):
        formatted_items.append({
            "id": f"hotpot_{idx}",
            "input": item.get("question", ""),
            "expected_output": item.get("answer", ""),
            "context": item.get("context", []),
            # 保留原始数据
            **item
        })

    return InMemoryDataset(dataset_name, formatted_items)


def hotpot_500(test_mode: bool = False) -> BaseDataset:
    """HotpotQA 数据集前 500 个样本"""
    nb_items = 500 if not test_mode else 5
    dataset_name = f"hotpot_500{'_test' if test_mode else ''}"

    data_file = Path(__file__).parent / "data" / "hotpot-500.json"
    with open(data_file, 'r', encoding='utf-8') as f:
        all_data = json.load(f)

    items = all_data[:nb_items]

    formatted_items = []
    for idx, item in enumerate(items):
        formatted_items.append({
            "id": f"hotpot_{idx}",
            "input": item.get("question", ""),
            "expected_output": item.get("answer", ""),
            "context": item.get("context", []),
            **item
        })

    return InMemoryDataset(dataset_name, formatted_items)
```

```python
# diting_core/optimization/datasets/tiny_test.py
from .base_dataset import InMemoryDataset, BaseDataset

def tiny_test() -> BaseDataset:
    """微型测试数据集，用于快速验证"""
    items = [
        {
            "id": "tiny_1",
            "input": "What is the capital of France?",
            "expected_output": "Paris",
        },
        {
            "id": "tiny_2",
            "input": "What is 2 + 2?",
            "expected_output": "4",
        },
        {
            "id": "tiny_3",
            "input": "Who wrote Romeo and Juliet?",
            "expected_output": "William Shakespeare",
        },
    ]
    return InMemoryDataset("tiny_test", items)
```

```python
# diting_core/optimization/datasets/__init__.py
"""优化器评估数据集

包含常用的评估数据集，用于提示词优化
"""

from .hotpot_qa import hotpot_300, hotpot_500
from .tiny_test import tiny_test
# from .gsm8k import gsm8k
# from .truthful_qa import truthful_qa
# from .ai2_arc import ai2_arc

__all__ = [
    "hotpot_300",
    "hotpot_500",
    "tiny_test",
    # "gsm8k",
    # "truthful_qa",
    # "ai2_arc",
]
```

### 3.3 数据集使用方式

```python
# 使用示例
from diting_core.optimization.datasets import hotpot_300, tiny_test

# 加载数据集
dataset = hotpot_300(test_mode=False)

# 获取所有项目
all_items = dataset.get_items()

# 获取前 10 个样本
sample_items = dataset.get_items(n_samples=10)

# 数据集大小
print(f"Dataset size: {len(dataset)}")
```

---

## 5. HierarchicalReflectiveOptimizer 完整实现

### 5.1 类型定义

```python
# diting_core/optimization/algorithms/hierarchical_reflective/types.py
from pydantic import BaseModel
from typing import List

class FailureMode(BaseModel):
    """失败模式定义"""
    name: str
    description: str
    root_cause: str

class RootCauseAnalysis(BaseModel):
    """单批次根因分析结果"""
    failure_modes: List[FailureMode]

class BatchAnalysis(BaseModel):
    """批次分析结果"""
    batch_number: int
    start_index: int
    end_index: int
    failure_modes: List[FailureMode]

class HierarchicalRootCauseAnalysis(BaseModel):
    """层次化根因分析最终结果"""
    total_test_cases: int
    num_batches: int
    unified_failure_modes: List[FailureMode]
    synthesis_notes: str

class PromptMessage(BaseModel):
    """提示消息"""
    role: str
    content: str

class ImprovedPrompt(BaseModel):
    """改进后的提示"""
    reasoning: str
    messages: List[PromptMessage]
```

### 5.2 层次化根因分析器

```python
# diting_core/optimization/algorithms/hierarchical_reflective/root_cause_analyzer.py
import asyncio
import logging
from typing import List, Any, Callable
from diting_core.evaluation.evaluation_result import EvaluationResult
from .types import (
    RootCauseAnalysis,
    BatchAnalysis,
    HierarchicalRootCauseAnalysis,
    FailureMode
)

logger = logging.getLogger(__name__)

class HierarchicalRootCauseAnalyzer:
    """层次化根因分析器

    核心功能：
    1. 将大型评估数据集分批处理
    2. 并行分析每个批次的根本原因
    3. 综合所有批次结果，提取统一的失败模式

    Args:
        call_model_fn: 异步 LLM 调用函数
        reasoning_model: 推理模型名称
        seed: 随机种子
        max_parallel_batches: 最大并行批次数（默认5）
        batch_size: 每批次测试用例数（默认25）
        verbose: 是否显示详细信息
    """

    def __init__(
        self,
        call_model_fn: Callable,
        reasoning_model: str,
        seed: int,
        max_parallel_batches: int = 5,
        batch_size: int = 25,
        verbose: bool = True,
    ):
        self.call_model_fn = call_model_fn
        self.reasoning_model = reasoning_model
        self.seed = seed
        self.max_parallel_batches = max_parallel_batches
        self.batch_size = batch_size
        self.verbose = verbose

    def _format_test_results_batch(
        self,
        test_results: List[Any],
        batch_start: int,
        batch_end: int,
    ) -> str:
        """格式化批次测试结果用于分析"""
        formatted_results = []

        for idx in range(batch_start, min(batch_end, len(test_results))):
            test_result = test_results[idx]

            # 提取分数信息
            scores_info = []
            for score in test_result.score_results:
                score_str = f"  - {score.name}: {score.value:.3f}"
                if score.reason:
                    score_str += f"\n    原因: {score.reason}"
                if score.scoring_failed:
                    score_str += " (失败)"
                scores_info.append(score_str)

            # 格式化测试结果
            result_text = f"""测试用例 #{idx + 1}
分数:
{chr(10).join(scores_info)}"""

            formatted_results.append(result_text)

        return "\n\n" + ("=" * 80 + "\n\n").join(formatted_results)

    async def _analyze_batch_async(
        self,
        evaluation_result: EvaluationResult,
        batch_number: int,
        batch_start: int,
        batch_end: int,
    ) -> BatchAnalysis:
        """异步分析单个批次"""
        test_results = evaluation_result.test_results
        actual_end = min(batch_end, len(test_results))

        logger.debug(
            f"分析批次 {batch_number}: "
            f"测试用例 {batch_start + 1} 到 {actual_end}"
        )

        # 格式化批次数据
        formatted_batch = self._format_test_results_batch(
            test_results, batch_start, batch_end
        )

        # 构建批次分析提示词
        batch_analysis_prompt = self._build_batch_analysis_prompt(formatted_batch)

        # 使用 Diting 原生的结构化输出接口 ⭐
        root_cause_response = await self.llm.generate_structured_output(
            prompt=batch_analysis_prompt,
            schema=RootCauseAnalysis,
        )

        return BatchAnalysis(
            batch_number=batch_number,
            start_index=batch_start,
            end_index=actual_end,
            failure_modes=root_cause_response.failure_modes,
        )

    async def _synthesize_batch_analyses_async(
        self,
        batch_analyses: List[BatchAnalysis],
        total_test_cases: int,
    ) -> HierarchicalRootCauseAnalysis:
        """综合所有批次分析，提取统一失败模式"""

        # 构建综合分析提示词
        synthesis_prompt = self._build_synthesis_prompt(
            batch_analyses, total_test_cases
        )

        # 使用 Diting 原生的结构化输出接口 ⭐
        synthesis_response = await self.llm.generate_structured_output(
            prompt=synthesis_prompt,
            schema=HierarchicalRootCauseAnalysis,
        )

        return synthesis_response

    async def analyze(
        self,
        evaluation_result: EvaluationResult
    ) -> HierarchicalRootCauseAnalysis:
        """执行完整的层次化根因分析

        流程：
        1. 将评估结果分批
        2. 并行分析每个批次（限制并发数）
        3. 综合所有批次结果

        Returns:
            HierarchicalRootCauseAnalysis 包含统一的失败模式
        """
        test_results = evaluation_result.test_results
        total_test_cases = len(test_results)

        # 计算批次
        num_batches = (total_test_cases + self.batch_size - 1) // self.batch_size

        logger.info(
            f"开始层次化根因分析: {total_test_cases} 个测试用例, "
            f"{num_batches} 个批次, 最大并行 {self.max_parallel_batches} 批次"
        )

        # 创建批次分析任务
        batch_tasks = []
        for batch_num in range(num_batches):
            batch_start = batch_num * self.batch_size
            batch_end = min(batch_start + self.batch_size, total_test_cases)

            task = self._analyze_batch_async(
                evaluation_result, batch_num + 1, batch_start, batch_end
            )
            batch_tasks.append(task)

        # 使用信号量限制并发数
        semaphore = asyncio.Semaphore(self.max_parallel_batches)

        async def bounded_analyze(task):
            async with semaphore:
                return await task

        # 并行执行批次分析
        batch_analyses = await asyncio.gather(
            *[bounded_analyze(task) for task in batch_tasks]
        )

        logger.info(f"批次分析完成，开始综合分析...")

        # 综合所有批次分析
        hierarchical_analysis = await self._synthesize_batch_analyses_async(
            batch_analyses, total_test_cases
        )

        return hierarchical_analysis

    def _build_batch_analysis_prompt(self, formatted_batch: str) -> str:
        """构建批次分析提示词

        这里需要实现具体的提示词模板，可以参考 Opik 的 BATCH_ANALYSIS_PROMPT
        提示词应该引导 LLM 分析批次中的失败模式，包括：
        - 失败模式的名称
        - 详细描述
        - 根本原因
        """
        return f"""请分析以下测试结果批次，识别失败模式。

{formatted_batch}

请返回 JSON 格式，包含 failure_modes 列表，每个失败模式需要包含：
- name: 失败模式的简短名称
- description: 详细描述
- root_cause: 根本原因分析
"""

    def _build_synthesis_prompt(
        self,
        batch_analyses: List[BatchAnalysis],
        total_test_cases: int
    ) -> str:
        """构建综合分析提示词

        这里需要实现具体的提示词模板，可以参考 Opik 的 SYNTHESIS_PROMPT
        提示词应该引导 LLM 综合多个批次的分析结果，提取统一的失败模式
        """
        batch_summaries = []
        for batch in batch_analyses:
            summary = f"批次 {batch.batch_number} (测试用例 {batch.start_index+1}-{batch.end_index}):\n"
            for fm in batch.failure_modes:
                summary += f"  - {fm.name}: {fm.description}\n"
            batch_summaries.append(summary)

        return f"""请综合以下 {len(batch_analyses)} 个批次的分析结果（共 {total_test_cases} 个测试用例），
提取统一的失败模式。

{chr(10).join(batch_summaries)}

请返回 JSON 格式，包含：
- total_test_cases: 总测试用例数
- num_batches: 批次数
- unified_failure_modes: 统一的失败模式列表
- synthesis_notes: 综合分析说明
"""
```

### 5.3 HierarchicalReflectiveOptimizer 实现

```python
# diting_core/optimization/algorithms/hierarchical_reflective/optimizer_name.py
from typing import Optional, Callable, Any
from diting_core.optimization.base_optimizer import BaseOptimizer
from diting_core.optimization.target.prompt_config import PromptConfig
from diting_core.optimization.optimization_result import OptimizationResult
from diting_core.optimization.datasets.base_dataset import BaseDataset
from diting_core.metrics.base_metric import BaseMetric
from .root_cause_analyzer import HierarchicalRootCauseAnalyzer
from .types import FailureMode, ImprovedPrompt


class HierarchicalReflectiveOptimizer(BaseOptimizer):
    """层次化反思优化器

    使用两阶段层次化根因分析来改进提示词：
    1. 批次分析阶段：分批独立分析失败案例
    2. 综合分析阶段：提取统一失败模式
    3. 迭代优化阶段：针对每个失败模式生成改进方案

    Args:
        reasoning_model: 用于分析的模型名称（默认使用主模型）
        num_threads: 评估并行线程数
        max_parallel_batches: 最大并行批次数（默认5）
        batch_size: 每批次测试用例数（默认25）
        max_iterations: 最大迭代次数（默认5）
        convergence_threshold: 收敛阈值（默认0.01，即1%）
        max_retries: 每个失败模式的最大重试次数（默认2）
    """

    DEFAULT_MAX_ITERATIONS = 5
    DEFAULT_CONVERGENCE_THRESHOLD = 0.01

    def __init__(
            self,
            reasoning_model: Optional[str] = None,
            num_threads: int = 12,
            max_parallel_batches: int = 5,
            batch_size: int = 25,
            max_iterations: int = DEFAULT_MAX_ITERATIONS,
            convergence_threshold: float = DEFAULT_CONVERGENCE_THRESHOLD,
            max_retries: int = 2,
            **kwargs
    ):
        super().__init__(**kwargs)
        self.reasoning_model = reasoning_model
        self.num_threads = num_threads
        self.max_parallel_batches = max_parallel_batches
        self.batch_size = batch_size
        self.max_iterations = max_iterations
        self.convergence_threshold = convergence_threshold
        self.max_retries = max_retries

        # 初始化层次化分析器
        self._hierarchical_analyzer = HierarchicalRootCauseAnalyzer(
            call_model_fn=self._call_model_async,
            reasoning_model=self.reasoning_model or self.llm.model_name,
            seed=42,
            max_parallel_batches=self.max_parallel_batches,
            batch_size=self.batch_size,
            verbose=True,
        )

    async def _optimize(
            self,
            prompt_config: PromptConfig,
            dataset: BaseDataset,
            metric: BaseMetric,
            n_trials: int,
            **kwargs
    ) -> OptimizationResult:
        """核心优化逻辑（多轮迭代）"""

        # 1. 基线评估
        baseline_result = await self._evaluate_prompt(
            prompt_config, dataset, metric
        )
        baseline_score = baseline_result.average_score

        best_prompt = prompt_config
        best_score = baseline_score
        previous_score = baseline_score

        # 2. 多轮迭代优化
        for iteration in range(1, self.max_iterations + 1):

            # 2.1 层次化根因分析
            hierarchical_analysis = await self._hierarchical_analyzer.analyze(
                baseline_result
            )

            # 2.2 针对每个失败模式进行优化
            for failure_mode in hierarchical_analysis.unified_failure_modes:

                # 尝试多次改进
                for attempt in range(1, self.max_retries + 1):

                    # 生成改进提示词
                    improved_prompt = await self._improve_prompt(
                        best_prompt, failure_mode, attempt
                    )

                    # 评估改进效果
                    improved_result = await self._evaluate_prompt(
                        improved_prompt, dataset, metric
                    )
                    improved_score = improved_result.average_score

                    # 如果有改进，更新最佳提示词
                    if improved_score > best_score:
                        best_prompt = improved_prompt
                        best_score = improved_score
                        baseline_result = improved_result
                        break

            # 2.3 检查收敛
            iteration_improvement = (best_score - previous_score) / previous_score
            if abs(iteration_improvement) < self.convergence_threshold:
                break

            previous_score = best_score

        # 3. 返回优化结果
        return OptimizationResult(
            best_config=best_prompt,
            best_score=best_score,
            improvement=(best_score - baseline_score) / baseline_score,
            history=history,
            total_llm_calls=self.llm_call_count,
        )

    async def _improve_prompt(
            self,
            current_prompt: PromptConfig,
            failure_mode: FailureMode,
            attempt: int,
    ) -> PromptConfig:
        """基于失败模式生成改进提示词"""

        # 构建改进提示词
        improve_prompt = self._build_improve_prompt(
            current_prompt, failure_mode
        )

        # 使用 Diting 原生的结构化输出接口 ⭐
        improved_response = await self.llm.generate_structured_output(
            prompt=improve_prompt,
            schema=ImprovedPrompt,
        )

        # 转换为 PromptConfig
        return self._convert_to_prompt_config(improved_response)

    def _build_improve_prompt(
            self,
            current_prompt: PromptConfig,
            failure_mode: FailureMode
    ) -> str:
        """构建改进提示词

        这里需要实现具体的提示词模板，可以参考 Opik 的 IMPROVE_PROMPT_TEMPLATE
        """
        return f"""请改进以下提示词以解决识别出的失败模式。

当前提示词:
{current_prompt.messages}

失败模式:
名称: {failure_mode.name}
描述: {failure_mode.description}
根本原因: {failure_mode.root_cause}

请返回 JSON 格式，包含：
- reasoning: 改进思路
- messages: 改进后的消息列表（包含 role 和 content）
"""

    def _convert_to_prompt_config(self, improved_response: ImprovedPrompt) -> PromptConfig:
        """将 ImprovedPrompt 转换为 PromptConfig"""
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in improved_response.messages
        ]
        return PromptConfig(messages=messages)
```

---

## 6. 关键迁移点总结

### 6.1 结构化输出支持 ⭐

**Opik 实现**：
```python
response = litellm.completion(
    model=model,
    messages=messages,
    response_format={"type": "json_object"},
    **kwargs
)
result = ResponseModel.model_validate_json(response.choices[0].message.content)
```

**Diting 原生支持** ✅：
```python
# Diting 的 BaseLLM 已经原生支持结构化输出
# 参考 diting_core/models/llms/base_model.py

result = await llm.generate_structured_output(
    prompt=prompt,
    schema=ResponseModel,  # 直接传入 Pydantic 类
    **kwargs
)
# result 已经是 ResponseModel 实例，无需额外解析！
```

**在优化器中使用**：
```python
# HierarchicalRootCauseAnalyzer 中
async def _analyze_batch_async(self, ...):
    # 直接使用 generate_structured_output
    root_cause_response = await self.llm.generate_structured_output(
        prompt=batch_analysis_prompt,
        schema=RootCauseAnalysis,
    )
    # root_cause_response 已经是 RootCauseAnalysis 实例
    return BatchAnalysis(
        batch_number=batch_number,
        start_index=batch_start,
        end_index=actual_end,
        failure_modes=root_cause_response.failure_modes,
    )
```

> **重要**：~~不需要 StructuredOutputAdapter~~！Diting 的 `generate_structured_output` 已经完美支持 Pydantic 模型。

### 7.2 异步并发控制

**核心代码**：
```python
import asyncio

# 创建信号量限制并发数
semaphore = asyncio.Semaphore(max_parallel_batches)

async def bounded_task(task):
    async with semaphore:
        return await task

# 并行执行任务
results = await asyncio.gather(
    *[bounded_task(task) for task in tasks]
)
```

### 7.3 提示词模板迁移

需要从 Opik 迁移的提示词模板：
1. `BATCH_ANALYSIS_PROMPT` - 批次分析提示词
2. `SYNTHESIS_PROMPT` - 综合分析提示词
3. `IMPROVE_PROMPT_TEMPLATE` - 改进生成提示词

建议在 `prompts.py` 中统一管理这些模板。

---

## 8. 测试策略

### 8.1 单元测试

```python
# tests/optimization/test_hierarchical_root_cause_analyzer.py
import pytest
from diting_core.optimization.algorithms.hierarchical_reflective import (
    HierarchicalRootCauseAnalyzer
)

@pytest.mark.asyncio
async def test_batch_analysis():
    """测试批次分析功能"""
    # 测试实现
    pass

@pytest.mark.asyncio
async def test_synthesis():
    """测试综合分析功能"""
    # 测试实现
    pass
```

### 8.2 集成测试

```python
# tests/optimization/test_hierarchical_reflective_optimizer_integration.py
import pytest
from diting_core.optimization.algorithms.hierarchical_reflective import (
    HierarchicalReflectiveOptimizer
)

@pytest.mark.asyncio
async def test_full_optimization_flow():
    """测试完整的优化流程"""
    # 测试实现
    pass
```

---

## 9. 性能优化建议

1. **缓存机制**：为 LLM 调用添加缓存，避免重复计算
2. **批量处理**：尽可能使用批量 API 减少网络开销
3. **并发调优**：根据 API 限制调整 `max_parallel_batches`
4. **结果复用**：在迭代优化中复用已评估的结果

---

## 10. 参考资源

- Opik Optimizer 源码：`opik/sdks/opik_optimizer/`
- Langchain 结构化输出文档：https://python.langchain.com/docs/how_to/structured_output/
- Pydantic 文档：https://docs.pydantic.dev/
- Asyncio 文档：https://docs.python.org/3/library/asyncio.html
