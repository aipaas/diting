"""优化目标配置

存放各类优化目标的配置类（提示词、参数、工具等）。
"""

from diting_core.optimization.target.prompt_config import PromptConfig
from diting_core.optimization.target.semantic_search_config import SemanticSearchConfig
from diting_core.optimization.target.semantic_retriever import SemanticRetriever, BaseSemanticRetriever

__all__ = [
    "PromptConfig",
    "SemanticSearchConfig",
    "SemanticRetriever",
    "BaseSemanticRetriever"
]