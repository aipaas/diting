# ⚡ diting-optimizer: Advanced Optimization Engine for LLM Applications

`diting-optimizer` is the sophisticated optimization module of the DiTing framework, designed to automatically improve LLM application performance through advanced algorithms. It provides powerful optimization capabilities for both prompt content and model parameters, enabling systematic performance enhancement across different datasets and evaluation metrics.

## 🎯 Core Purpose

`diting-optimizer` focuses on enabling automated, data-driven optimization of LLM applications by leveraging advanced search algorithms and machine learning techniques. Its primary goals are:

1. **Automatically optimize prompt content** using hierarchical analysis and iterative refinement
2. **Fine-tune model hyperparameters** with state-of-the-art optimization algorithms (TPE)
3. **Provide comprehensive optimization tracking** with detailed history and progress monitoring
4. **Support extensible optimization framework** for adding new algorithms and strategies
5. **Enable systematic performance improvement** through data-driven experimentation

## 🔍 Key Algorithms

### 1. Hierarchical Reflective Optimizer
Advanced prompt optimization using root cause analysis and iterative improvement.

- **Core Approach**: Two-stage hierarchical analysis (batch analysis → unified failure mode identification)
- **Multi-iteration Optimization**: Convergence detection with configurable stopping criteria
- **Failure Mode Classification**: Systematic identification and categorization of prompt weaknesses
- **Retry Mechanism**: Multiple optimization attempts with different seeds for robustness

#### **Optimization Process**

1. **Batch Analysis**: Analyze multiple test cases to identify common failure patterns
2. **Root Cause Identification**: Extract unified failure modes across the batch
3. **Prompt Improvement**: Generate enhanced prompts based on failure analysis
4. **Iterative Refinement**: Continue optimization until convergence or max iterations

### 2. TPE Parameter Optimizer
Model hyperparameter optimization using Tree-structured Parzen Estimator.

- **Algorithm**: Optuna's TPE sampler for efficient hyperparameter search
- **Two-phase Search**: Global exploration (70% of trials) → Local refinement (30% of trials)
- **Parameter Types**: Support for FLOAT, INT, and CATEGORICAL parameters
- **Adaptive Range**: Dynamic range narrowing around best-performing parameters

#### **Search Space Definition**

```python
parameter_space = ParameterSearchSpace(
    parameters=[
        ParameterSpec(
            name="temperature",
            distribution=ParameterType.FLOAT,
            low=0.0, high=1.0
        ),
        ParameterSpec(
            name="max_tokens",
            distribution=ParameterType.INT,
            low=10, high=1000
        ),
        ParameterSpec(
            name="model_choice",
            distribution=ParameterType.CATEGORICAL,
            choices=["gpt-3.5-turbo", "gpt-4", "claude-3"]
        )
    ]
)
```

## 🏗️ Architecture Components

### 1. Base Optimizer Framework
Abstract foundation providing common optimization interfaces and utilities.

- **`BaseOptimizer`**: Abstract base class with standard optimization workflow
- **Token Tracking**: Comprehensive monitoring of LLM and embedding API usage
- **Callback Integration**: Seamless integration with DiTing's callback system
- **Result Aggregation**: Structured collection and analysis of optimization results

### 2. Optimization Results System
Comprehensive result tracking and analysis inspired by Opik's design.

- **`OptimizationResult`**: Complete optimization history with best configurations
- **Performance Tracking**: Detailed scoring and improvement metrics
- **Convergence Analysis**: Detection of optimization convergence and plateau points
- **Metadata Management**: Rich contextual information for optimization runs

### 3. Target Configuration System
Flexible configuration management for optimization targets.

- **`PromptConfig`**: Comprehensive prompt configuration with multiple formats
- **Template Variables**: Dynamic content substitution for flexible prompts
- **Model Parameters**: Full integration with LLM configuration options
- **Async Execution**: Self-contained async execution with proper error handling

### 4. Dataset Infrastructure
Robust dataset management for optimization workflows.

- **`BaseDataset`**: Abstract interface for extensible data sources
- **`InMemoryDataset`**: Efficient in-memory dataset implementation
- **Built-in Datasets**: HotpotQA (300/500 samples) for multi-hop QA evaluation
- **Test Datasets**: Small datasets for quick testing and debugging

