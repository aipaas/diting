#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
import typing as t


class BaseReranker(ABC):
    @abstractmethod
    async def rerank(
        self,
        query: str,
        documents: t.List[str],
        top_k: t.Optional[int] = None,
        **kwargs: t.Any,
    ) -> t.List[t.Dict[str, t.Any]]:
        """
        对文档列表进行重排序。

        Args:
            query: 查询字符串
            documents: 待排序的文档列表
            top_k: 返回前 k 个结果的数目，如果为 None 则返回所有结果
            **kwargs: 其他参数

        Returns:
            包含重排序结果的字典列表，每个字典包含以下字段：
            - index: 原始文档在输入列表中的索引
            - document: 文档内容
            - score: 重排序分数
            - relevance_score: 相关性分数（可选）
        """
        ...

    @abstractmethod
    async def rerank_with_scores(
        self,
        query: str,
        documents: t.List[str],
        **kwargs: t.Any,
    ) -> t.List[t.Dict[str, t.Any]]:
        """
        对文档列表进行重排序并返回详细分数信息。

        Args:
            query: 查询字符串
            documents: 待排序的文档列表
            **kwargs: 其他参数

        Returns:
            包含详细分数信息的字典列表，每个字典包含以下字段：
            - index: 原始文档在输入列表中的索引
            - document: 文档内容
            - score: 重排序分数
            - relevance_score: 相关性分数
            - rank: 重排序后的排名
        """
        ...

    async def rerank_single(
        self,
        query: str,
        document: str,
        **kwargs: t.Any,
    ) -> t.Dict[str, t.Any]:
        """
        对单个文档进行重排序评分。

        Args:
            query: 查询字符串
            document: 待评分的文档
            **kwargs: 其他参数

        Returns:
            包含评分信息的字典
        """
        result = await self.rerank(query, [document], **kwargs)
        return result[0] if result else {"index": 0, "document": document, "score": 0.0}