# 模型管理功能使用指南

## 📝 功能概述

模型管理功能允许你统一管理系统中使用的 LLM 和 Embedding 模型配置，支持：

- ✅ **创建模型配置**：配置 OpenAI、Azure、Anthropic 等各种提供商的模型
- ✅ **管理模型**：查看、编辑、删除模型配置
- ✅ **设置默认模型**：为 LLM 和 Embedding 分别设置默认模型
- ✅ **API Key 脱敏**：API Key 在前端显示时自动脱敏处理
- ✅ **使用统计**：追踪每个模型的使用次数和最后使用时间

## 🚀 快速开始

### 1. 数据库迁移

首先需要运行数据库迁移以创建 `models` 表：

```bash
cd diting/packages/diting-web/backend

# 运行迁移
alembic upgrade head
```

迁移会自动创建示例模型：
- GPT-4 (LLM, 默认)
- GPT-3.5 Turbo (LLM)
- Claude 3 Sonnet (LLM)
- Text Embedding 3 Small (Embedding, 默认)
- Text Embedding Ada 002 (Embedding)

### 2. 启动后端服务

```bash
# 开发模式
cd diting/packages/diting-web/backend
python -m diting_web.main
```

后端服务将在 `http://localhost:8000` 启动。

### 3. 启动前端服务

```bash
cd diting/packages/diting-web/frontend
pnpm install
pnpm dev
```

前端服务将在 `http://localhost:5173` 启动。

### 4. 访问模型管理页面

1. 登录系统（默认账户：admin / admin123）
2. 点击侧边栏的 **"模型管理"** 菜单
3. 查看、创建、编辑或删除模型配置

## 📖 API 接口说明

### 基础 URL

```
http://localhost:8000/api/v1/models
```

### 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/models` | 创建模型 |
| GET | `/models` | 获取模型列表（支持分页和类型筛选） |
| GET | `/models/{model_id}` | 获取单个模型详情 |
| PUT | `/models/{model_id}` | 更新模型 |
| DELETE | `/models/{model_id}` | 删除模型 |
| POST | `/models/{model_id}/set-default` | 设置默认模型 |

### 示例：创建模型

```bash
curl -X POST http://localhost:8000/api/v1/models \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "GPT-4 Turbo",
    "model_type": "llm",
    "provider": "OpenAI",
    "model_name": "gpt-4-turbo",
    "api_key": "sk-xxx",
    "base_url": "https://api.openai.com/v1",
    "description": "最新的 GPT-4 Turbo 模型",
    "timeout": 60,
    "parameters": {
      "temperature": 0.7,
      "max_tokens": 2000
    },
    "is_default": false
  }'
```

## 🎨 前端使用说明

### 添加模型

1. 点击右上角 **"添加模型"** 按钮
2. 填写模型信息：
   - **模型名称**（必填）：如 "GPT-4"
   - **模型类型**（必填）：选择 LLM 或 Embedding
   - **提供商**（必填）：如 "OpenAI"
   - **模型标识**（必填）：如 "gpt-4"
   - **API Key**（可选）：留空则使用系统默认配置
   - **Base URL**（可选）：自定义 API 端点
   - **描述**（可选）：模型描述信息
   - **超时时间**：默认 60 秒
   - **设为默认模型**：勾选后自动取消同类型的其他默认模型
3. 点击 **"创建"** 保存

### 编辑模型

1. 在模型列表中找到目标模型
2. 点击 **"编辑"** 按钮
3. 修改需要的字段（模型类型不可修改）
4. 点击 **"保存"**

### 设置默认模型

1. 在模型列表中找到目标模型
2. 点击 **"设为默认"** 按钮
3. 系统自动取消同类型的其他默认模型

### 删除模型

1. 在模型列表中找到目标模型
2. 点击 **"删除"** 按钮
3. 确认删除操作

**注意**：如果某个类型只有一个模型，删除前需要先添加其他模型。

## 🔒 安全性说明

### API Key 脱敏

- API Key 在数据库中以明文存储（建议后续加密）
- 前端显示时自动脱敏处理，只显示前 4 位和后 3 位
- 例如：`sk-xxx123456789` 显示为 `sk-x***789`

### 建议的安全措施