### 5. Evaluation Framework
High-performance evaluation system with concurrent processing.

- **`ExperimentResult`**: Aggregated test results with average score computation
- **`TestResult`**: Individual test case outcomes with detailed metric values
- **Concurrent Evaluation**: Thread pool execution for scalable evaluation
- **Failure Analysis**: Sorted results for detailed failure pattern analysis

## 🚀 Quickstart

### Installation
```bash
# From the parent project root
uv sync  # diting-optimizer is included in workspace dependencies
```

### Basic Prompt Optimization
```python
import asyncio
from diting_core.models.llms.factory import llm_factory
from diting_optimizer.algorithms.prompt.prompt_messages.hierarchical_reflective.optimizer import (
    HierarchicalReflectiveOptimizer,
)
from diting_optimizer.target.prompt_config import PromptConfig
from diting_optimizer.datasets.hotpot_qa import hotpot_300
from diting_optimizer.callbacks.history import HistoryCallbackHandler

async def optimize_prompt():
    # Configure LLM for generation
    generate_llm = llm_factory(
        model="qwen/qwen2.5-7b-instruct",
        base_url="https://api.example.com/v1",
        api_key="your-api-key"
    )

    # Define initial prompt configuration
    prompt_config = PromptConfig(
        messages=[
            {"role": "system", "content": "Provide an answer to the question"},
            {"role": "user", "content": "{user_input}"}
        ],
        llm=generate_llm
    )

    # Configure optimizer
    optimize_llm = llm_factory(
        model="gpt-4",
        base_url="https://api.openai.com/v1",
        api_key="your-openai-key"
    )

    optimizer = HierarchicalReflectiveOptimizer(
        llm=optimize_llm,
        num_eval_threads=20
    )

    # Run optimization
    result = await optimizer.optimize(
        prompt_config=prompt_config,
        dataset=hotpot_300(),
        metric=your_metric,  # Your evaluation metric (BaseMetric instance)
        n_samples=100,
        callbacks=[HistoryCallbackHandler()]
    )

    # Display results
    result.display()
    return result.best_config

# Run optimization
best_config = asyncio.run(optimize_prompt())
```

### Parameter Optimization Example
```python
from diting_optimizer.algorithms.prompt.model_parameters.tpe.optimizer import (
    ParameterOptimizer,
)
from diting_optimizer.algorithms.prompt.model_parameters.tpe.search_space import (
    ParameterSearchSpace,
    ParameterSpec,
    ParameterType,
)

async def optimize_parameters():
    # Configure parameter search space
    parameter_space = ParameterSearchSpace(
        parameters=[
            ParameterSpec(
                name="temperature",
                distribution=ParameterType.FLOAT,
                low=0.0, high=1.0
            ),
            ParameterSpec(
                name="max_tokens",
                distribution=ParameterType.INT,
                low=50, high=500
            ),
            ParameterSpec(
                name="top_p",
                distribution=ParameterType.FLOAT,
                low=0.1, high=1.0
            )
        ]
    )

    # Initialize parameter optimizer
    optimizer = ParameterOptimizer(
        num_eval_threads=20,
        max_iterations=50
    )

    # Run optimization
    result = await optimizer.optimize(
        prompt_config=your_prompt_config,
        dataset=your_dataset,
        metric=your_metric,
        parameter_space=parameter_space,
        n_samples=100,
        callbacks=[HistoryCallbackHandler()]
    )

    # Display optimization results
    result.display()
    print(f"Best parameters: {result.best_config.parameters}")
    print(f"Best score: {result.best_score}")

    return result

# Run parameter optimization
result = asyncio.run(optimize_parameters())
```

### Custom Metric Integration
```python
from diting_core.metrics.base_metric import BaseMetric, MetricValue
from diting_core.cases.llm_case import LLMCase

class CustomAccuracyMetric(BaseMetric):
    async def _compute(self, test_case: LLMCase, **kwargs) -> MetricValue:
        # Implement your custom metric logic
        score = self.calculate_accuracy(test_case)
        reason = f"Custom accuracy evaluation: {score:.2f}"

        return MetricValue(score=score, reason=reason)

    def calculate_accuracy(self, test_case: LLMCase) -> float:
        # Your accuracy calculation logic
        return 0.85  # Example score

# Use with optimizer
metric = CustomAccuracyMetric()
result = await optimizer.optimize(
    prompt_config=prompt_config,
    dataset=dataset,
    metric=metric,
    n_samples=50
)
```

