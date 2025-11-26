"""Integrations with external systems and libraries."""

from . import core_adapter

# Re-export commonly used functions and classes from diting-core adapter
# This provides convenient import paths like:
#   from diting_web.integrations import create_llm_from_config
# instead of:
#   from diting_web.integrations.core_adapter import create_llm_from_config
from .core_adapter import (
    create_llm_from_config,
    create_embedding_from_config,
    get_default_llm_config,
    get_default_embedding_config,
    EvaluationRunner,
    SynthesisRunner,
)

__all__ = [
    "core_adapter",  # Keep submodule available for explicit imports
    "create_llm_from_config",
    "create_embedding_from_config",
    "get_default_llm_config",
    "get_default_embedding_config",
    "EvaluationRunner",
    "SynthesisRunner",
]

