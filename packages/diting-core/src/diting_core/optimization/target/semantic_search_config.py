"""语义搜索配置类

用于优化语义搜索节点的相关度阈值配置。
"""

from typing import Dict, List, Optional, Any
from pydantic import Field

from diting_core.optimization.target.base_config import BaseConfig
from diting_core.optimization.target.semantic_retriever import SemanticRetriever


class SemanticSearchConfig(BaseConfig):
    """语义搜索配置类

    用于优化语义搜索器的相关度阈值参数。

    Attributes:
        similarity_threshold: 相似度阈值 (0.0 ~ 1.0)，低于此值的结果将被过滤
        context_recall_max_tokens: 上下文召回可用token数，用于控制召回内容的总长度
        semantic_retriever: 语义检索器实例
    """

    similarity_threshold: float = Field(
        default=0.7,
        description="相似度阈值，范围 0.0 ~ 1.0，低于此值的结果将被过滤",
        ge=0.0,
        le=1.0
    )
    context_recall_max_tokens: int = Field(
        default=3000,
        description="上下文召回可用token数，用于控制召回内容的总长度",
        ge=100,
        le=80000
    )
    semantic_retriever: Optional[SemanticRetriever] = Field(
        default=None,
        description="语义检索器实例"
    )

    def validate_dependencies(self) -> None:
        """验证依赖是否已注入"""
        if not self.semantic_retriever:
            raise ValueError("SemanticRetriever not configured. Set semantic_retriever first.")

        # 验证检索器是否支持必要方法
        if not hasattr(self.semantic_retriever, 'retrieve'):
            raise ValueError("SemanticRetriever must support retrieve method")

    async def execute(self, dataset_item: Optional[Dict[str, str]] = None, **kwargs) -> List[Dict[str, Any]]:
        """执行语义搜索

        Args:
            dataset_item: 数据集项，包含 user_input 等字段
            **kwargs: 额外参数传递给检索器

        Returns:
            过滤后的检索结果列表，每个结果包含文档内容和相似度得分

        Raises:
            ValueError: 当检索器未配置或缺少必要参数时
        """
        self.validate_dependencies()

        # 获取查询文本
        query = ""
        if dataset_item and "user_input" in dataset_item:
            query = dataset_item["user_input"]
        elif "query" in kwargs:
            query = kwargs.pop("query")
        else:
            raise ValueError("No query provided in dataset_item or kwargs")

        # 传递参数给检索器
        # 注意：将 dataset_item 传递给检索器，让回调检索器可以使用它
        retrieve_kwargs = {
            "similarity_threshold": self.similarity_threshold,
            "context_recall_max_tokens": self.context_recall_max_tokens,
            "dataset_item": dataset_item,
            **kwargs,
        }

        # 执行检索（如果是 CallbackSemanticRetriever，它会调用回调 URL）
        results = await self.semantic_retriever.retrieve(query, **retrieve_kwargs)

        # 结果已经由检索器处理（如 CallbackSemanticRetriever 调用远程服务）
        # 远程服务会根据参数进行过滤，所以这里不再需要本地过滤
        # 但为了兼容本地检索器，仍然保留过滤逻辑

        # 根据相似度阈值过滤结果（如果远程服务未过滤）
        filtered_results = [
            result for result in results
            if result.get('similarity', 0.0) >= self.similarity_threshold
        ]

        # 如果设置了context_recall_max_tokens，则进一步处理结果
        if self.context_recall_max_tokens and filtered_results:
            # 按相似度排序
            filtered_results.sort(key=lambda x: x.get('similarity', 0.0), reverse=True)

            # 根据token数量限制结果
            total_tokens = 0
            final_results = []

            for result in filtered_results:
                # 简单估算token数量（假设1个token约等于1.5个字符）
                # 或使用结果中的 token_count 字段（如果有）
                content = result.get('content', '')
                estimated_tokens = result.get('token_count', len(content) // 1.5)

                if total_tokens + estimated_tokens <= self.context_recall_max_tokens:
                    final_results.append(result)
                    total_tokens += estimated_tokens
                else:
                    # 如果添加当前结果会超过限制，则停止添加
                    break

            filtered_results = final_results

        return filtered_results

    def get_threshold_config(self) -> Dict[str, Any]:
        """获取阈值配置

        Returns:
            阈值配置字典
        """
        return {
            "similarity_threshold": self.similarity_threshold,
            "context_recall_max_tokens": self.context_recall_max_tokens
        }

    def set_threshold(self, similarity_threshold: float) -> None:
        """设置相似度阈值

        Args:
            similarity_threshold: 相似度阈值 (0.0 ~ 1.0)
        """
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError("similarity_threshold 必须在 0.0 到 1.0 之间")
        self.similarity_threshold = similarity_threshold

    def set_context_recall_max_tokens(self, max_tokens: int) -> None:
        """设置上下文召回可用token数

        Args:
            max_tokens: 最大token数 (100 ~ 8000)
        """
        if not 100 <= max_tokens <= 8000:
            raise ValueError("context_recall_max_tokens 必须在 100 到 8000 之间")
        self.context_recall_max_tokens = max_tokens

    def describe(self) -> Dict[str, Any]:
        """返回配置描述

        Returns:
            配置信息字典
        """
        threshold_config = self.get_threshold_config()

        return {
            "config_type": "semantic_search",
            "thresholds": threshold_config,
            "has_retriever": self.semantic_retriever is not None
        }

    @classmethod
    def create_default(cls, semantic_retriever: SemanticRetriever) -> "SemanticSearchConfig":
        """创建默认配置

        Args:
            semantic_retriever: 语义检索器实例

        Returns:
            默认配置实例
        """
        return cls(
            similarity_threshold=0.4,  # 基线阈值设为0.5
            context_recall_max_tokens=5000,  # 默认2000个token
            semantic_retriever=semantic_retriever
        )

    @classmethod
    def create_with_threshold(
        cls, 
        semantic_retriever: SemanticRetriever, 
        similarity_threshold: float = 0.5,
        context_recall_max_tokens: int = 2000
    ) -> "SemanticSearchConfig":
        """创建带有指定阈值的配置

        Args:
            semantic_retriever: 语义检索器实例
            similarity_threshold: 相似度阈值
            context_recall_max_tokens: 上下文召回可用token数

        Returns:
            配置实例
        """
        return cls(
            similarity_threshold=similarity_threshold,
            context_recall_max_tokens=context_recall_max_tokens,
            semantic_retriever=semantic_retriever
        )