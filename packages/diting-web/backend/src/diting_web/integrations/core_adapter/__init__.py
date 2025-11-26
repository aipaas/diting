"""DiTing Core integration module.

This module provides wrappers and utilities to integrate diting-core
evaluation and synthesis capabilities into the web backend.
"""

from .config_mapper import (
    create_llm_from_config,
    create_embedding_from_config,
    get_default_llm_config,
    get_default_embedding_config,
)
from .evaluation_runner import EvaluationRunner
from .synthesis_runner import SynthesisRunner

__all__ = [
    "create_llm_from_config",
    "create_embedding_from_config",
    "get_default_llm_config",
    "get_default_embedding_config",
    "EvaluationRunner",
    "SynthesisRunner",
]

