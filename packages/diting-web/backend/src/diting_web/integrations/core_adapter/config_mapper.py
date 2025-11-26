"""Configuration mapping between web backend and diting-core.

Maps configuration dictionaries from the web API to diting-core model instances.
"""

from typing import Any, Optional

from diting_core.models.embeddings.base_model import BaseEmbeddings
from diting_core.models.embeddings.factory import embedding_factory
from diting_core.models.llms.base_model import BaseLLM
from diting_core.models.llms.factory import llm_factory

from diting_web.common.logging import get_logger

logger = get_logger(__name__)


def create_llm_from_config(llm_config: dict[str, Any]) -> BaseLLM:
    """Create a BaseLLM instance from configuration dictionary.
    
    Args:
        llm_config: LLM configuration dictionary with fields:
            - model_name (str): Model name (e.g., "gpt-4", "gpt-3.5-turbo")
            - base_url (str, optional): API base URL
            - api_key (str, optional): API key
            - timeout (float, optional): Request timeout in seconds
            - temperature (float, optional): Temperature for generation
            - max_tokens (int, optional): Maximum tokens to generate
            - **kwargs: Additional model-specific parameters
    
    Returns:
        BaseLLM: Configured LLM instance
    
    Examples:
        >>> config = {
        ...     "model_name": "gpt-4",
        ...     "temperature": 0.7,
        ...     "api_key": "sk-..."
        ... }
        >>> llm = create_llm_from_config(config)
    """
    model_name = llm_config.get("model_name", "gpt-4o-mini")
    base_url = llm_config.get("base_url")
    api_key = llm_config.get("api_key")
    timeout = llm_config.get("timeout", 60.0)
    
    # Extract additional parameters
    temperature = llm_config.get("temperature")
    max_tokens = llm_config.get("max_tokens")
    
    # Build kwargs for factory
    kwargs: dict[str, Any] = {}
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    
    # Pass through any other parameters
    for key in ["top_p", "frequency_penalty", "presence_penalty", "stop"]:
        if key in llm_config:
            kwargs[key] = llm_config[key]
    
    logger.info(
        "Creating LLM from config",
        model=model_name,
        base_url=base_url,
        has_api_key=bool(api_key),
        timeout=timeout,
        extra_params=list(kwargs.keys()),
    )
    
    try:
        llm = llm_factory(
            model=model_name,
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            **kwargs,
        )
        logger.info("LLM created successfully", model=model_name)
        return llm
    except Exception as e:
        logger.error("Failed to create LLM", model=model_name, error=str(e), exc_info=True)
        raise


def create_embedding_from_config(embedding_config: dict[str, Any]) -> BaseEmbeddings:
    """Create a BaseEmbeddings instance from configuration dictionary.
    
    Args:
        embedding_config: Embedding configuration dictionary with fields:
            - model_name (str): Model name (e.g., "text-embedding-ada-002", "bge-m3")
            - base_url (str, optional): API base URL
            - api_key (str, optional): API key
            - timeout (float, optional): Request timeout in seconds
    
    Returns:
        BaseEmbeddings: Configured embedding instance
    
    Examples:
        >>> config = {
        ...     "model_name": "text-embedding-ada-002",
        ...     "api_key": "sk-..."
        ... }
        >>> embedding = create_embedding_from_config(config)
    """
    model_name = embedding_config.get("model_name", "bge-m3")
    base_url = embedding_config.get("base_url")
    api_key = embedding_config.get("api_key")
    timeout = embedding_config.get("timeout", 60.0)
    
    logger.info(
        "Creating embedding from config",
        model=model_name,
        base_url=base_url,
        has_api_key=bool(api_key),
        timeout=timeout,
    )
    
    try:
        embedding = embedding_factory(
            model=model_name,
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
        )
        logger.info("Embedding created successfully", model=model_name)
        return embedding
    except Exception as e:
        logger.error("Failed to create embedding", model=model_name, error=str(e), exc_info=True)
        raise


def get_default_llm_config() -> dict[str, Any]:
    """Get default LLM configuration from settings.
    
    Returns:
        dict: Default LLM configuration
    """
    from diting_web.config.settings import get_settings
    
    settings = get_settings()
    
    # Get from environment variables or use defaults
    return {
        "model_name": settings.default_llm_model if hasattr(settings, "default_llm_model") else "gpt-4o-mini",
        "base_url": settings.llm_base_url if hasattr(settings, "llm_base_url") else None,
        "api_key": settings.llm_api_key if hasattr(settings, "llm_api_key") else None,
        "timeout": settings.llm_timeout if hasattr(settings, "llm_timeout") else 60.0,
    }


def get_default_embedding_config() -> dict[str, Any]:
    """Get default embedding configuration from settings.
    
    Returns:
        dict: Default embedding configuration
    """
    from diting_web.config.settings import get_settings
    
    settings = get_settings()
    
    return {
        "model_name": settings.default_embedding_model if hasattr(settings, "default_embedding_model") else "bge-m3",
        "base_url": settings.embedding_base_url if hasattr(settings, "embedding_base_url") else None,
        "api_key": settings.embedding_api_key if hasattr(settings, "embedding_api_key") else None,
        "timeout": settings.embedding_timeout if hasattr(settings, "embedding_timeout") else 60.0,
    }

