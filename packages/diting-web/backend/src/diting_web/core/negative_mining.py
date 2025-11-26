"""
负样本挖掘核心模块

提供基于 FAISS 向量检索的困难负样本挖掘功能。

核心功能：
1. 使用 FAISS 构建向量检索索引（内积相似度）
2. 批量进行 KNN 检索
3. 基于区间采样和过滤的负样本挖掘
"""

import random
from typing import List, Optional, Union

try:
    import numpy as np
except ImportError:
    raise ImportError(
        "This module requires 'numpy'. Install it with: pip install numpy"
    )

try:
    import faiss
except ImportError:
    raise ImportError(
        "This module requires 'faiss-cpu'."
        "Install it with: pip install faiss-cpu"
    )

from diting_core.models.embeddings.base_model import BaseEmbeddings


def create_index(embeddings: np.ndarray, use_gpu: bool = False) -> faiss.Index:
    """
    用内积相似度（Inner Product, IP）构建 FAISS 向量检索索引。

    关键点：
    - 这里使用的是 `IndexFlatIP`，意味着相似度度量是"内积"，适合与归一化后的向量配合，
      等价于余弦相似度排序（当向量 L2 归一化时，内积大小等价于余弦相似度大小）。
    - `use_gpu=True` 时，会把 CPU 索引克隆到所有 GPU 上做并行检索；`co.useFloat16=True` 提升速度、降低显存占用。
    - `index.add(embeddings)` 会把所有待检索向量（语料向量）加入索引。

    参数：
    - embeddings: shape=[N, D] 的向量矩阵，N 为语料条数，D 为向量维度。
    - use_gpu: 是否启用 GPU 检索。

    返回：
    - FAISS 索引对象
    """
    index = faiss.IndexFlatIP(len(embeddings[0]))
    embeddings = np.asarray(embeddings, dtype=np.float32)

    if use_gpu:
        co = faiss.GpuMultipleClonerOptions()
        co.shard = True  # 多卡分片（shard），每张卡持有一部分向量，提升可检索规模
        co.useFloat16 = True  # FP16 存储/计算，加速同时节省显存
        index = faiss.index_cpu_to_all_gpus(index, co=co)

    index.add(embeddings)
    return index