1. **加密存储**：在生产环境中使用 PostgreSQL 的 `pgcrypto` 扩展加密 API Key
2. **环境变量**：优先使用环境变量配置全局 API Key
3. **权限控制**：确保只有管理员可以访问模型管理功能
4. **审计日志**：记录模型配置的创建、修改、删除操作

## 📊 数据库表结构

```sql
CREATE TABLE models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- 基本信息
    name VARCHAR(100) NOT NULL,
    model_type model_type_enum NOT NULL,  -- 'llm' | 'embedding'
    provider VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    description TEXT,
    -- 配置信息
    api_key TEXT,
    base_url VARCHAR(500),
    parameters JSONB DEFAULT '{}',
    timeout INTEGER DEFAULT 60,
    -- 默认标记
    is_default BOOLEAN DEFAULT FALSE,
    -- 使用统计
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## 🔧 技术架构

### 前端技术栈

- **React 18** + **TypeScript**
- **React Router** 用于路由管理
- **Tailwind CSS** 用于样式
- **Axios** 用于 HTTP 请求

### 后端技术栈

- **FastAPI** Web 框架
- **SQLAlchemy 2.0** ORM
- **PostgreSQL** 数据库
- **Alembic** 数据库迁移
- **Pydantic** 数据验证

### 代码结构

```
backend/
├── src/diting_web/
│   ├── models/model.py           # SQLAlchemy 模型
│   ├── schemas/model.py          # Pydantic Schema
│   ├── services/model_service.py # 业务逻辑层
│   └── api/v1/models.py          # API 路由
├── alembic/
│   └── versions/
│       └── 001_add_models_table.py  # 数据库迁移

frontend/
├── src/
│   ├── types/api.ts              # TypeScript 类型定义
│   ├── api/client.ts             # API 客户端
│   └── pages/Models.tsx          # 模型管理页面
```

## 🎯 最佳实践

### 1. 模型命名规范

- 使用清晰易懂的名称，如 "GPT-4"、"Claude 3 Sonnet"
- 避免使用技术性的模型标识作为显示名称

### 2. 提供商管理

常见提供商：
- `OpenAI` - OpenAI 官方
- `Azure` - Azure OpenAI Service
- `Anthropic` - Anthropic Claude
- `Google` - Google AI (Gemini)
- `Cohere` - Cohere AI
- `Custom` - 自定义提供商

### 3. 默认模型设置

- 每种类型（LLM/Embedding）应至少有一个默认模型
- 默认模型用于未指定模型的场景
- 定期评估和更新默认模型

### 4. 参数配置示例

**LLM 模型参数：**
```json
{
  "temperature": 0.7,
  "max_tokens": 2000,
  "top_p": 1.0,
  "frequency_penalty": 0.0,
  "presence_penalty": 0.0
}
```

**Embedding 模型参数：**
```json
{
  "dimensions": 1536,
  "encoding_format": "float"
}
```

## 🐛 故障排除

### 问题：无法创建模型

**可能原因**：
- 数据库迁移未执行
- 模型名称和类型组合已存在

**解决方法**：
1. 检查数据库迁移状态：`alembic current`
2. 使用不同的模型名称或类型

### 问题：API Key 显示异常

**可能原因**：
- API Key 格式不符合预期

**解决方法**：
- 确保 API Key 长度大于 10 个字符
- 检查 `mask_api_key()` 方法的实现

### 问题：无法删除默认模型

**可能原因**：
- 试图删除该类型的唯一模型

**解决方法**：
1. 先创建同类型的其他模型
2. 将其他模型设为默认
3. 再删除原默认模型

## 📚 相关文档

- [后端设计文档](./docs/BACKEND_DESIGN.md) - 完整的后端架构设计
- [前端集成说明](./FRONTEND_METRIC_INTEGRATION.md) - 前端集成指南
- [本地开发指南](./LOCAL_DEV_GUIDE.md) - 本地开发环境搭建

## 🎉 总结

模型管理功能为 diting-web 提供了统一的模型配置管理能力，使得：

1. **配置集中**：所有模型配置在一处管理
2. **易于切换**：快速切换不同提供商和模型
3. **成本优化**：根据任务需求选择合适的模型
4. **安全可控**：API Key 脱敏处理，保护敏感信息

如有问题或建议，欢迎提交 Issue！

