"""Hierarchical Reflective Optimizer.

Uses hierarchical root cause analysis to improve prompts based on failure patterns.

Note: Current implementation uses mock LLM calls and evaluations.
Full functionality requires real LLM integration and evaluation framework support.
"""

from .optimizer import HierarchicalReflectiveOptimizer
from .root_cause_analyzer import HierarchicalRootCauseAnalyzer
from .types import (
    FailureMode,
    RootCauseAnalysis,
    BatchAnalysis,
    HierarchicalRootCauseAnalysis,
    PromptMessage,
    ImprovedPrompt,
)

__all__ = [
    "HierarchicalReflectiveOptimizer",
    "HierarchicalRootCauseAnalyzer",
    "FailureMode",
    "RootCauseAnalysis",
    "BatchAnalysis",
    "HierarchicalRootCauseAnalysis",
    "PromptMessage",
    "ImprovedPrompt",
]