def batch_search(
    index: faiss.Index,
    query: np.ndarray,
    topk: int = 200,
    batch_size: int = 64,
) -> tuple[List[List[float]], List[List[int]]]:
    """
    对查询向量进行批量 KNN 检索，返回每个查询的 topk 结果的分数与下标。

    关键点：
    - 为了避免一次性把所有查询喂给 FAISS 导致内存/显存峰值过高，这里按 `batch_size` 分批检索。
    - `index.search(batch_query, k=topk)` 返回：scores（相似度）和 inxs（对应语料向量的索引）。
    - 这里的下标 inxs 对应的是"去重后的 corpus 列表"的位置（见 find_knn_neg 中对 corpus 的 set 去重）。

    参数：
    - index: FAISS 索引
    - query: 查询向量矩阵，shape=[Q, D]
    - topk: 每条查询检索多少候选（需要 >= 负样本采样上界，例如 10-210 的上界 210）
    - batch_size: 分批大小

    返回：
    - (all_scores, all_inxs): 分数列表和索引列表
    """
    all_scores: List[List[float]] = []
    all_inxs: List[List[int]] = []

    for start_index in range(0, len(query), batch_size):
        batch_query = query[start_index : start_index + batch_size]
        batch_scores, batch_inxs = index.search(
            np.asarray(batch_query, dtype=np.float32), k=topk
        )
        all_scores.extend(batch_scores.tolist())
        all_inxs.extend(batch_inxs.tolist())

    return all_scores, all_inxs


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

    输入训练数据：每项形如
    {
      "query": "...",
      "pos": ["正例1", "正例2", ...],
      "neg": ["可选-已有负例1", ...]  # 可无
    }

    整体流程：
    1) 读入训练数据，构建用于检索的 `corpus` 和 `queries`。
       - corpus 初始包含所有正例 `pos`（以及已有的 neg，如果存在）；
       - 若提供 `candidate_pool`（一个列表，每项为文本），则以其为检索语料池；
       - 最终对 `corpus` 做去重：`list(set(corpus))`。

    2) 用嵌入模型对 `corpus` 和 `queries` 编码为向量：`p_vecs` 与 `q_vecs`。
       - 使用异步方法 `aembed_documents`。

    3) 基于 `p_vecs` 构建 FAISS IP 索引，用 `q_vecs` 进行 KNN 检索。
       - 检索时的 topk = `sample_range` 的上界值（例如 210）。
       - 得到每条 query 对应的候选下标列表 `all_inxs[i]`（按照相似度从高到低）。

    4) 负样本区间裁剪与过滤：
       - 设 `sample_range=[L, R]`（如 [10, 210]），取 `inxs[L:R]` 作为"候选负样本区间"。
         这样可以避开最相近的 top-L（通常可能包含语义非常接近、甚至真实正例的文本）。
       - 对该区间内的下标逐个过滤：
         a) 跳过 -1（FAISS 当检索不足 topk 时可能返回 -1 占位）
         b) 剔除出现在该样本 `pos` 中的文本
         c) 剔除与 `query` 文本完全相同的条目（防止把 query 自己当成负例）
       - 若过滤后数量超过 `negative_number`，随机采样到 `negative_number` 条。

    5) 对不足的样本进行随机补齐（避开 pos）：
       - 若数量仍不足 `negative_number`，则从 `corpus` 随机补齐（并避免与 `pos` 冲突）。

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
    # 1) 构造语料池与查询集
    corpus: List[str] = []
    queries: List[str] = []

    for data in train_data:
        # 把正例加入语料池；若已有负例，也加入语料池作为潜在"硬负样本"的候选（之后仍会过滤）
        corpus.extend(data.get("pos", []))
        if "neg" in data:
            corpus.extend(data["neg"])
        queries.append(data["query"])

    # 若提供外部候选池，则完全由候选池决定检索语料；否则，使用上文收集的 pos/neg 汇总去重
    if candidate_pool is not None:
        corpus = list(set(candidate_pool))
    else:
        corpus = list(set(corpus))

    # 2) 向量化 - 使用异步接口
    # 批量处理 corpus embeddings
    p_vecs_list: List[List[float]] = []
    for i in range(0, len(corpus), embedding_batch_size):
        batch_corpus = corpus[i : i + embedding_batch_size]
        batch_embeddings = await embedding_model.aembed_documents(batch_corpus)
        p_vecs_list.extend(batch_embeddings)

    # 处理返回结果：可能返回 dict（如 M3Embedder）或直接返回列表
    if not p_vecs_list:
        raise ValueError("No embeddings generated for corpus")

    if isinstance(p_vecs_list[0], dict):
        # 如果是 dict，尝试取 dense_vecs
        if "dense_vecs" in p_vecs_list[0]:
            p_vecs = np.array([vec["dense_vecs"] for vec in p_vecs_list], dtype=np.float32)
        else:
            # 如果是其他格式的 dict，取第一个值
            p_vecs = np.array([list(vec.values())[0] for vec in p_vecs_list], dtype=np.float32)
    else:
        p_vecs = np.array(p_vecs_list, dtype=np.float32)

    # 批量处理 query embeddings
    q_vecs_list: List[List[float]] = []
    for i in range(0, len(queries), embedding_batch_size):
        batch_queries = queries[i : i + embedding_batch_size]
        batch_embeddings = await embedding_model.aembed_documents(batch_queries)
        q_vecs_list.extend(batch_embeddings)

    # 处理返回结果
    if not q_vecs_list:
        raise ValueError("No embeddings generated for queries")

    if isinstance(q_vecs_list[0], dict):
        if "dense_vecs" in q_vecs_list[0]:
            q_vecs = np.array([vec["dense_vecs"] for vec in q_vecs_list], dtype=np.float32)
        else:
            q_vecs = np.array([list(vec.values())[0] for vec in q_vecs_list], dtype=np.float32)
    else:
        q_vecs = np.array(q_vecs_list, dtype=np.float32)

    # L2 归一化（使内积等价于余弦相似度）
    p_vecs = p_vecs / (np.linalg.norm(p_vecs, axis=1, keepdims=True) + 1e-8)
    q_vecs = q_vecs / (np.linalg.norm(q_vecs, axis=1, keepdims=True) + 1e-8)

    # 3) 建索引 + KNN 检索
    index = create_index(p_vecs, use_gpu=use_gpu)

    # 解析 sample_range：允许传入字符串 "10-210" 或 [10, 210]
    if isinstance(sample_range, str):
        L, R = [int(x) for x in sample_range.split("-")]
    else:
        L, R = sample_range

    # topk 至少为上界 R
    _, all_inxs = batch_search(index, q_vecs, topk=R)
    assert len(all_inxs) == len(train_data)

    # 4) 针对每条样本进行区间裁剪 + 过滤 + 抽样
    enhanced_data = []
    for i, data in enumerate(train_data):
        query_text = data["query"]
        inxs = all_inxs[i][L:R]  # 仅取 [L, R) 区间作为候选负样本

        filtered_inx = []
        for inx in inxs:
            if inx == -1:
                break  # -1 表示无更多命中

            # 过滤：不能命中到正例；且不能与 query 完全相同
            if corpus[inx] not in data.get("pos", []) and corpus[inx] != query_text:
                filtered_inx.append(inx)

        # 超过需求数量则随机裁剪
        if len(filtered_inx) > negative_number:
            filtered_inx = random.sample(filtered_inx, negative_number)

        # 回填到当前样本的 neg
        data["neg"] = [corpus[inx] for inx in filtered_inx]
        enhanced_data.append(data)

    # 5) 对不足的样本进行随机补齐（避开 pos）
    for data in enhanced_data:
        if len(data["neg"]) < negative_number:
            # 从整个 corpus 中随机采样，数量 = 需要补齐的数量 + 正例数量
            # 之后再把与 pos 冲突的剔除掉，确保最终补齐到 negative_number
            samples = random.sample(
                corpus, min(negative_number - len(data["neg"]) + len(data.get("pos", [])), len(corpus))
            )
            samples = [sent for sent in samples if sent not in data.get("pos", [])]
            data["neg"].extend(samples[: negative_number - len(data["neg"])])

    return enhanced_data

