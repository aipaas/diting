# RerankMetric

RerankMetric 是一个专门用于计算rerank相关指标的评估工具，支持以下核心指标：

- **MRR (Mean Reciprocal Rank)**: 平均倒数排名
- **NDCG (Normalized Discounted Cumulative Gain)**: 标准化折损累积增益
- **MAP (Mean Average Precision)**: 平均精度均值

## 功能特性

1. **多指标支持**: 同时计算MRR、NDCG、MAP三个核心指标
2. **灵活的数据格式**: 支持DataFrame、字典列表等多种数据输入格式
3. **自定义计算列**: 可指定需要计算的列名（如embedding_top5、rerank_top10等）
4. **详细的统计信息**: 提供命中率、详细分数等统计信息
5. **标准接口**: 继承自BaseMetric，可与现有的评估系统无缝集成

## 数据格式要求

输入数据需要包含以下字段：

### 必需字段
- `expect_kids`: 期望的参考文档ID列表

### 可选字段（评估列）
- `embedding_top5`/`embedding_top10`/`embedding_top15`: embedding检索结果
- `rerank_top5`/`rerank_top10`/`rerank_top15`: rerank后的结果

### 示例数据格式

```python
data = [
    {
        "question": "什么是机器学习？",
        "expect_kids": ["doc1","doc2","doc3"],
        "embedding_top5": ["doc1", "doc4", "doc2", "doc5", "doc6"],
        "rerank_top5": ["doc2", "doc1", "doc3", "doc4", "doc5"],
    }
]
```

## 指标说明

### MRR (Mean Reciprocal Rank)
- **定义**: 第一个相关文档的排名的倒数的平均值
- **范围**: [0, 1]，越高越好
- **用途**: 衡量系统找到第一个正确答案的能力

### NDCG (Normalized Discounted Cumulative Gain)
- **定义**: 标准化后的折损累积增益
- **范围**: [0, 1]，越高越好
- **用途**: 考虑排名位置和相关性，适用于多相关文档的情况

### MAP (Mean Average Precision)
- **定义**: 平均精度(AP)的平均值
- **范围**: [0, 1]，越高越好
- **用途**: 综合考虑 precision 和 recall，适用于检索质量评估

## 输出结果

RerankMetric返回包含以下信息的MetricValue：

```python
MetricValue(
    score=0.75,  # 主要分数（默认为rerank_top10_mrr MRR）
    reason="详细的计算结果说明...",
    run_logs={
        "detailed_results": {
            # 各列的详细指标
            "embedding_top5_mrr": 0.8,
            "embedding_top5_ndcg": 0.75,
            "embedding_top5_map": 0.7,
            "embedding_top5_precision": 0.6,
            ...
        },
        "mrr_scores": {...},  # 各列的MRR分数数组
        "ndcg_scores": {...}, # 各列的NDCG分数数组
        "map_scores": {...},  # 各列的MAP分数数组
        "column_stats": {...}, # 统计信息
        "total_rows": 100,
        "expect_count": 95
    }
)
```

## 配置选项

### columns_to_evaluate
指定需要评估的列名列表：
```python
metric = RerankMetric(
    columns_to_evaluate=[
        "embedding_top5", 
        "rerank_top10", 
        "rrf_top15"
    ]
)
```

### k_values
指定评估的top-k值（目前用于限制NDCG计算的最大k值）：
```python
metric = RerankMetric(k_values=[5, 10, 15])
```