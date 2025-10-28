"""语义检索器类

为 diting 项目实现的语义检索器，与项目技术栈保持一致。
"""

from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass

from diting_core.models.embeddings.base_model import BaseEmbeddings


@dataclass
class SearchResult:
    """搜索结果数据类"""
    content: str
    id: str
    similarity: float


class SemanticRetriever(ABC):
    """语义检索器基类

    为 diting 项目实现的语义检索器，与项目技术栈保持一致。
    """

    def __init__(self):
        """初始化语义检索器"""
        pass

    @abstractmethod
    async def retrieve(
        self, query: str, top_k: Optional[int] = None, **kwargs
    ) -> List[Dict[str, Any]]:
        """执行语义检索

        Args:
            query: 查询文本
            top_k: 返回结果数量，如果为 None 则返回所有结果
            **kwargs: 其他参数

        Returns:
            检索结果列表，每个结果包含文档内容和相似度得分
        """
        pass


class BaseSemanticRetriever(SemanticRetriever):
    """基础语义检索器实现"""

    def __init__(
        self,
        embeddings: BaseEmbeddings,
        documents: Optional[List[Dict[str, Any]]] = None
    ):
        """初始化基础语义检索器

        Args:
            embeddings: 嵌入模型实例
            documents: 文档集合，格式为 [{"id": str, "content": str}, ...]
        """
        super().__init__()
        self.embeddings = embeddings
        self.documents = documents or []
        self.document_embeddings = []

    async def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """添加文档到检索器

        Args:
            documents: 文档列表，格式为 [{"id": str, "content": str}, ...]
        """
        self.documents.extend(documents)
        # 为新添加的文档生成嵌入
        contents = [doc["content"] for doc in documents]
        embeddings = await self.embeddings.aembed_documents(contents)
        self.document_embeddings.extend(embeddings)

    async def retrieve(
        self, query: str, top_k: Optional[int] = None, **kwargs
    ) -> List[Dict[str, Any]]:
        """执行语义检索

        Args:
            query: 查询文本
            top_k: 返回结果数量，如果为 None 则返回所有结果
            **kwargs: 其他参数，如 similarity_threshold（相似度阈值）

        Returns:
            检索结果列表，每个结果包含文档内容和相似度得分
        """
        if not self.documents or not self.document_embeddings:
            return []

        # 生成查询嵌入
        query_embedding = await self.embeddings.aembed_query(query)
        
        # 计算相似度
        similarities = []
        for doc_embedding in self.document_embeddings:
            similarity = self._cosine_similarity(query_embedding, doc_embedding)
            similarities.append(similarity)
        
        # 根据参数选择结果
        if top_k is not None:
            # 获取top_k个最相似的结果
            top_indices = sorted(
                range(len(similarities)), 
                key=lambda i: similarities[i], 
                reverse=True
            )[:top_k]
        else:
            # 检查是否有相似度阈值参数
            similarity_threshold = kwargs.get('similarity_threshold', None)
            if similarity_threshold is not None:
                # 返回高于阈值的所有结果
                top_indices = [i for i, sim in enumerate(similarities) if sim >= similarity_threshold]
            else:
                # 默认返回所有结果
                top_indices = list(range(len(similarities)))
        
        # 构造结果
        results = []
        for i in top_indices:
            results.append({
                "content": self.documents[i]["content"],
                "id": self.documents[i]["id"],
                "similarity": similarities[i]
            })
        
        # 如果是基于top_k或者阈值筛选的结果，按相似度排序
        if top_k is not None or 'similarity_threshold' in kwargs:
            results.sort(key=lambda x: x["similarity"], reverse=True)
        
        return results

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """计算余弦相似度

        Args:
            a: 向量a
            b: 向量b

        Returns:
            余弦相似度值
        """
        dot_product = sum(x * y for x, y in zip(a, b))
        magnitude_a = sum(x * x for x in a) ** 0.5
        magnitude_b = sum(x * x for x in b) ** 0.5
        
        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0
            
        return dot_product / (magnitude_a * magnitude_b)