# 优化器测试框架使用说明

## 概述

本框架提供了一个统一的测试环境，用于对比不同优化器在不同数据集和评估指标下的表现。

## 特性

- **统一配置管理**：通过YAML/JSON文件配置所有参数
- **灵活的执行模式**：支持串行、并发、批量执行
- **动态加载**：支持动态加载数据集、评估指标和优化器
- **自动化报告**：生成Markdown、JSON、HTML格式的测试报告
- **进度跟踪**：实时显示测试进度和统计信息

## 快速开始

### 1. 使用示例配置

```bash
# 进入examples目录
cd packages/diting-optimizer/src/examples

# 运行所有测试任务（串行）
python run_optimizer_test.py --config configs/example_test_config.yaml

# 并发运行
python run_optimizer_test.py --config configs/example_test_config.yaml --mode parallel --workers 2

# 只运行特定任务
python run_optimizer_test.py --config configs/example_test_config.yaml --tasks fund_manager_accuracy_test hotpot_accuracy_test

# 调整样本数
python run_optimizer_test.py --config configs/example_test_config.yaml --samples 5
```

### 2. 创建自定义配置

复制示例配置文件并修改：

```yaml
name: "我的测试"
description: "测试描述"

# LLM配置
generate_llm:
  model: "your-model"
  base_url: "your-base-url"
  api_key: "your-api-key"

# 测试任务
tasks:
  - name: "my_task"
    dataset:
      name: "my_dataset"
      module_path: "path.to.dataset.module"
      function_name: "load_dataset"
    metric:
      name: "my_metric"
      module_path: "path.to.metric.module"
      class_name: "MyMetric"
    optimizer:
      name: "my_optimizer"
      module_path: "path.to.optimizer.module"
      class_name: "MyOptimizer"
    prompt_template: "Your prompt template"
    n_samples: 10

# 执行配置
execution:
  execution_mode: "sequential"
  max_workers: 4
  save_reports: true
  report_dir: "reports"
  report_format: "markdown"
```

## 配置说明

### LLM配置

- `generate_llm`: 用于生成回答的模型
- `eval_llm`: 用于评估的模型
- `optimize_llm`: 用于优化的模型
- `embedding`: 用于Embedding的模型（某些评估指标需要）

### 任务配置

每个任务包含：

- `dataset`: 数据集配置
  - `module_path`: Python模块路径
  - `function_name`: 加载数据集的函数名
- `metric`: 评估指标配置
  - `module_path`: Python模块路径
  - `class_name`: 评估指标类名
  - `params`: 传递给评估指标的参数
- `optimizer`: 优化器配置
  - `module_path`: Python模块路径
  - `class_name`: 优化器类名
  - `params`: 传递给优化器的参数
- `prompt_template`: 提示词模板
- `n_samples`: 测试样本数

### 执行模式

- `sequential`: 串行执行（默认）
- `parallel`: 并发执行
- `batch`: 批量执行（分批并发）

## 报告

测试完成后，报告将保存在 `reports` 目录下：

- `{test_name}_report_{timestamp}.md`: Markdown格式的汇总报告
- `{test_name}_report_{timestamp}.json`: JSON格式的详细数据
- `task_reports/{timestamp}/`: 每个任务的详细优化报告

## 示例输出

```
开始执行优化器测试
测试名称: 优化器对比测试示例
任务数量: 3
执行模式: sequential

==================================================
开始执行任务: fund_manager_accuracy_test
数据集: fund_manager_qa_10
评估指标: AccuracyAndConciseMetric
优化器: HierarchicalReflectiveOptimizer
==================================================

任务完成: fund_manager_accuracy_test
最佳分数: 0.8500
迭代次数: 5
耗时: 45.23秒

==================================================

测试结果汇总
============================================================

任务: fund_manager_accuracy_test
  数据集: fund_manager_qa_10
  评估指标: AccuracyAndConciseMetric
  最佳分数: 0.8500
  迭代次数: 5
  耗时: 45.23秒

总体统计:
  平均分数: 0.8350
  总耗时: 156.78秒
  完成任务数: 3

[报告] Markdown报告已生成: reports/优化器对比测试示例_report_20250111_143052.md
[报告] 任务详细报告已生成: reports/task_reports/20250111_143052/fund_manager_accuracy_test_20250111_143052.md
```

## 注意事项

1. 确保所有依赖的模块已正确安装
2. API密钥等敏感信息建议通过环境变量管理
3. 并发执行时注意API的速率限制
4. 大数据集测试时建议调整 `n_samples` 参数