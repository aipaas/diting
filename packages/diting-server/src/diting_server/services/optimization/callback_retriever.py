#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过回调 URL 调用发起方的语义检索器实现"""
from __future__ import annotations

import asyncio
import uuid
from typing import Any, Dict, List, Optional

import httpx

from diting_core.optimization.target.semantic_retriever import SemanticRetriever
from diting_server.common.logging_config.config import get_logger

logger = get_logger(__name__)


class CallbackSemanticRetriever(SemanticRetriever):
    """通过回调 URL 调用发起方获取检索结果的语义检索器

    该检索器不直接执行检索，而是通过 HTTP 回调发起方的服务来获取检索结果。
    这样可以让发起方自己实现检索逻辑，优化服务只负责评估和寻找最优参数。
    """

    def __init__(self, callback_url: str, timeout: float = 30.0) -> None:
        """初始化回调检索器

        Args:
            callback_url: 发起方提供的回调 URL
            timeout: HTTP 请求超时时间（秒）
        """
        super().__init__()
        self.callback_url = callback_url.rstrip("/")
        self.timeout = timeout

    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """通过回调 URL 执行语义检索

        Args:
            query: 查询文本
            top_k: 返回结果数量
            **kwargs: 其他参数，如 similarity_threshold, context_recall_max_tokens, dataset_item 等

        Returns:
            检索结果列表，每个结果包含文档内容和相似度得分

        Raises:
            RuntimeError: 当回调失败时抛出
        """
        request_id = str(uuid.uuid4())

        # 从 kwargs 中提取 dataset_item（如果有）
        dataset_item = kwargs.pop("dataset_item", None)

        # 构造参数（移除 dataset_item，其他的都是检索参数）
        parameters = {
            k: v
            for k, v in kwargs.items()
            if k in ["similarity_threshold", "context_recall_max_tokens", "top_k"]
        }
        if top_k is not None:
            parameters["top_k"] = top_k

        # 构造回调请求 payload（匹配 remote_service.py 的格式）
        payload = {
            "request_id": request_id,
            "stage": "retrieval.semantic_search",
            "dataset_item": dataset_item or {},
            "parameters": parameters,
        }

        # 调用回调 URL（端点固定为 /api/v1/rag/retrieval）
        url = f"{self.callback_url}/api/v1/rag/retrieval"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                result = response.json()

            if result.get("status") != "ok":
                error_msg = result.get("error", "Unknown error")
                raise RuntimeError(f"Callback service returned error: {error_msg}")

            documents = result.get("documents", [])

            logger.info(
                "Callback retrieval successful",
                request_id=request_id,
                query=query,
                num_results=len(documents),
                parameters=parameters,
            )

            return documents

        except httpx.HTTPError as exc:
            logger.error(
                "Callback retrieval failed",
                request_id=request_id,
                callback_url=url,
                error=str(exc),
            )
            raise RuntimeError(f"Failed to call callback URL: {exc}") from exc
