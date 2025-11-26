# 评估维度（Metric）API 使用指南

## 概述

评估维度分为两种类型：
- **内置维度（BUILTIN）**：系统预置的评估指标，不可修改、不可删除
- **自定义维度（CUSTOM）**：用户创建的评估指标，可修改、可删除

## 创建自定义维度

用户创建自定义维度只需提供**三要素**：名称、描述、提示词

### API 请求示例

```http
POST /api/v1/metrics
Content-Type: application/json

{
  "name": "custom_accuracy",
  "description": "自定义准确性评估",
  "prompt": "请评估答案的准确性，给出 0-1 之间的分数"
}
```

### 响应示例

```json
{
  "code": 201,
  "msg": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "custom_accuracy",
    "description": "自定义准确性评估",
    "prompt": "请评估答案的准确性，给出 0-1 之间的分数",
    "type": "custom",
    "user_input_required": false,
    "actual_output_required": true,
    "expected_output_required": false,
    "context_required": false,
    "retrieval_context_required": false,
    "embedding_required": false,
    "llm_required": true,
    "created_at": "2025-10-28T10:00:00Z",
    "updated_at": "2025-10-28T10:00:00Z"
  }
}
```

### 字段说明

**用户提供的字段：**
- `name` (必填): 指标名称，全局唯一
- `description` (可选): 指标描述
- `prompt` (可选): 评估提示词

**系统自动设置的字段：**
- `type`: 自动设置为 `custom`
- `user_input_required`: 默认 `false`
- `actual_output_required`: 默认 `true`
- `expected_output_required`: 默认 `false`
- `context_required`: 默认 `false`
- `retrieval_context_required`: 默认 `false`
- `embedding_required`: 默认 `false`
- `llm_required`: 默认 `true` (自定义维度需要LLM执行评估)

## 更新自定义维度

用户只能更新三要素：名称、描述、提示词

```http
PUT /api/v1/metrics/{metric_id}
Content-Type: application/json

{
  "name": "updated_accuracy",
  "description": "更新后的描述",
  "prompt": "更新后的提示词"
}
```

**注意：** `type` 和其他配置字段（布尔值）不允许用户修改。

## 查询维度列表

```http
GET /api/v1/metrics?metric_type=custom&page=1&page_size=20
```

### 查询参数
- `metric_type` (可选): 过滤维度类型
  - `builtin`: 只返回内置维度
  - `custom`: 只返回自定义维度
  - 不传: 返回所有维度
- `page`: 页码（默认 1）
- `page_size`: 每页数量（默认 20）

## 删除自定义维度

```http
DELETE /api/v1/metrics/{metric_id}
```

**限制：**
- ✅ 可以删除自定义维度（type=custom）
- ❌ 不能删除内置维度（type=builtin）
- ❌ 不能删除被评估器引用的维度

## 前端 TypeScript 示例

```typescript
import { MetricCreate, MetricUpdate, EvalMetricTypeEnum } from '@/types/api';

// 创建自定义维度
const createCustomMetric = async () => {
  const newMetric: MetricCreate = {
    name: 'custom_accuracy',
    description: '自定义准确性评估',
    prompt: '请评估答案的准确性',
  };
  
  const response = await fetch('/api/v1/metrics', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(newMetric),
  });
  
  const result = await response.json();
  console.log(result.data); // MetricResponse
};

// 更新自定义维度
const updateCustomMetric = async (metricId: string) => {
  const updates: MetricUpdate = {
    description: '更新后的描述',
    prompt: '更新后的提示词',
  };
  
  await fetch(`/api/v1/metrics/${metricId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
};

// 获取维度列表（只获取自定义维度）
const getCustomMetrics = async () => {
  const response = await fetch('/api/v1/metrics?metric_type=custom');
  const result = await response.json();
  return result.data.items; // MetricResponse[]
};
```

## 设计原则

1. **简化用户体验**：创建自定义维度只需三个字段，降低使用门槛
2. **自动化配置**：系统自动设置 type 和其他配置项的默认值
3. **明确权限边界**：用户只能管理自定义维度，无法修改内置维度
4. **保持扩展性**：内部保留完整的字段定义，便于未来扩展功能

## 常见问题

**Q: 为什么创建时不能指定 type？**  
A: 用户创建的维度统一为自定义维度（CUSTOM），内置维度（BUILTIN）由系统预置。

**Q: 如何修改布尔配置字段？**  
A: 当前版本不支持用户修改这些字段，使用数据库默认值。如需调整，可联系管理员直接修改数据库。

**Q: 删除维度时提示"被评估器引用"？**  
A: 需要先删除或修改引用该维度的评估器，然后才能删除维度。


