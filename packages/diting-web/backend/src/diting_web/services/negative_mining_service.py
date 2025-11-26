"""
负样本挖掘服务

这是 diting-web 层的服务封装，调用 core 中的核心负样本挖掘功能。
"""

from typing import List, Optional, Union

from diting_core.models.embeddings.base_model import BaseEmbeddings
from diting_web.core.negative_mining import mine_negatives as core_mine_negatives
from diting_web.common.logging import get_logger

logger = get_logger(__name__)


class NegativeMiningService:
    """负样本挖掘服务（Web 层封装）"""

    @staticmethod
    async def mine_negatives(
        embedding_model: BaseEmbeddings,
        train_data: List[dict],
        candidate_pool: Optional[List[str]] = None,
        sample_range: Union[str, List[int]] = "10-210",
        negative_number: int = 15,
        use_gpu: bool = False,
        embedding_batch_size: int = 32,
    ) -> List[dict]:
        """
        基于 KNN（近邻检索）进行"困难负样本"挖掘。

        这是对 core 中核心功能的封装，添加了日志记录。

        参数：
        - embedding_model: BaseEmbeddings 实例，用于向量化
        - train_data: 训练数据列表
        - candidate_pool: 可选的外部候选语料池
        - sample_range: 负样本采样区间，如 "10-210" 或 [10, 210]
        - negative_number: 每条样本挖掘的负样本数量
        - use_gpu: 是否使用 GPU 进行 FAISS 检索
        - embedding_batch_size: embedding 编码时的批处理大小

        返回：
        - 增强后的训练数据列表，每条样本包含挖掘的负样本
        """
        logger.info(
            "Starting negative mining",
            train_data_size=len(train_data),
            candidate_pool_size=len(candidate_pool) if candidate_pool else 0,
            sample_range=sample_range,
            negative_number=negative_number,
        )

        # 调用 core 中的核心功能
        enhanced_data = await core_mine_negatives(
            embedding_model=embedding_model,
            train_data=train_data,
            candidate_pool=candidate_pool,
            sample_range=sample_range,
            negative_number=negative_number,
            use_gpu=use_gpu,
            embedding_batch_size=embedding_batch_size,
        )

        logger.info(
            "Negative mining completed",
            enhanced_samples=len(enhanced_data),
        )

        return enhanced_data