## 📊 Monitoring and Callbacks

### History Tracking
```python
from diting_optimizer.callbacks.history import HistoryCallbackHandler

# Configure detailed history tracking
history_callback = HistoryCallbackHandler()

# Run optimization with monitoring
result = await optimizer.optimize(
    prompt_config=prompt_config,
    dataset=dataset,
    metric=metric,
    n_samples=100,
    callbacks=[history_callback]
)

# Access optimization history
for iteration in history_callback.history:
    print(f"Iteration {iteration.iteration}: score={iteration.score:.3f}")
```

### Token Usage Monitoring
The optimizer automatically tracks:
- **LLM Token Usage**: All optimization and evaluation API calls
- **Embedding Token Usage**: Embedding model API consumption
- **Cost Tracking**: Estimated API costs for different providers
- **Performance Metrics**: Latency and throughput statistics

## 🛠️ Development Guide

### Project Structure
```
diting-optimizer/
├── src/diting_optimizer/
│   ├── algorithms/                    # Optimization algorithms
│   │   └── prompt/                   # Prompt optimization strategies
│   │       ├── model_parameters/     # Parameter optimization (TPE)
│   │       └── prompt_messages/      # Content optimization
│   ├── callbacks/                    # Optimization callbacks
│   │   └── history.py               # History tracking
│   ├── datasets/                     # Dataset management
│   │   ├── base_dataset.py          # Abstract dataset interface
│   │   └── hotpot_qa.py             # HotpotQA dataset
│   ├── infra/                        # Infrastructure components
│   │   └── eval_task.py             # Evaluation framework
│   ├── target/                       # Optimization targets
│   │   ├── base_config.py           # Base configuration
│   │   └── prompt_config.py         # Prompt configuration
│   ├── base_optimizer.py            # Abstract optimizer
│   ├── optimization_result.py       # Result management
│   └── main.py                      # Usage examples
├── examples/                        # Additional examples
└── pyproject.toml                   # Package configuration
```

### Adding Custom Optimizers
```python
from diting_optimizer.base_optimizer import BaseOptimizer
from diting_optimizer.optimization_result import OptimizationResult

class CustomOptimizer(BaseOptimizer):
    async def _optimize(
        self,
        config: BaseConfig,
        dataset: BaseDataset,
        metric: BaseMetric,
        **kwargs
    ) -> OptimizationResult:
        # Implement your custom optimization algorithm
        best_config = await self.your_optimization_logic(
            config, dataset, metric
        )

        return OptimizationResult(
            best_config=best_config,
            best_score=best_score,
            optimization_history=history
        )
```

### Environment Requirements
- Python 3.11+
- Dependencies managed via `uv` (see `pyproject.toml`)
- Optuna >= 3.0.0 for TPE optimization
- Integration with `diting-core` evaluation framework

## 🔄 Integration with DiTing Ecosystem

- **Works with `diting-core`** to leverage evaluation metrics, LLM interfaces, and callback systems
- **Powers `diting-server`** by providing optimization capabilities that can be deployed as API services
- **Integrates with DiTing's callback framework** for comprehensive monitoring and logging
- **Seamlessly connects with DiTing's LLM factory system** for model management and configuration

## 📈 Key Features

- **Multi-Algorithm Support**: Both content and parameter optimization
- **Advanced Analysis**: Hierarchical failure analysis and parameter importance
- **Production Ready**: Comprehensive error handling, logging, and monitoring
- **High Performance**: Async-first design with concurrent evaluation
- **Extensible Architecture**: Clean interfaces for adding new optimizers
- **Rich Reporting**: Detailed optimization history and analysis tools

## 📄 License

Part of the DiTing project, licensed under the [MIT License](../LICENSE).

For more details, see the main [DiTing documentation](https://your-repo.com/org/diting) or contact the maintainers.

## 🔗 Related Packages

- **[diting-core](../diting-core/README.md)** - Core evaluation engine for LLM applications
- **[diting-server](../diting-server/README.md)** - High-performance web API server (when available)
- **[openspec/project.md](../../openspec/project.md)** - Project conventions and domain context