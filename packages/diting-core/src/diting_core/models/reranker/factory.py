#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, Any, Dict

from diting_core.models.reranker.base_model import BaseReranker
from diting_core.models.reranker.openai_model import PrivateReranker


def reranker_factory(
    model: str = "qwen3-reranker-06b",
    api_url: str = None,
    api_key: Optional[str] = None,
    timeout: float = 30.0,
    max_retries: int = 3,
    headers: Optional[Dict[str, str]] = None,
    **kwargs: Any,
) -> BaseReranker:
    """
    Parameters
    ----------
    model : str, optional
    api_url : str, required
    api_key : str, optional
    timeout : float, optional
    max_retries : int, optional
    headers : Dict[str, str], optional
    **kwargs: Any
    """
    if api_url is None:
        raise ValueError("api_url is required for reranker_factory")

    return PrivateReranker(
        model=model,
        api_url=api_url,
        api_key=api_key,
        timeout=timeout,
        max_retries=max_retries,
        headers=headers or {},
        **kwargs,
    )
