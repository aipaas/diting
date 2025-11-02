# RAG 参数优化项目待办事项清单

## 项目概述

本项目旨在实现一个完整的 RAG（检索增强生成）参数优化系统，通过自动化搜索最优参数组合来提升检索系统的性能。

## 功能需求

### 1. 核心优化功能
- [ ] 实现语义搜索参数优化器
  - [ ] 支持相似度阈值参数优化
  - [ ] 支持上下文召回 token 数量优化
  - [ ] 实现穷举搜索算法
  - [ ] 支持自定义参数范围和步长

### 2. 指标系统
- [ ] 实现混合指标评估系统
  - [ ] 参考 example.py 中的复合指标用法
  - [ ] 使用 ContextPrecision 和 ContextRecall 指标
  - [ ] 支持权重配置
  - [ ] 实现指标结果的综合计算

### 3. 回调机制
- [ ] 实现参数回调传参功能
  - [ ] 通过回调接口将当前参数组合传入检索服务
  - [ ] RAG 服务根据参数调整检索行为
  - [ ] 确保优化过程与真实场景一致

### 4. 服务架构
- [ ] 优化服务（diting-server）
  - [ ] 提供参数优化 API 接口
  - [ ] 实现优化算法逻辑
  - [ ] 支持回调机制
- [ ] RAG 服务（diting_rag_system）
  - [ ] 提供检索 API 接口
  - [ ] 支持参数化检索
  - [ ] 实现基于参数的检索结果过滤

### 5. 客户端功能
- [ ] 实现优化请求构建
  - [ ] 支持自定义数据集
  - [ ] 支持参数搜索空间配置
  - [ ] 支持全局上下文配置
- [ ] 实现结果展示
  - [ ] 显示最优参数组合
  - [ ] 展示优化过程历史
  - [ ] 提供性能提升统计

## 技术要求

### 1. 指标实现
参考 example.py 文件中的复合指标实现：
```python
# 创建context_precision和context_recall实例
context_precision = ContextPrecision(model=llm_model)
context_recall = ContextRecall(model=llm_model)

# 使用CompositeMetric组合它们，权重各自0.5
metric = CompositeMetric(
    metrics=[context_precision, context_recall],
    weights=[0.5, 0.5]  # 各自0.5权重
)
```

### 2. 参数回调传参
确保在优化过程中通过回调接口将参数传递给 RAG 服务：
- similarity_threshold: 相似度阈值
- context_recall_max_tokens: 上下文召回最大 token 数

### 3. API 接口
- 优化服务接口: `POST /api/v1/optimizations/rag`
- RAG 服务接口: `POST /api/v1/rag/retrieval`

## 待解决的问题

### 1. 指标类缺少 evaluate 方法
- [ ] 修复 AverageSimilarityMetric 类，添加 evaluate 方法
- [ ] 确保指标类与优化器兼容

### 2. 浮点数无穷大处理
- [ ] 在构建 API 响应时检查浮点数值
- [ ] 将 inf 或 NaN 值转换为合理默认值

## 验收标准

- [ ] 成功运行完整的参数优化流程
- [ ] 正确使用混合指标进行评估
- [ ] 通过回调传参实现参数化检索
- [ ] 输出最优参数组合和性能提升统计
- [ ] 生成详细的优化过程日志