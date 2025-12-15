#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Any, List, Dict, Optional
import httpx

from pydantic import BaseModel, Field
from diting_core.models.reranker.base_model import BaseReranker
from diting_core.callbacks.manager import new_group
from diting_core.callbacks.base import ChainType


class PrivateReranker(BaseModel, BaseReranker):
    """
    基于私有 API 的重排序器实现。
    """

    model: str = Field(default="bge-reranker-v2-m3", description="重排序模型名称")
    api_url: str = Field(..., description="Reranker API 端点 URL")
    api_key: Optional[str] = Field(default=None, description="API 密钥")
    timeout: float = Field(default=30.0, description="请求超时时间（秒）")
    max_retries: int = Field(default=3, description="最大重试次数")
    headers: Dict[str, str] = Field(default_factory=dict, description="请求头")

    def __init__(self, **data):
        super().__init__(**data)
        # 设置默认请求头
        if not self.headers:
            self.headers = {"Content-Type": "application/json"}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    async def _call_rerank_api(
        self,
        query: str,
        documents: List[str],
        top_k: Optional[int] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """
        调用重排序 API 的内部方法。
        """
        # 构建请求数据
        request_data = {
            "model": self.model,
            "query": query,
            "documents": documents,
        }

        if top_k is not None:
            request_data["top_k"] = top_k

        # 添加其他参数
        request_data.update(kwargs)

        run_manager, grp_cb = await new_group(
            name=self.__repr__(),
            inputs={"query": query, "documents": documents},
            callbacks=kwargs.pop("callbacks", None),
            chain_type=ChainType.RERANK,
            verbose=kwargs.pop("verbose", False),
        )
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.api_url,
                    json=request_data,
                    headers=self.headers,
                )
                response.raise_for_status()

                # 解析响应
                result = response.json()
                rankings, usage = self._parse_api_response(result, documents)

                return rankings, usage

        except Exception as e:
            await run_manager.on_chain_error(e)
            raise e

    def _parse_api_response(
        self, response_data: Dict[str, Any], documents: List[str]
    ) -> List[Dict[str, Any]]:
        """
        解析 API 响应数据。
        {
            "model": "qwen3-reranker-06b",
            "results": [
                {
                    "index": 0,
                    "document": {
                        "text": "深信服超融合是一种集成了计算、存储、网络的新型IT基础架构。"
                    },
                    "relevance_score": 0.977022634773286
                }
            ],
            "usage": {
                "total_tokens": 4
            }
        }

        支持多种常见的 reranker API 响应格式：
        1. {"results": [{"index": 0, "score": 0.95, "document": "..."}, ...]}
        2. [{"index": 0, "score": 0.95, "document": "..."}, ...]
        3. {"rankings": [{"index": 0, "score": 0.95, "document": "..."}, ...]}
        """
        try:
            if "usage" in response_data:
                usage = response_data["usage"]
            else:
                usage = {"total_tokens": 0}

            # 尝试不同的响应格式
            rankings = None
            if "results" in response_data:
                rankings = response_data["results"]
            elif "rankings" in response_data:
                rankings = response_data["rankings"]
            elif isinstance(response_data, list):
                rankings = response_data
            else:
                # 如果格式不匹配，返回默认排序
                return self._create_default_response(documents)

            # 验证和补充缺失的字段
            processed_rankings = []
            for i, ranking in enumerate(rankings):
                if not isinstance(ranking, dict):
                    continue

                processed_ranking = {
                    "index": ranking.get("index", i),
                    "score": ranking.get("score", 1.0 - (i * 0.1)),
                    "document": ranking.get(
                        "document", documents[ranking.get("index", i)]
                    ),
                }

                # 添加可选字段
                if "relevance_score" in ranking:
                    processed_ranking["relevance_score"] = ranking["relevance_score"]

                processed_rankings.append(processed_ranking)

            if processed_rankings:
                return processed_rankings, usage
            else:
                return self._create_default_response(documents)

        except Exception:
            # 出现任何错误时返回默认排序
            return self._create_default_response(documents)

    def _create_default_response(self, documents: List[str]) -> List[Dict[str, Any]]:
        """
        创建默认排序结果。
        """
        return [
            {
                "index": i,
                "document": doc,
                "score": 1.0 - (i * 0.1),
                "relevance_score": 1.0 - (i * 0.1),
            }
            for i, doc in enumerate(documents)
        ], {"total_tokens": 0}

    async def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: Optional[int] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """
        对文档列表进行重排序。
        """
        if not isinstance(query, str):
            raise TypeError(f"query must be str, got {type(query)}")
        if not isinstance(documents, list):
            raise TypeError(f"documents must be a list, got {type(documents)}")

        if not documents:
            return []

        run_manager, _ = await new_group(
            name=self.__repr__(),
            inputs={"query": query, "documents": documents},
            callbacks=kwargs.pop("callbacks", None),
            chain_type=ChainType.RERANK,
        )
        # 执行重排序
        rankings, usage = await self._call_rerank_api(
            query, documents, top_k=top_k, **kwargs
        )

        result = []
        for ranking in rankings:
            result_item = {
                "index": ranking["index"],
                "document": ranking["document"],
                "score": ranking["score"],
            }
            result.append(result_item)

        await run_manager.on_chain_end(
            outputs={"rankings": rankings, "usage": usage},
            inputs={"query": query, "documents": documents},
            chain_type=ChainType.RERANK,
        )
        return result

    async def rerank_with_scores(
        self,
        query: str,
        documents: List[str],
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """
        对文档列表进行重排序并返回详细分数信息。
        """
        if not isinstance(query, str):
            raise TypeError(f"query must be str, got {type(query)}")
        if not isinstance(documents, list):
            raise TypeError(f"documents must be a list, got {type(documents)}")

        if not documents:
            return []

        run_manager, _ = await new_group(
            name=self.__repr__(),
            inputs={"query": query, "documents": documents},
            callbacks=kwargs.pop("callbacks", None),
            chain_type=ChainType.RERANK,
        )
        # 执行重排序
        rankings, usage = await self._call_rerank_api(query, documents, **kwargs)

        # 确保所有必需字段都存在
        result = []
        for i, ranking in enumerate(rankings):
            result_item = {
                "index": ranking["index"],
                "document": ranking["document"],
                "score": ranking["score"],
                "relevance_score": ranking.get("relevance_score", ranking["score"]),
                "rank": i + 1,
            }
            result.append(result_item)

        await run_manager.on_chain_end(
            outputs={"rankings": rankings, "usage": usage},
            inputs={"query": query, "documents": documents},
            chain_type=ChainType.RERANK,
        )
        return result

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model}, api_url={self.api_url})"
