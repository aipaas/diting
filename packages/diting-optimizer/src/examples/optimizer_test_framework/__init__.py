"""
优化器测试框架

一个用于测试和比较不同优化器效果的通用框架。
支持：
- 多种数据集和评估指标
- 并发或串行执行模式
- 统一的配置管理
- 自动化报告生成
"""

from .config import (
    OptimizerTestConfig,
    TestTaskConfig,
    LLMConfig,
    EmbeddingConfig,
    DatasetConfig,
    MetricConfig,
    OptimizerConfig,
    ExecutionConfig,
)

from .optimizer_test_framework import (
    OptimizerTestFramework,
)

from .executor import ExecutionMode, TaskExecutor

from .report import ReportGenerator

__all__ = [
    # 配置类
    "OptimizerTestConfig",
    "TestTaskConfig",
    "LLMConfig",
    "EmbeddingConfig",
    "DatasetConfig",
    "MetricConfig",
    "OptimizerConfig",
    "ExecutionConfig",
    # 框架主类
    "OptimizerTestFramework",
    "run_optimizer_test",
    # 执行器
    "ExecutionMode",
    "TaskExecutor",
    # 报告生成器
    "ReportGenerator",
]
