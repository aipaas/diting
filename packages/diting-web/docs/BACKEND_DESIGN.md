# Diting-Web 后端总体设计文档

## 📋 目录

1. [系统架构](#系统架构)
2. [数据库设计](#数据库设计)
3. [API 设计](#api-设计)
4. [数据结构 Schema](#数据结构-schema)
5. [业务流程](#业务流程)
6. [技术栈](#技术栈)

---

## 1. 系统架构

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      diting-web                             │
│                   (Web 应用层)                              │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            Frontend (React)                          │  │
│  │         http://localhost:5173                        │  │
│  └────────────────────┬─────────────────────────────────┘  │
│                       │ HTTP/WebSocket                      │
│                       ↓                                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Backend API (FastAPI)                        │  │
│  │         http://localhost:8000                        │  │
│  │                                                       │  │
│  │  Routes:                                             │  │
│  │  • /api/v1/healthz   - 健康检查 🆕                   │  │
│  │  • /api/v1/datasets  - 数据集管理                   │  │
│  │  • /api/v1/tasks     - 任务管理 (核心)              │  │
│  │  • /api/v1/metrics   - 评估维度管理 🆕               │  │
│  │  • /api/v1/evaluators- 评估器管理 🆕                 │  │
│  │  • /api/v1/results   - 结果查询                     │  │
│  │  • /api/v1/statistics- 统计信息 🆕                   │  │
│  │  • /ws               - WebSocket                     │  │
│  └──────────┬───────────────────────┬───────────────────┘  │
│             │                       │                       │
│             ↓                       ↓                       │
│  ┌──────────────────┐    ┌──────────────────┐             │
│  │   PostgreSQL     │    │   Redis          │             │
│  │   (数据持久化)   │    │   (队列+缓存)    │             │
│  └──────────────────┘    └────────┬─────────┘             │
│                                   │                         │
│                                   ↓                         │
│                          ┌──────────────────┐               │
│                          │  arq Worker      │               │
│                          │  (异步任务处理)  │               │
│                          └────────┬─────────┘               │
└───────────────────────────────────┼─────────────────────────┘
                                    │
                                    │ HTTP API 调用
                                    ↓
                    ┌───────────────────────────────┐
                    │      diting-server            │
                    │    (独立评估微服务)           │
                    │  http://localhost:3000        │
                    │                               │
                    │  • POST /api/v1/evaluations   │
                    │  • POST /api/v1/synthesis     │
                    └───────────────────────────────┘
```

### 1.2 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| **核心 SDK** | **diting-core** | **workspace** |
| Web 框架 | FastAPI | ≥0.115.0 |
| 数据库 | PostgreSQL | ≥16.0 |
| ORM | SQLAlchemy | ≥2.0.0 |
| 迁移工具 | Alembic | ≥1.13.0 |
| 任务队列 | arq | ≥0.25.0 |
| 缓存 | Redis | ≥7.0 |
| WebSocket | python-socketio | ≥5.11.0 |
| 认证 | python-jose | ≥3.3.0 |
| 对象存储 | MinIO | latest |

---

## 2. 数据库设计

### 2.1 ER 图

```
┌─────────────┐
│ admin_users │ ← 新增：管理员表
│             │
│  • id       │
│  • username │
│  • password │
└─────────────┘
       │
       │ (所有操作都需要 admin 认证)
       │
┌─────────────┐         ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   models    │ 🆕      │   metrics    │         │ evaluators  │         │  datasets   │
│             │         │             │       n │             │         │             │
│  • id       │         │  • id       │◄────────┤  • id       │         │  • id       │
│  • name     │         │  • name     │ metrics │  • name     │         │  • name     │
│  • type     │         │  • category │         │  • desc     │         │  • file_path│
│  • provider │         └─────────────┘         └──────┬──────┘         └──────┬──────┘
└─────────────┘                                        │1                      │1
                                                       │                       │
                                                       │n                      │n
                                                ┌──────┴──────┐         ┌──────┴──────────┐
                                                │    tasks    │         │  dataset_rows   │ 🆕
                                                │             │         │                 │
                                                │  • id       │         │  • id           │
                                                │  • type     │         │  • dataset_id   │
                                                │  • status   │         │  • row_index    │
                                                │  • config   │         │  • data (JSONB) │
                                                │  • result   │         └─────────────────┘
                                                └──────┬──────┘
                                                       │1
                                        ┌──────────────┼──────────────┐
                                        │n             │n             │n
                                 ┌──────┴──────┐ ┌────┴─────┐ ┌──────┴──────┐
                                 │ evaluation  │ │synthesis │ │ audit_logs  │
                                 │ _results    │ │_results  │ │             │
                                 │             │ │          │ │  • action   │
                                 │  • score    │ │• question│ │  • resource │
                                 │  • reason   │ │• answer  │ └─────────────┘
                                 └─────────────┘ └──────────┘

说明：
- 添加了 admin_users 表，存储管理员信息（单 Admin 模式）
- 添加了 models 表 🆕，统一管理 LLM 和 Embedding 模型配置
- 移除了 projects 表，简化资源管理
- metrics: 评估维度表，存储内置和自定义评估指标
- evaluators: 评估器表，组合多个 metrics 用于批量评估
- datasets: 数据集表，存储数据集元信息
- dataset_rows: 数据集行表 🆕，每行数据为一条记录，支持索引和快速搜索
- 所有资源都是全局的，但需要 admin 认证
- 未来可扩展：添加 user_id 字段实现多用户支持
```

### 2.2 数据表设计 (v1.0 - 单 Admin 模式)

> **注意**: 采用单 Admin 模式，简化了用户管理，所有资源都是全局的。

#### 2.2.1 admin_users (管理员表) 🆕

```sql
CREATE TABLE admin_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 插入默认 admin 用户
INSERT INTO admin_users (username, hashed_password) VALUES 
('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8Kz8Kz8');

-- 索引
CREATE INDEX idx_admin_users_username ON admin_users(username);
CREATE INDEX idx_admin_users_active ON admin_users(is_active);

-- 注释
COMMENT ON TABLE admin_users IS '管理员表（单 Admin 模式）';
COMMENT ON COLUMN admin_users.username IS '管理员用户名（固定为 admin）';
COMMENT ON COLUMN admin_users.hashed_password IS '密码哈希';
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | UUID | 是 | 主键 |
| username | VARCHAR(50) | 是 | 用户名（固定为 admin） |
| hashed_password | VARCHAR(255) | 是 | bcrypt 哈希密码 |
| is_active | BOOLEAN | 是 | 是否激活 |
| last_login_at | TIMESTAMPTZ | 否 | 最后登录时间 |
| created_at | TIMESTAMPTZ | 是 | 创建时间 |
| updated_at | TIMESTAMPTZ | 是 | 更新时间 |

---

#### 2.2.2 models (模型管理表) 🆕

```sql
-- 模型类型枚举
CREATE TYPE model_type_enum AS ENUM ('llm', 'embedding');

CREATE TABLE models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- 基本信息
    name VARCHAR(100) NOT NULL,
    model_type model_type_enum NOT NULL,
    provider VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    description TEXT,
    -- 配置信息
    api_key TEXT,
    base_url VARCHAR(500),
    parameters JSONB DEFAULT '{}',
    timeout INTEGER DEFAULT 60,
    -- 默认标记
    is_default BOOLEAN DEFAULT FALSE NOT NULL,
    -- 使用统计
    usage_count INTEGER DEFAULT 0 NOT NULL,
    last_used_at TIMESTAMPTZ,
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    -- 唯一约束：每种类型只能有一个默认模型
    CONSTRAINT unique_default_per_type UNIQUE (model_type, is_default) 
        WHERE is_default = TRUE
);

-- 索引
CREATE INDEX idx_models_type ON models(model_type);
CREATE INDEX idx_models_provider ON models(provider);
CREATE INDEX idx_models_is_default ON models(is_default) WHERE is_default = TRUE;
CREATE INDEX idx_models_created ON models(created_at DESC);
CREATE INDEX idx_models_usage ON models(usage_count DESC);

-- 注释
COMMENT ON TABLE models IS '模型管理表（统一管理 LLM 和 Embedding 模型）';
COMMENT ON COLUMN models.name IS '模型显示名称';
COMMENT ON COLUMN models.model_type IS '模型类型：llm / embedding';
COMMENT ON COLUMN models.provider IS '提供商（如 OpenAI, Azure, Anthropic）';
COMMENT ON COLUMN models.model_name IS '实际调用的模型标识（如 gpt-4, text-embedding-3-small）';
COMMENT ON COLUMN models.api_key IS 'API Key（加密存储，可选）';
COMMENT ON COLUMN models.base_url IS '自定义 API 端点（可选）';
COMMENT ON COLUMN models.parameters IS '模型参数配置（JSONB）';
COMMENT ON COLUMN models.timeout IS '超时时间（秒），默认 60';
COMMENT ON COLUMN models.is_default IS '是否为该类型的默认模型';
COMMENT ON COLUMN models.usage_count IS '使用次数统计';
COMMENT ON COLUMN models.last_used_at IS '最后使用时间';
```

**字段说明**：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | UUID | 是 | gen_random_uuid() | 主键 |
| name | VARCHAR(100) | 是 | - | 模型显示名称（如 GPT-4） |
| model_type | ENUM | 是 | - | 模型类型（llm / embedding） |
| provider | VARCHAR(50) | 是 | - | 提供商（OpenAI, Azure, Anthropic 等） |
| model_name | VARCHAR(100) | 是 | - | 实际调用的模型标识 |
| description | TEXT | 否 | NULL | 模型描述 |
| api_key | TEXT | 否 | NULL | API Key（建议加密存储） |
| base_url | VARCHAR(500) | 否 | NULL | 自定义 API 端点 |
| parameters | JSONB | 否 | {} | 模型参数配置 |
| timeout | INTEGER | 是 | 60 | 超时时间（秒） |
| is_default | BOOLEAN | 是 | FALSE | 是否为默认模型 |
| usage_count | INTEGER | 是 | 0 | 使用次数统计 |
| last_used_at | TIMESTAMPTZ | 否 | NULL | 最后使用时间 |
| created_at | TIMESTAMPTZ | 是 | NOW() | 创建时间 |
| updated_at | TIMESTAMPTZ | 是 | NOW() | 更新时间 |

**parameters 字段示例**：
```json
{
  "temperature": 0.7,
  "max_tokens": 2000,
  "top_p": 1.0,
  "frequency_penalty": 0.0,
  "presence_penalty": 0.0
}
```

**设计说明**：

1. **模型类型**：
   - **LLM**：大语言模型（用于评估、生成等）
   - **Embedding**：嵌入模型（用于语义相似度计算等）

2. **默认模型**：
   - 每种类型（llm/embedding）只能有一个默认模型
   - 通过唯一约束 `unique_default_per_type` 保证
   - 设置新默认模型时，需要先取消旧默认模型

3. **安全性**：
   - API Key 建议加密存储（可使用 `pgcrypto` 扩展）
   - 前端不应返回完整的 API Key，只返回脱敏后的部分

4. **灵活性**：
   - 支持自定义 base_url（私有部署、代理等场景）
   - parameters 使用 JSONB 存储，支持任意模型参数
   - 统计使用次数和最后使用时间，便于优化和清理

**示例数据**：
```sql
-- 插入示例模型
INSERT INTO models (name, model_type, provider, model_name, description, is_default) VALUES
  ('GPT-4', 'llm', 'OpenAI', 'gpt-4', 'OpenAI GPT-4 模型，适合复杂推理任务', TRUE),
  ('GPT-3.5 Turbo', 'llm', 'OpenAI', 'gpt-3.5-turbo', '性价比高的通用模型', FALSE),
  ('Claude 3 Sonnet', 'llm', 'Anthropic', 'claude-3-sonnet-20240229', 'Anthropic Claude 3 Sonnet', FALSE),
  ('Text Embedding 3 Small', 'embedding', 'OpenAI', 'text-embedding-3-small', '高性价比嵌入模型', TRUE),
  ('Text Embedding Ada 002', 'embedding', 'OpenAI', 'text-embedding-ada-002', '传统嵌入模型', FALSE);
```

---

#### 2.2.3 datasets (数据集表)

```sql
CREATE TABLE datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    file_path VARCHAR(500),
    file_size BIGINT,
    file_type VARCHAR(50),
    row_count INTEGER NOT NULL DEFAULT 0,
    columns JSONB,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_datasets_name ON datasets(name);
CREATE INDEX idx_datasets_created ON datasets(created_at DESC);
CREATE INDEX idx_datasets_type ON datasets(file_type);

-- 注释
COMMENT ON TABLE datasets IS '数据集表';
COMMENT ON COLUMN datasets.file_path IS 'MinIO 存储路径（原始文件备份）';
COMMENT ON COLUMN datasets.columns IS '列信息（JSON）';
COMMENT ON COLUMN datasets.metadata IS '元数据（JSON），包含 annotation_columns 等配置，不再存储 full_data';
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | UUID | 是 | 主键 |
| name | VARCHAR(100) | 是 | 数据集名称 |
| description | TEXT | 否 | 描述 |
| file_path | VARCHAR(500) | 否 | MinIO 存储路径（原始文件备份） |
| file_size | BIGINT | 否 | 文件大小（字节） |
| file_type | VARCHAR(50) | 否 | 文件类型（csv, jsonl, parquet） |
| row_count | INTEGER | 是 | 行数（从 dataset_rows 表统计） |
| columns | JSONB | 否 | 列信息 |
| metadata | JSONB | 否 | 元数据（包含 annotation_columns 等配置，不再存储 full_data） |
| created_at | TIMESTAMPTZ | 是 | 创建时间 |
| updated_at | TIMESTAMPTZ | 是 | 更新时间 |

**columns 示例**：
```json
[
  {"name": "user_input", "type": "string", "nullable": false},
  {"name": "actual_output", "type": "string", "nullable": false},
  {"name": "expected_output", "type": "string", "nullable": true}
]
```

**metadata 示例**（不再包含 full_data）：
```json
{
  "column_count": 3,
  "data_types": {
    "user_input": "object",
    "actual_output": "object",
    "expected_output": "object"
  },
  "annotation_columns": [
    {
      "column_name": "情感标注",
      "column_type": "category",
      "description": "情感分类标注",
      "options": ["正面", "负面", "中性"]
    }
  ]
}
```

**设计变更说明**：
- ⚠️ **重要变更**：`metadata.full_data` 不再存储实际数据行
- ✅ 实际数据行存储在 `dataset_rows` 表中（见下方）
- ✅ 这样可以支持索引、快速搜索和高效更新

---

#### 2.2.4 dataset_rows (数据集行表) 🆕

```sql
CREATE TABLE dataset_rows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    row_index INTEGER NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 唯一约束：每个数据集中的行索引唯一
    CONSTRAINT unique_dataset_row UNIQUE (dataset_id, row_index)
);

-- 索引
CREATE INDEX idx_dataset_rows_dataset ON dataset_rows(dataset_id);
CREATE INDEX idx_dataset_rows_index ON dataset_rows(dataset_id, row_index);
CREATE INDEX idx_dataset_rows_data_gin ON dataset_rows USING GIN (data);  -- JSONB GIN索引，加速搜索

-- 全文搜索索引（可选，用于全文搜索）
CREATE INDEX idx_dataset_rows_data_fts ON dataset_rows 
    USING GIN (to_tsvector('english', data::text));

-- 注释
COMMENT ON TABLE dataset_rows IS '数据集行表（每行数据为一条记录）';
COMMENT ON COLUMN dataset_rows.dataset_id IS '所属数据集ID（外键 → datasets.id）';
COMMENT ON COLUMN dataset_rows.row_index IS '行索引（从0开始，用于排序）';
COMMENT ON COLUMN dataset_rows.data IS '数据行内容（JSONB，包含所有列的数据）';
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | UUID | 是 | 主键 |
| dataset_id | UUID | 是 | 所属数据集ID（外键 → datasets.id） |
| row_index | INTEGER | 是 | 行索引（从0开始，用于排序和维护顺序） |
| data | JSONB | 是 | 数据行内容（包含所有列的数据） |
| created_at | TIMESTAMPTZ | 是 | 创建时间 |
| updated_at | TIMESTAMPTZ | 是 | 更新时间 |

**data 字段示例**：
```json
{
  "user_input": "世界最高峰是什么",
  "expected_output": "珠穆朗玛峰",
  "情感标注": "中性"
}
```

**设计说明**：

1. **数据存储**：
   - 每行数据存储为一条独立的数据库记录
   - `data` 字段使用 JSONB 类型，支持灵活的列结构
   - `row_index` 字段维护行的原始顺序

2. **性能优化**：
   - GIN 索引加速 JSONB 查询和搜索
   - 全文搜索索引（可选）支持全文搜索功能
   - `(dataset_id, row_index)` 索引加速分页查询

3. **优势**：
   - ✅ 支持数据库层面的快速搜索（SQL WHERE 条件）
   - ✅ 更新单行数据高效（直接 UPDATE 单条记录）
   - ✅ 支持索引，查询性能好
   - ✅ 内存友好（只加载需要的数据）
   - ✅ 支持复杂查询（JOIN、聚合等）

4. **数据迁移**：
   - 上传数据集时，将 `full_data` 中的每行数据插入到 `dataset_rows` 表
   - 保持 `row_index` 与原始顺序一致

---

#### 2.2.5 metrics (评估维度表) 🆕

```sql
-- 指标类型枚举
CREATE TYPE metric_type_enum AS ENUM ('builtin', 'custom');

CREATE TABLE metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- 基本信息
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    type metric_type_enum DEFAULT 'custom' NOT NULL,
    prompt TEXT,
    -- 必需项配置
    user_input_required BOOLEAN DEFAULT FALSE NOT NULL,
    actual_output_required BOOLEAN DEFAULT TRUE NOT NULL,
    expected_output_required BOOLEAN DEFAULT FALSE NOT NULL,
    context_required BOOLEAN DEFAULT FALSE NOT NULL,
    retrieval_context_required BOOLEAN DEFAULT FALSE NOT NULL,
    -- 模型依赖
    embedding_required BOOLEAN DEFAULT FALSE NOT NULL,
    llm_required BOOLEAN DEFAULT FALSE NOT NULL,
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- 索引
CREATE UNIQUE INDEX idx_metrics_name ON metrics(name);
CREATE INDEX idx_metrics_type ON metrics(type);

-- 注释
COMMENT ON TABLE metrics IS '评估维度表（单 Admin 模式 - 全局资源）';
COMMENT ON COLUMN metrics.name IS '指标名称（唯一，如 answer_correctness）';
COMMENT ON COLUMN metrics.description IS '描述';
COMMENT ON COLUMN metrics.type IS '指标类型：builtin（内置）/ custom（自定义）';
COMMENT ON COLUMN metrics.prompt IS '提示词（内置维度为 NULL，自定义维度可选）';
COMMENT ON COLUMN metrics.user_input_required IS '是否需要用户输入';
COMMENT ON COLUMN metrics.actual_output_required IS '是否需要实际输出';
COMMENT ON COLUMN metrics.expected_output_required IS '是否需要期望输出';
COMMENT ON COLUMN metrics.context_required IS '是否需要上下文';
COMMENT ON COLUMN metrics.retrieval_context_required IS '是否需要检索上下文';
COMMENT ON COLUMN metrics.embedding_required IS '是否需要嵌入模型';
COMMENT ON COLUMN metrics.llm_required IS '是否需要大语言模型';
```

**字段说明**：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | UUID | 是 | gen_random_uuid() | 主键 |
| name | VARCHAR(100) | 是 | - | 指标名称（唯一） |
| description | TEXT | 否 | NULL | 描述 |
| type | ENUM | 是 | custom | 指标类型（builtin/custom） |
| prompt | TEXT | 否 | NULL | 提示词（内置维度为 NULL） |
| user_input_required | BOOLEAN | 是 | FALSE | 是否需要用户输入 |
| actual_output_required | BOOLEAN | 是 | TRUE | 是否需要实际输出 |
| expected_output_required | BOOLEAN | 是 | FALSE | 是否需要期望输出 |
| context_required | BOOLEAN | 是 | FALSE | 是否需要上下文 |
| retrieval_context_required | BOOLEAN | 是 | FALSE | 是否需要检索上下文 |
| embedding_required | BOOLEAN | 是 | FALSE | 是否需要嵌入模型 |
| llm_required | BOOLEAN | 是 | FALSE (内置) / TRUE (自定义) | 是否需要大语言模型 |
| created_at | TIMESTAMPTZ | 是 | NOW() | 创建时间 |
| updated_at | TIMESTAMPTZ | 是 | NOW() | 更新时间 |

**设计说明**：

1. **内置维度 vs 自定义维度**：
   - **内置维度（builtin）**：提示词硬编码在 diting-core 算法中，`prompt` 字段为 NULL
   - **自定义维度（custom）**：用户创建，`prompt` 字段可选（用户填写）

2. **用户创建维度**：
   - 只需三要素：`name`（必填）、`description`（可选）、`prompt`（可选）
   - `type` 自动设置为 `custom`
   - `llm_required` 自动设置为 `true`（自定义维度需要LLM执行评估）
   - 其他配置字段使用默认值

3. **权限控制**：
   - 内置维度不可修改、不可删除
   - 自定义维度可以编辑和删除（需要检查引用关系）

**内置指标示例数据**：
```sql
-- 插入内置评估指标（从 diting-core 同步）
-- 注意：内置维度的 prompt 为 NULL（在代码中定义）
INSERT INTO metrics (name, description, type, user_input_required, actual_output_required, expected_output_required, llm_required) VALUES
  ('answer_correctness', '评估生成答案的准确性和完整性', 'builtin', TRUE, TRUE, TRUE, TRUE),
  ('faithfulness', '衡量生成内容是否忠实于给定上下文', 'builtin', FALSE, TRUE, FALSE, TRUE),
  ('answer_relevancy', '评估答案与问题的相关程度', 'builtin', TRUE, TRUE, FALSE, TRUE),
  ('context_recall', '评估检索到的上下文覆盖度', 'builtin', FALSE, FALSE, TRUE, TRUE),
  ('context_precision', '评估检索到的上下文的精确性', 'builtin', FALSE, FALSE, FALSE, TRUE);
```

**自定义指标示例**：
```sql
-- 用户创建的自定义维度
INSERT INTO metrics (name, description, prompt, type) VALUES
  ('custom_accuracy', '自定义准确性评估', '请评估答案的准确性，给出 0-1 之间的分数', 'custom');
```

---

#### 2.2.5 evaluators (评估器表) 🆕

```sql
CREATE TABLE evaluators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    metric_ids UUID[] NOT NULL,
    config JSONB DEFAULT '{}',
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_evaluators_project ON evaluators(project_id);
CREATE INDEX idx_evaluators_creator ON evaluators(created_by);
CREATE INDEX idx_evaluators_created ON evaluators(created_at DESC);
CREATE INDEX idx_evaluators_last_used ON evaluators(last_used_at DESC);

-- GIN 索引（加速数组查询）
CREATE INDEX idx_evaluators_metric_ids ON evaluators USING GIN (metric_ids);

-- 注释
COMMENT ON TABLE evaluators IS '评估器表（组合多个评估维度）';
COMMENT ON COLUMN evaluators.metric_ids IS '包含的评估维度 ID 数组';
COMMENT ON COLUMN evaluators.config IS '评估器配置（如默认 LLM 配置）';
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | UUID | 是 | 主键 |
| name | VARCHAR(100) | 是 | 评估器名称 |
| description | TEXT | 否 | 描述 |
| project_id | UUID | 否 | 所属项目（NULL 表示全局评估器） |
| created_by | UUID | 是 | 创建者 ID（外键 → users.id） |
| metric_ids | UUID[] | 是 | 包含的评估维度 ID 数组 |
| config | JSONB | 否 | 评估器配置 |
| usage_count | INTEGER | 是 | 使用次数 |
| last_used_at | TIMESTAMPTZ | 否 | 最后使用时间 |
| created_at | TIMESTAMPTZ | 是 | 创建时间 |
| updated_at | TIMESTAMPTZ | 是 | 更新时间 |

**metric_ids 示例**：
```sql
-- 评估器包含 3 个指标
metric_ids = ARRAY[
  'uuid-of-answer-correctness'::UUID,
  'uuid-of-faithfulness'::UUID,
  'uuid-of-context-recall'::UUID
]
```

**config 字段结构** ⭐ 重要更新：

评估器的 `config` 字段采用 **JSONB** 类型，支持为不同维度配置不同的模型，实现成本优化和灵活性。

**完整配置示例**（按维度配置模型）：
```json
{
  "metric_model_configs": [
    {
      "metric_id": "uuid-of-answer-correctness",
      "llm_config": {
        "name": "gpt-4",
        "api_key": "sk-xxx",
        "base_url": "https://api.openai.com/v1",
        "parameters": {"temperature": 0.1},
        "timeout": 300
      }
    },
    {
      "metric_id": "uuid-of-answer-similarity",
      "embedding_config": {
        "name": "text-embedding-3-small",
        "api_key": "sk-xxx",
        "timeout": 300
      }
    },
    {
      "metric_id": "uuid-of-faithfulness",
      "llm_config": {
        "name": "gpt-3.5-turbo",
        "parameters": {"temperature": 0.0}
      }
    }
  ],
  "default_llm_config": {
    "name": "gpt-3.5-turbo",
    "api_key": "sk-xxx",
    "timeout": 300
  },
  "default_embedding_config": {
    "name": "text-embedding-ada-002",
    "api_key": "sk-xxx",
    "timeout": 300
  }
}
```

**简化配置示例**（全局统一模型）：
```json
{
  "default_llm_config": {
    "name": "gpt-3.5-turbo",
    "api_key": "sk-xxx"
  },
  "default_embedding_config": {
    "name": "text-embedding-ada-002",
    "api_key": "sk-xxx"
  }
}
```

**空配置示例**（向后兼容）：
```json
{}
```

**配置优先级**：
1. 维度专属配置（`metric_model_configs`）
2. 评估器默认配置（`default_llm_config`）
3. 任务级配置
4. 系统默认配置

---

#### 2.2.6 tasks (任务表) ⭐ 核心

```sql
-- 枚举类型
CREATE TYPE task_type AS ENUM ('evaluation', 'synthesis', 'batch_evaluation');
CREATE TYPE task_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled');

CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_type task_type NOT NULL,
    status task_status DEFAULT 'pending',
    
    -- 关联
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    dataset_id UUID REFERENCES datasets(id) ON DELETE SET NULL,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 任务配置
    config JSONB NOT NULL,
    input_data JSONB,
    
    -- 执行信息
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    job_id VARCHAR(100),  -- arq job ID
    worker_id VARCHAR(100),
    
    -- 结果
    result JSONB,
    error TEXT,
    
    -- 统计
    progress DECIMAL(5,2) DEFAULT 0.00,  -- 0.00 - 100.00
    total_tokens INTEGER DEFAULT 0,
    total_cost DECIMAL(10,4) DEFAULT 0.00,
    
    -- 元数据
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 约束
    CONSTRAINT chk_progress CHECK (progress >= 0 AND progress <= 100)
);

-- 索引
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_type ON tasks(task_type);
CREATE INDEX idx_tasks_project ON tasks(project_id);
CREATE INDEX idx_tasks_dataset ON tasks(dataset_id);
CREATE INDEX idx_tasks_creator ON tasks(created_by);
CREATE INDEX idx_tasks_created ON tasks(created_at DESC);
CREATE INDEX idx_tasks_status_created ON tasks(status, created_at DESC);

-- GIN 索引（加速 JSONB 查询）
CREATE INDEX idx_tasks_config ON tasks USING GIN (config);
CREATE INDEX idx_tasks_result ON tasks USING GIN (result);

-- 注释
COMMENT ON TABLE tasks IS '任务表（核心）';
COMMENT ON COLUMN tasks.config IS '任务配置（JSONB）';
COMMENT ON COLUMN tasks.result IS '任务结果（JSONB）';
COMMENT ON COLUMN tasks.progress IS '进度百分比 0-100';
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | UUID | 是 | 主键 |
| task_type | ENUM | 是 | evaluation, synthesis, batch_evaluation |
| status | ENUM | 是 | pending, running, completed, failed, cancelled |
| project_id | UUID | 否 | 所属项目 |
| dataset_id | UUID | 否 | 关联数据集（批量任务） |
| created_by | UUID | 是 | 创建者 |
| config | JSONB | 是 | 任务配置（LLM、指标等） |
| input_data | JSONB | 否 | 输入数据 |
| started_at | TIMESTAMPTZ | 否 | 开始时间 |
| completed_at | TIMESTAMPTZ | 否 | 完成时间 |
| job_id | VARCHAR(100) | 否 | arq job ID |
| worker_id | VARCHAR(100) | 否 | worker 标识 |
| result | JSONB | 否 | 结果数据 |
| error | TEXT | 否 | 错误信息 |
| progress | DECIMAL(5,2) | 是 | 进度 0-100 |
| total_tokens | INTEGER | 是 | 总 token 数 |
| total_cost | DECIMAL(10,4) | 是 | 总成本（美元） |
| metadata | JSONB | 否 | 元数据 |
| created_at | TIMESTAMPTZ | 是 | 创建时间 |
| updated_at | TIMESTAMPTZ | 是 | 更新时间 |

**config 示例（evaluation）**：
```json
{
  "llm_config": {
    "name": "gpt-4",
    "api_key": "sk-...",
    "base_url": "https://api.openai.com/v1",
    "parameters": {
      "temperature": 0.7,
      "max_tokens": 1000
    }
  },
  "metric_config": {
    "metric_name": "answer_relevancy",
    "metric_type": "builtin_metric"
  },
  "eval_case": {
    "user_input": "What is Python?",
    "actual_output": "Python is a programming language.",
    "context": ["Python is a high-level language..."]
  }
}
```

**result 示例**：
```json
{
  "metric_name": "answer_relevancy",
  "score": 0.95,
  "reason": "The answer is highly relevant...",
  "usages": [
    {
      "model_type": "llm",
      "prompt_tokens": 120,
      "completion_tokens": 30,
      "total_tokens": 150
    }
  ]
}
```

---

#### 2.2.7 evaluation_results (评估结果表)

```sql
CREATE TABLE evaluation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    
    -- 评估信息
    metric_name VARCHAR(50) NOT NULL,
    score DECIMAL(5,4),  -- 0.0000 - 1.0000
    reason TEXT,
    
    -- 输入数据
    user_input TEXT,
    actual_output TEXT,
    expected_output TEXT,
    context JSONB,  -- 数组
    retrieval_context JSONB,  -- 数组
    
    -- 执行详情
    run_logs JSONB,
    usages JSONB,
    
    -- 元数据
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_eval_task ON evaluation_results(task_id);
CREATE INDEX idx_eval_metric ON evaluation_results(metric_name);
CREATE INDEX idx_eval_score ON evaluation_results(score);
CREATE INDEX idx_eval_created ON evaluation_results(created_at DESC);

-- 全文搜索索引
CREATE INDEX idx_eval_reason_fts ON evaluation_results 
    USING GIN (to_tsvector('english', reason));

-- 注释
COMMENT ON TABLE evaluation_results IS '评估结果表';
COMMENT ON COLUMN evaluation_results.score IS '评估分数 0-1';
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | UUID | 是 | 主键 |
| task_id | UUID | 是 | 关联任务 |
| metric_name | VARCHAR(50) | 是 | 指标名称 |
| score | DECIMAL(5,4) | 否 | 分数 0-1 |
| reason | TEXT | 否 | 评估原因 |
| user_input | TEXT | 否 | 用户输入 |
| actual_output | TEXT | 否 | 实际输出 |
| expected_output | TEXT | 否 | 期望输出 |
| context | JSONB | 否 | 上下文（数组） |
| retrieval_context | JSONB | 否 | 检索上下文 |
| run_logs | JSONB | 否 | 运行日志 |
| usages | JSONB | 否 | Token 使用情况 |
| metadata | JSONB | 否 | 元数据 |
| created_at | TIMESTAMPTZ | 是 | 创建时间 |

---

#### 2.2.8 synthesis_results (合成结果表)

```sql
CREATE TABLE synthesis_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    
    -- 合成数据
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    
    -- 输入上下文
    source_context JSONB,
    
    -- 质量评分（可选）
    quality_score DECIMAL(5,4),
    
    -- 执行详情
    usages JSONB,
    
    -- 元数据
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_synth_task ON synthesis_results(task_id);
CREATE INDEX idx_synth_quality ON synthesis_results(quality_score);
CREATE INDEX idx_synth_created ON synthesis_results(created_at DESC);

-- 全文搜索
CREATE INDEX idx_synth_question_fts ON synthesis_results 
    USING GIN (to_tsvector('english', question));

-- 注释
COMMENT ON TABLE synthesis_results IS '合成结果表';
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | UUID | 是 | 主键 |
| task_id | UUID | 是 | 关联任务 |
| question | TEXT | 是 | 生成的问题 |
| answer | TEXT | 是 | 生成的答案 |
| source_context | JSONB | 否 | 源上下文 |
| quality_score | DECIMAL(5,4) | 否 | 质量分数 |
| usages | JSONB | 否 | Token 使用 |
| metadata | JSONB | 否 | 元数据 |
| created_at | TIMESTAMPTZ | 是 | 创建时间 |

---

#### 2.2.9 audit_logs (审计日志表)

```sql
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_created ON audit_logs(created_at DESC);

-- 分区（按月分区，可选）
-- CREATE TABLE audit_logs_2024_01 PARTITION OF audit_logs
--     FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- 注释
COMMENT ON TABLE audit_logs IS '审计日志表';
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | BIGSERIAL | 是 | 主键 |
| user_id | UUID | 否 | 用户 ID |
| action | VARCHAR(50) | 是 | 操作类型 |
| resource_type | VARCHAR(50) | 否 | 资源类型 |
| resource_id | UUID | 否 | 资源 ID |
| details | JSONB | 否 | 详细信息 |
| ip_address | INET | 否 | IP 地址 |
| user_agent | TEXT | 否 | User Agent |
| created_at | TIMESTAMPTZ | 是 | 创建时间 |

**action 示例**：
- `user.login`
- `user.logout`
- `project.create`
- `project.update`
- `project.delete`
- `task.create`
- `task.cancel`

---

## 3. API 设计

### 3.1 API 规范

#### 基础信息 (v1.0 - 单 Admin 模式)

- **Base URL**: `http://localhost:8000`
- **Content-Type**: `application/json`
- **认证方式**: 简化的 Admin 认证 (固定账户)

#### 统一响应格式

**成功响应**：
```json
{
  "code": 200,
  "msg": "success",
  "data": { /* 业务数据 */ }
}
```

**错误响应**：
```json
{
  "code": 400,
  "msg": "error",
  "error": "错误类型",
  "detail": "详细错误信息"
}
```

#### HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 500 | 服务器内部错误 |

---

### 3.2 健康检查 API 🆕

#### 3.2.1 健康检查

```http
GET /api/v1/healthz
```

**功能**: 检查服务健康状态

**无需认证**

**响应**：
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "version": "1.0.0",
    "status": "healthy",
    "timestamp": "2024-01-20T10:30:00Z"
  }
}
```

---

### 3.3 模型管理 API 🆕

#### 3.3.1 创建模型

```http
POST /api/v1/models
Authorization: Bearer <token>
```

**请求体**：
```json
{
  "name": "GPT-4",
  "model_type": "llm",
  "provider": "OpenAI",
  "model_name": "gpt-4",
  "api_key": "sk-xxx",
  "base_url": "https://api.openai.com/v1",
  "description": "OpenAI GPT-4 模型",
  "timeout": 60,
  "parameters": {
    "temperature": 0.7,
    "max_tokens": 2000
  },
  "is_default": true
}
```

**字段说明**：
- `name` (必填): 模型显示名称
- `model_type` (必填): 模型类型 (`llm` / `embedding`)
- `provider` (必填): 提供商
- `model_name` (必填): 实际调用的模型标识
- `api_key` (可选): API Key
- `base_url` (可选): 自定义 API 端点
- `description` (可选): 描述
- `timeout` (可选): 超时时间，默认 60 秒
- `parameters` (可选): 模型参数配置
- `is_default` (可选): 是否设为默认，默认 false

**响应**：
```json
{
  "code": 201,
  "msg": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "GPT-4",
    "model_type": "llm",
    "provider": "OpenAI",
    "model_name": "gpt-4",
    "api_key": "sk-xxx***",
    "base_url": "https://api.openai.com/v1",
    "description": "OpenAI GPT-4 模型",
    "timeout": 60,
    "parameters": {
      "temperature": 0.7,
      "max_tokens": 2000
    },
    "is_default": true,
    "usage_count": 0,
    "last_used_at": null,
    "created_at": "2024-01-20T10:30:00Z",
    "updated_at": "2024-01-20T10:30:00Z"
  }
}
```

**注意**：
- API Key 返回时会脱敏处理（只显示前几位和后几位）
- 如果设置为默认模型，会自动取消同类型的其他默认模型

---

#### 3.3.2 获取模型列表

```http
GET /api/v1/models?model_type=llm&page=1&page_size=20
Authorization: Bearer <token>
```

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| model_type | string | 否 | 类型筛选 (llm/embedding) |
| page | int | 否 | 页码（默认 1） |
| page_size | int | 否 | 每页数量（默认 20） |

**响应**：
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "items": [
      {
        "id": "model-uuid",
        "name": "GPT-4",
        "model_type": "llm",
        "provider": "OpenAI",
        "model_name": "gpt-4",
        "api_key": "sk-xxx***",
        "base_url": "https://api.openai.com/v1",
        "description": "OpenAI GPT-4 模型",
        "timeout": 60,
        "parameters": {
          "temperature": 0.7
        },
        "is_default": true,
        "usage_count": 128,
        "last_used_at": "2024-01-20T09:00:00Z",
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-20T10:30:00Z"
      }
    ],
    "total": 10,
    "page": 1,
    "page_size": 20,
    "pages": 1
  }
}
```

---

#### 3.3.3 获取单个模型

```http
GET /api/v1/models/{model_id}
Authorization: Bearer <token>
```

**响应**：同创建模型的响应格式

---

#### 3.3.4 更新模型

```http
PUT /api/v1/models/{model_id}
Authorization: Bearer <token>
```

**请求体**（所有字段可选）：
```json
{
  "name": "GPT-4 Turbo",
  "provider": "OpenAI",
  "model_name": "gpt-4-turbo",
  "api_key": "sk-new-key",
  "base_url": "https://api.openai.com/v1",
  "description": "更新后的描述",
  "timeout": 120,
  "parameters": {
    "temperature": 0.5
  },
  "is_default": false
}
```

**响应**：同创建模型的响应格式

**注意**：
- `model_type` 不可修改
- 如果修改 `is_default` 为 true，会自动取消同类型的其他默认模型

---

#### 3.3.5 删除模型

```http
DELETE /api/v1/models/{model_id}
Authorization: Bearer <token>
```

**响应**：
```json
{
  "code": 200,
  "msg": "删除成功"
}
```

**注意**：
- 删除默认模型前需要先设置其他模型为默认
- 可以添加检查：正在使用的模型不允许删除

---

#### 3.3.6 设置默认模型

```http
POST /api/v1/models/{model_id}/set-default
Authorization: Bearer <token>
```

**响应**：同获取单个模型的响应格式

**说明**：
- 自动取消同类型的其他默认模型
- 只能为同类型模型设置默认

---

### 3.4 简化认证 API 🆕

#### 3.4.1 Admin 登录

```http
POST /api/v1/auth/login
```

**请求体**：
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**响应**：
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 86400
  }
}
```

**说明**：
- 固定用户名: `admin`
- 密码通过环境变量 `ADMIN_PASSWORD` 设置
- Token 有效期: 24小时
- 无需注册功能，直接使用固定账户

---

### 3.4 评估维度管理 API 🆕

#### 3.4.1 创建自定义评估维度

```http
POST /api/v1/metrics
Authorization: Bearer <token>
```

**请求体**（仅需三要素）：
```json
{
  "name": "custom_accuracy",
  "description": "自定义准确性评估",
  "prompt": "请评估答案的准确性，给出 0-1 之间的分数"
}
```

**字段说明**：
- `name` (必填): 指标名称，全局唯一
- `description` (可选): 描述
- `prompt` (可选): 评估提示词（内置维度不需要）

**响应**：
```json
{
  "code": 201,
  "msg": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "custom_accuracy",
    "description": "自定义准确性评估",
    "type": "custom",
    "prompt": "请评估答案的准确性，给出 0-1 之间的分数",
    "user_input_required": false,
    "actual_output_required": true,
    "expected_output_required": false,
    "context_required": false,
    "retrieval_context_required": false,
    "embedding_required": false,
    "llm_required": false,
    "created_at": "2024-01-20T10:30:00Z",
    "updated_at": "2024-01-20T10:30:00Z"
  }
}
```

---

#### 3.4.2 获取评估维度列表

```http
GET /api/v1/metrics?metric_type=custom&page=1&page_size=20
Authorization: Bearer <token>
```

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| metric_type | string | 否 | 类型筛选 (builtin/custom) |
| page | int | 否 | 页码（默认 1） |
| page_size | int | 否 | 每页数量（默认 20） |

**响应**：
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "items": [
      {
        "id": "metric-uuid",
        "name": "answer_correctness",
        "description": "评估生成答案的准确性和完整性",
        "type": "builtin",
        "prompt": null,
        "user_input_required": true,
        "actual_output_required": true,
        "expected_output_required": true,
        "llm_required": true,
        "created_at": "2024-01-20T10:30:00Z",
        "updated_at": "2024-01-20T10:30:00Z"
      }
    ],
    "total": 10,
    "page": 1,
    "page_size": 20,
    "pages": 1
  }
}
```

---

#### 3.4.3 获取评估维度详情

```http
GET /api/v1/metrics/{metric_id}
Authorization: Bearer <token>
```

**响应**：返回单个 Metric 对象（格式同上）

---

#### 3.4.4 更新自定义评估维度

```http
PUT /api/v1/metrics/{metric_id}
Authorization: Bearer <token>
```

**请求体**：
```json
{
  "name": "updated_name",
  "description": "更新后的描述",
  "prompt": "更新后的提示词"
}
```

**注意**: 
- 仅自定义维度（type=custom）可修改
- 内置维度（type=builtin）不可修改
- 只能修改三要素：name, description, prompt

---

#### 3.4.5 删除自定义评估维度

```http
DELETE /api/v1/metrics/{metric_id}
Authorization: Bearer <token>
```

**响应**: 204 No Content

**注意**: 
- 仅自定义维度可删除
- 内置维度不可删除
- 被评估器引用的维度不可删除

---

### 3.7 评估器管理 API 🆕

#### 3.7.1 创建评估器

```http
POST /api/v1/evaluators
```

**请求体**：
```json
{
  "name": "QA 全面评估器",
  "description": "包含答案正确性、忠实度、上下文召回等维度",
  "project_id": "project-uuid",
  "metric_ids": [
    "metric-uuid-1",
    "metric-uuid-2",
    "metric-uuid-3"
  ],
  "config": {
    "default_llm": {
      "name": "gpt-4",
      "temperature": 0.7
    },
    "parallel_execution": true
  }
}
```

**响应**：
```json
{
  "code": 201,
  "msg": "success",
  "data": {
    "id": "evaluator-uuid",
    "name": "QA 全面评估器",
    "description": "包含答案正确性、忠实度、上下文召回等维度",
    "project_id": "project-uuid",
    "created_by": "user-uuid",
    "metric_ids": ["metric-uuid-1", "metric-uuid-2", "metric-uuid-3"],
    "config": {...},
    "usage_count": 0,
    "last_used_at": null,
    "created_at": "2024-01-20T10:30:00Z",
    "updated_at": "2024-01-20T10:30:00Z"
  }
}
```

---

#### 3.7.2 获取评估器列表

```http
GET /api/v1/evaluators?project_id=uuid&page=1
```

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_id | UUID | 否 | 项目 ID |
| page | int | 否 | 页码 |
| page_size | int | 否 | 每页数量 |

**响应**：
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "items": [
      {
        "id": "evaluator-uuid",
        "name": "QA 全面评估器",
        "metric_ids": ["uuid-1", "uuid-2"],
        "usage_count": 156,
        "last_used_at": "2024-01-20T10:30:00Z"
      }
    ],
    "total": 5,
    "page": 1,
    "page_size": 20
  }
}
```

---

#### 3.7.3 获取评估器详情

```http
GET /api/v1/evaluators/{evaluator_id}
```

---

#### 3.7.4 更新评估器

```http
PUT /api/v1/evaluators/{evaluator_id}
```

**请求体**：
```json
{
  "name": "更新后的名称",
  "description": "更新后的描述",
  "metric_ids": ["new-metric-uuid-1", "new-metric-uuid-2"]
}
```

---

#### 3.7.5 删除评估器

```http
DELETE /api/v1/evaluators/{evaluator_id}
```

**注意**: 删除前会检查是否有正在运行的任务使用该评估器

---

### 3.8 任务管理 API (核心)

#### 3.8.1 创建评估任务

```http
POST /api/v1/tasks/evaluations
```

**请求体**：
```json
{
  "project_id": "project-uuid",
  "llm_config": {
    "name": "gpt-4",
    "api_key": "sk-...",
    "base_url": "https://api.openai.com/v1",
    "parameters": {
      "temperature": 0.7,
      "max_tokens": 1000
    }
  },
  "embedding_config": {
    "name": "text-embedding-ada-002",
    "api_key": "sk-..."
  },
  "metric_config": {
    "metric_name": "answer_relevancy",
    "metric_type": "builtin_metric"
  },
  "eval_case": {
    "user_input": "What is Python?",
    "actual_output": "Python is a programming language.",
    "context": ["Python is a high-level language..."]
  }
}
```

**响应**：
```json
{
  "code": 201,
  "msg": "success",
  "data": {
    "task_id": "task-uuid",
    "status": "pending",
    "created_at": "2024-01-20T10:30:00Z",
    "estimated_time": 30
  }
}
```

---

#### 3.8.2 创建合成任务

```http
POST /api/v1/tasks/synthesis
```

**请求体**：
```json
{
  "project_id": "project-uuid",
  "llm_config": {
    "name": "gpt-4",
    "api_key": "sk-..."
  },
  "synthesizer_config": {
    "synthesizer_name": "qa_synthesizer",
    "config": {
      "num_questions": 5
    }
  },
  "input_data": {
    "context": ["Python is a programming language..."],
    "themes": ["Python basics"]
  }
}
```

---

#### 3.8.3 创建批量评估任务

```http
POST /api/v1/tasks/batch-evaluations
```

**请求体**：
```json
{
  "project_id": "project-uuid",
  "dataset_id": "dataset-uuid",
  "evaluator_id": "evaluator-uuid",  // 🆕 新增:使用评估器
  "llm_config": {...},
  "embedding_config": {...}
}
```

**或者** (单指标批量评估):
```json
{
  "project_id": "project-uuid",
  "dataset_id": "dataset-uuid",
  "metric_config": {...},  // 单个指标
  "llm_config": {...}
}
```

**说明**:
- `evaluator_id` 和 `metric_config` 二选一,不能同时提供
- 使用 `evaluator_id` 时,会为评估器中的每个指标创建子任务

---

#### 3.8.4 获取任务状态

```http
GET /api/v1/tasks/{task_id}
```

**响应**：
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "id": "task-uuid",
    "task_type": "evaluation",
    "status": "completed",
    "progress": 100.0,
    "started_at": "2024-01-20T10:30:05Z",
    "completed_at": "2024-01-20T10:30:35Z",
    "result": {
      "metric_name": "answer_relevancy",
      "score": 0.95,
      "reason": "..."
    },
    "total_tokens": 150,
    "total_cost": 0.0045
  }
}
```

---

#### 3.8.5 获取任务列表

```http
GET /api/v1/tasks?project_id=uuid&status=completed&page=1
```

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_id | UUID | 否 | 项目 ID |
| task_type | string | 否 | 任务类型 |
| status | string | 否 | 任务状态 |
| page | int | 否 | 页码 |
| page_size | int | 否 | 每页数量 |

---

#### 3.8.6 取消任务

```http
POST /api/v1/tasks/{task_id}/cancel
```

---

#### 3.8.7 获取合成结果列表 🆕

```http
GET /api/v1/tasks/{task_id}/synthesis-results
Authorization: Bearer <token>
```

**功能**: 获取指定合成任务的所有结果

**响应**：
```json
{
  "code": 200,
  "msg": "success",
  "data": [
    {
      "id": "result-uuid",
      "task_id": "task-uuid",
      "question": "生成的问题",
      "answer": "生成的答案",
      "source_context": ["上下文1", "上下文2"],
      "quality_score": 0.95,
      "usages": [
        {
          "model_type": "llm",
          "prompt_tokens": 120,
          "completion_tokens": 30,
          "total_tokens": 150
        }
      ],
      "created_at": "2024-01-20T10:30:00Z"
    }
  ]
}
```

**说明**：
- 仅适用于 `task_type=synthesis` 的任务
- 返回该任务的所有合成结果
- 结果按创建时间升序排列

---

#### 3.8.8 导出合成结果 🆕

```http
GET /api/v1/tasks/{task_id}/synthesis-results/export?format=csv
Authorization: Bearer <token>
```

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| format | string | 否 | 导出格式：csv 或 jsonl（默认 csv） |

**响应**：
- 直接返回文件流
- Content-Type: `text/csv; charset=utf-8` 或 `application/x-ndjson`
- Content-Disposition: `attachment; filename="synthesis_results_{task_id}.csv"`

**功能说明**：
- 导出指定任务的合成结果
- CSV 格式包含 UTF-8 BOM，兼容 Excel
- JSONL 格式每行一个 JSON 对象

**CSV 格式字段**：
- question（问题）
- answer（答案）
- source_context（源上下文，JSON 字符串）
- quality_score（质量分数）
- created_at（创建时间）

---

#### 3.8.9 从合成结果创建数据集 🆕

```http
POST /api/v1/tasks/{task_id}/synthesis-results/create-dataset
Authorization: Bearer <token>
```

**请求体**：
```json
{
  "name": "合成数据集_2024-01-20",
  "description": "从合成任务生成的QA数据集"
}
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 数据集名称 |
| description | string | 否 | 数据集描述 |

**响应**：
```json
{
  "code": 201,
  "msg": "success",
  "data": {
    "id": "dataset-uuid",
    "name": "合成数据集_2024-01-20",
    "description": "从合成任务生成的QA数据集",
    "file_path": null,
    "file_size": null,
    "file_type": null,
    "row_count": 50,
    "columns": {
      "columns": ["question", "answer", "source_context", "quality_score"]
    },
    "metadata": {
      "column_count": 4,
      "data_types": {
        "question": "string",
        "answer": "string",
        "source_context": "string",
        "quality_score": "float"
      },
      "source": "synthesis_results"
    },
    "created_at": "2024-01-20T10:30:00Z",
    "updated_at": "2024-01-20T10:30:00Z"
  }
}
```

**功能说明**：
- 将合成任务的结果转换为数据集
- 自动创建数据集记录并插入所有数据行
- 数据集标记为 `source: "synthesis_results"`
- 数据集可在数据集管理模块中进一步编辑和管理

**错误处理**：
- 如果任务不存在或不是合成任务，返回 404 或 400
- 如果任务没有合成结果，返回 400 错误

---

### 3.9 结果查询 API

#### 3.9.1 获取评估结果列表

```http
GET /api/v1/results/evaluations?project_id=uuid&metric=answer_relevancy
```

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_id | UUID | 否 | 项目 ID |
| metric_name | string | 否 | 指标名称 |
| min_score | float | 否 | 最小分数 |
| max_score | float | 否 | 最大分数 |
| page | int | 否 | 页码 |

**响应**：
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "items": [
      {
        "id": "uuid",
        "task_id": "task-uuid",
        "metric_name": "answer_relevancy",
        "score": 0.95,
        "reason": "...",
        "created_at": "2024-01-20T10:30:00Z"
      }
    ],
    "total": 50,
    "page": 1,
    "page_size": 20
  }
}
```

---

#### 3.9.2 获取合成结果列表

```http
GET /api/v1/results/synthesis?project_id=uuid
```

**说明**：
- 此接口用于按项目查询所有合成结果（全局查询）
- 如需查询特定任务的合成结果，请使用 `GET /api/v1/tasks/{task_id}/synthesis-results`（见 3.8.7）
- **新增使用场景**：数据集导入模式可以从数据集预览接口获取数据用于合成任务

---

#### 3.8.2 创建合成任务

**新增功能**: 支持从数据集导入数据

```http
POST /api/v1/tasks/synthesis
```

**请求体**（手动输入模式）：
```json
{
  "project_id": "project-uuid",
  "llm_config": {
    "name": "gpt-4",
    "api_key": "sk-..."
  },
  "synthesizer_config": {
    "synthesizer_name": "qa_synthesizer",
    "config": {
      "num_questions": 5
    }
  },
  "input_data": {
    "context": ["Python is a programming language..."],
    "themes": ["Python basics"]
  }
}
```

**请求体**（从数据集导入模式）：
```json
{
  "project_id": "project-uuid",
  "llm_config": {
    "name": "gpt-4",
    "api_key": "sk-..."
  },
  "synthesizer_config": {
    "synthesizer_name": "qa_synthesizer"
  },
  "input_data": {
    "context": ["从数据集字段提取的上下文1", "上下文2", ...],
    "themes": ["主题1, 主题2, 主题3"]
  }
}
```

**新增功能说明**：
- 前端支持两种输入模式：
  1. **手动输入模式**：用户直接输入主题和上下文
  2. **数据集导入模式**：从已有数据集选择数据，通过字段映射自动填充主题和上下文
- 数据集导入模式使用现有的数据集预览API (`GET /api/v1/datasets/{dataset_id}/preview`) 获取数据
- 字段映射由前端完成，后端无需改动
- 无论哪种模式，最终提交给后端的请求格式相同

---

#### 3.9.3 导出结果

```http
POST /api/v1/results/export
```

**请求体**：
```json
{
  "project_id": "uuid",
  "format": "csv",
  "filters": {
    "metric_name": "answer_relevancy",
    "min_score": 0.8
  }
}
```

**响应**：
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "download_url": "https://minio.../export_uuid.csv",
    "expires_at": "2024-01-20T11:30:00Z"
  }
}
```

**说明**：
- 此接口用于导出评估结果（支持过滤）
- 如需导出特定任务的合成结果，请使用 `GET /api/v1/tasks/{task_id}/synthesis-results/export`（见 3.8.8）

---

### 3.10 数据集管理 API

#### 3.10.1 上传数据集

```http
POST /api/v1/datasets
Content-Type: multipart/form-data
```

**表单数据**：
```
file: <文件>
project_id: uuid
name: My Dataset
description: 测试数据集
```

---

#### 3.10.2 获取数据集列表

```http
GET /api/v1/datasets?project_id=uuid
```

---

#### 3.10.3 删除数据集

```http
DELETE /api/v1/datasets/{dataset_id}
```

---

#### 3.10.4 获取数据集详情

```http
GET /api/v1/datasets/{dataset_id}
Authorization: Bearer <token>
```

**响应**：
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "id": "dataset-uuid",
    "name": "My Dataset",
    "description": "测试数据集",
    "project_id": "project-uuid",
    "file_path": "datasets/dataset-uuid/data.csv",
    "file_size": 1024,
    "row_count": 100,
    "column_count": 5,
    "metadata": {
      "annotation_columns": [
        {
          "column_name": "情感标注",
          "column_type": "category",
          "description": "情感分类标注",
          "options": ["正面", "负面", "中性"]
        }
      ]
    },
    "created_at": "2024-01-20T10:30:00Z",
    "updated_at": "2024-01-20T10:30:00Z"
  }
}
```

---

#### 3.10.5 预览数据集数据

```http
GET /api/v1/datasets/{dataset_id}/preview?page=1&page_size=10&search=keyword
Authorization: Bearer <token>
```

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 页码（默认 1） |
| page_size | int | 否 | 每页数量（默认 10） |
| search | string | 否 | 搜索关键词（在所有列中搜索） |

**响应**：
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "columns": ["user_input", "expected_output", "情感标注"],
    "data_types": {
      "user_input": "object",
      "expected_output": "object",
      "情感标注": "object"
    },
    "preview_data": [
      {
        "user_input": "世界最高峰是什么",
        "expected_output": "珠穆朗玛峰",
        "情感标注": "中性"
      }
    ],
    "total": 100,
    "page": 1,
    "page_size": 10,
    "pages": 10
  }
}
```

**功能说明**：
- 支持分页查询数据集内容（从 dataset_rows 表查询）
- 支持全文搜索（在数据库层面使用 JSONB 查询，性能更好）
- 返回列信息、数据类型和实际数据
- 包含标注列的数据

**搜索实现**：
- 使用 PostgreSQL JSONB 查询功能，在数据库层面过滤数据
- 支持在所有列的值（value）和列名（key）中搜索关键词
- 自动处理嵌套 JSON 结构（数组、对象等）转换为文本后搜索
- 性能优化：使用 GIN 索引加速查询

---

#### 3.10.6 更新数据集数据

```http
PUT /api/v1/datasets/{dataset_id}/data
Authorization: Bearer <token>
Content-Type: application/json
```

**请求体**：
```json
{
  "preview_data": [
    {
      "user_input": "世界最高峰是什么",
      "expected_output": "珠穆朗玛峰",
      "情感标注": "中性"
    }
  ],
  "row_count": 100
}
```

**响应**：
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "id": "dataset-uuid",
    "name": "My Dataset",
    "row_count": 100,
    "updated_at": "2024-01-20T10:30:00Z"
  }
}
```

**功能说明**：
- 更新数据集的数据行（更新 dataset_rows 表中的记录）
- 支持更新原始列和标注列的数据
- 直接更新单条记录，性能高效
- 自动更新 row_count 和 updated_at 字段

---

#### 3.10.7 添加标注列 🆕

```http
POST /api/v1/datasets/{dataset_id}/annotations/columns
Authorization: Bearer <token>
Content-Type: application/json
```

**请求体**：
```json
{
  "column_name": "情感标注",
  "column_type": "category",
  "description": "情感分类标注",
  "options": ["正面", "负面", "中性"]
}
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| column_name | string | 是 | 标注列名称（1-100字符） |
| column_type | string | 否 | 列类型：text/number/category/boolean（默认text） |
| description | string | 否 | 列描述说明 |
| options | array | 否 | 分类选项（仅category类型需要） |

**响应**：
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "id": "dataset-uuid",
    "name": "My Dataset",
    "metadata": {
      "annotation_columns": [
        {
          "column_name": "情感标注",
          "column_type": "category",
          "description": "情感分类标注",
          "options": ["正面", "负面", "中性"]
        }
      ]
    },
    "updated_at": "2024-01-20T10:30:00Z"
  }
}
```

**功能说明**：
- 为数据集添加标注列
- 自动在所有 dataset_rows 记录中初始化该列（值为空字符串）
- 标注列信息存储在 `metadata.annotation_columns` 中
- 支持多种列类型（文本、数字、分类、布尔值）

**错误处理**：
- 如果列名已存在，返回 400 错误
- 列名不能与原始数据列重名

---

#### 3.10.8 删除标注列 🆕

```http
DELETE /api/v1/datasets/{dataset_id}/annotations/columns
Authorization: Bearer <token>
Content-Type: application/json
```

**请求体**：
```json
{
  "column_name": "情感标注"
}
```

**响应**：
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "id": "dataset-uuid",
    "name": "My Dataset",
    "metadata": {
      "annotation_columns": []
    },
    "updated_at": "2024-01-20T10:30:00Z"
  }
}
```

**功能说明**：
- 删除指定的标注列
- 从 `metadata.annotation_columns` 中移除列信息
- 从所有 dataset_rows 记录中删除该列的数据（使用 JSONB 操作）
- 只能删除标注列，不能删除原始数据列

**错误处理**：
- 如果列不存在，返回 404 错误
- 如果尝试删除原始数据列，返回 400 错误

---

#### 3.10.9 下载原始文件 🆕

```http
GET /api/v1/datasets/{dataset_id}/download/original
Authorization: Bearer <token>
```

**响应**：
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "download_url": "https://minio.example.com/presigned-url..."
  }
}
```

**功能说明**：
- 返回MinIO中原始文件的预签名下载URL
- URL有效期通常为1小时
- 文件是上传时的原始文件，不包含后续的编辑

---

#### 3.10.10 导出数据集 🆕

```http
GET /api/v1/datasets/{dataset_id}/export
Authorization: Bearer <token>
```

**响应**：
- 直接返回文件流（CSV或JSONL格式）
- Content-Type: `text/csv` 或 `application/jsonl`
- Content-Disposition: `attachment; filename="dataset_name_exported.csv"`

**功能说明**：
- 导出PostgreSQL中的当前数据
- **包含所有编辑的数据和新增的列**
- 自动根据原始文件类型选择导出格式（CSV/JSONL）
- 文件名自动添加 `_exported` 后缀

**使用场景**：
- 导出已标注完成的数据集
- 导出包含新增列的完整数据
- 获取最新的编辑结果

---

### 3.11 统计 API 🆕

#### 3.11.1 获取 Dashboard 统计

```http
GET /api/v1/statistics/dashboard
```

**功能**: 获取仪表板展示的统计数据

**响应**：
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "total_tasks": 100,
    "completed_tasks": 85,
    "failed_tasks": 5,
    "success_rate": 0.85,
    "total_tokens": 150000,
    "total_cost": 45.00,
    "average_score": 0.85,
    "recent_tasks": [
      {
        "id": "task-uuid",
        "task_type": "evaluation",
        "status": "completed",
        "created_at": "2024-01-20T10:30:00Z"
      }
    ]
  }
}
```

---

#### 3.11.2 获取项目统计

```http
GET /api/v1/statistics/projects/{project_id}
```

**响应**：
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "total_tasks": 100,
    "completed_tasks": 85,
    "failed_tasks": 5,
    "total_tokens": 150000,
    "total_cost": 45.00,
    "average_score": 0.85,
    "metrics_distribution": {
      "answer_relevancy": 50,
      "faithfulness": 30,
      "answer_correctness": 20
    }
  }
}
```

---

#### 3.11.3 获取指标统计

```http
GET /api/v1/statistics/metrics?metric_name=answer_relevancy&period=7d
```

**响应**：
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "metric_name": "answer_relevancy",
    "period": "7d",
    "total_count": 500,
    "average_score": 0.85,
    "min_score": 0.20,
    "max_score": 1.00,
    "trend": [
      {"date": "2024-01-14", "avg_score": 0.82, "count": 50},
      {"date": "2024-01-15", "avg_score": 0.84, "count": 60},
      ...
    ]
  }
}
```

---

## 4. 数据结构 Schema

### 4.1 Pydantic 模型

#### 4.1.1 用户相关

```python
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional
from uuid import UUID

class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=100)

class UserCreate(UserBase):
    """用户创建"""
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    """用户更新"""
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None

class UserResponse(UserBase):
    """用户响应"""
    id: UUID
    avatar_url: Optional[str]
    is_active: bool
    is_superuser: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}

class Token(BaseModel):
    """Token 响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
```

---

#### 4.1.2 项目相关

```python
class ProjectBase(BaseModel):
    """项目基础模型"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    is_public: bool = False
    settings: dict = Field(default_factory=dict)

class ProjectCreate(ProjectBase):
    """项目创建"""
    pass

class ProjectUpdate(BaseModel):
    """项目更新"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_public: Optional[bool] = None
    settings: Optional[dict] = None

class ProjectResponse(ProjectBase):
    """项目响应"""
    id: UUID
    owner_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}
```

---

#### 4.1.3 评估维度相关 🆕

```python
from enum import Enum

class MetricTypeEnum(str, Enum):
    """指标类型"""
    BUILTIN = "builtin"  # 内置类型
    CUSTOM = "custom"    # 自定义类型

class MetricCreate(BaseModel):
    """评估维度创建 - 用户只需三要素"""
    name: str = Field(..., min_length=1, max_length=100, description="指标名称")
    description: Optional[str] = Field(None, description="描述")
    prompt: Optional[str] = Field(None, description="提示词")
    # type 自动设置为 CUSTOM
    # 其他配置字段使用数据库默认值

class MetricUpdate(BaseModel):
    """评估维度更新 - 仅能修改三要素"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    prompt: Optional[str] = None
    # type 和其他配置字段不允许修改

class MetricResponse(BaseModel):
    """评估维度响应"""
    id: UUID
    name: str
    description: Optional[str]
    type: MetricTypeEnum
    prompt: Optional[str]
    # 必需项配置
    user_input_required: bool
    actual_output_required: bool
    expected_output_required: bool
    context_required: bool
    retrieval_context_required: bool
    # 模型依赖
    embedding_required: bool
    llm_required: bool
    # 时间戳
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}
```

**设计说明**：

1. **创建简化**：用户创建自定义维度只需填写 3 个字段
   - `name`: 必填
   - `description`: 可选
   - `prompt`: 可选

2. **类型自动设置**：
   - 用户创建的维度自动设为 `custom`
   - 系统预置的维度为 `builtin`

3. **提示词存储**：
   - 内置维度：`prompt` 为 NULL（硬编码在算法中）
   - 自定义维度：`prompt` 可选（用户填写）

4. **权限控制**：
   - 内置维度：不可修改、不可删除
   - 自定义维度：可修改、可删除（需检查引用）
```

---

#### 4.1.4 评估器相关 🆕

```python
from typing import Any, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

# ===== 模型配置相关 =====

class ModelConfig(BaseModel):
    """模型配置（LLM 或 Embedding）"""
    name: str = Field(..., description="模型名称，如 gpt-4, gpt-3.5-turbo, text-embedding-ada-002")
    api_key: Optional[str] = Field(None, description="API密钥")
    base_url: Optional[str] = Field(None, description="API基础URL")
    parameters: dict[str, Any] = Field(default_factory=dict, description="模型参数（如 temperature, max_tokens）")
    timeout: int = Field(default=300, description="请求超时时间（秒）")

class MetricModelConfig(BaseModel):
    """单个维度的模型配置"""
    metric_id: UUID = Field(..., description="维度ID")
    llm_config: Optional[ModelConfig] = Field(None, description="该维度使用的LLM配置")
    embedding_config: Optional[ModelConfig] = Field(None, description="该维度使用的Embedding配置")

class EvaluatorConfig(BaseModel):
    """评估器配置结构 ⭐ 核心"""
    metric_model_configs: list[MetricModelConfig] = Field(
        default_factory=list,
        description="每个维度的独立模型配置列表（支持为不同维度配置不同模型）"
    )
    default_llm_config: Optional[ModelConfig] = Field(
        None,
        description="默认LLM配置（未在 metric_model_configs 中配置的维度将使用此默认值）"
    )
    default_embedding_config: Optional[ModelConfig] = Field(
        None,
        description="默认Embedding配置（未在 metric_model_configs 中配置的维度将使用此默认值）"
    )

# ===== 评估器 CRUD Schema =====

class EvaluatorBase(BaseModel):
    """评估器基础模型"""
    name: str = Field(..., min_length=1, max_length=100, description="评估器名称")
    description: Optional[str] = Field(None, description="评估器描述")
    metric_ids: list[UUID] = Field(..., min_items=1, description="包含的评估维度ID列表")
    config: EvaluatorConfig = Field(
        default_factory=EvaluatorConfig,
        description="评估器配置（支持按维度配置不同模型）"
    )
    
    @field_validator("config", mode="before")
    @classmethod
    def parse_config(cls, v: Any) -> EvaluatorConfig:
        """从 dict 或 EvaluatorConfig 解析配置"""
        if isinstance(v, dict):
            return EvaluatorConfig(**v)
        return v

class EvaluatorCreate(EvaluatorBase):
    """评估器创建"""
    pass

class EvaluatorUpdate(BaseModel):
    """评估器更新"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    metric_ids: Optional[list[UUID]] = Field(None, min_items=1)
    config: Optional[EvaluatorConfig] = None
    
    @field_validator("config", mode="before")
    @classmethod
    def parse_config(cls, v: Any) -> Optional[EvaluatorConfig]:
        """从 dict 或 EvaluatorConfig 解析配置"""
        if v is None:
            return None
        if isinstance(v, dict):
            return EvaluatorConfig(**v)
        return v

class EvaluatorResponse(EvaluatorBase):
    """评估器响应"""
    id: UUID
    created_by: UUID
    usage_count: int
    last_used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}
```

**设计亮点**：

1. **灵活的模型配置**：
   - ✅ 支持为每个维度配置不同的模型（成本优化）
   - ✅ 支持全局默认配置（简化使用）
   - ✅ 向后兼容空配置 `{}`

2. **配置优先级**：
   ```python
   # 伪代码：获取维度的模型配置
   def get_model_for_metric(metric, evaluator):
       # 1. 优先使用维度专属配置
       for config in evaluator.config.metric_model_configs:
           if config.metric_id == metric.id:
               return config.llm_config or config.embedding_config
       
       # 2. 使用评估器默认配置
       if evaluator.config.default_llm_config:
           return evaluator.config.default_llm_config
       
       # 3. 使用系统默认（兜底）
       return system_default
   ```

3. **使用场景**：
   - 🎯 **成本优化**：核心维度用 GPT-4，其他用 GPT-3.5
   - 🎯 **多模型组合**：代码评估用 GPT-4，创意评估用 Claude
   - 🎯 **简化配置**：统一使用默认模型（适合 90% 用户）

**实际配置示例**：

##### 场景1：成本优化评估器
```json
{
  "name": "成本优化评估器",
  "description": "核心指标用 GPT-4，其他用 GPT-3.5 降低成本",
  "metric_ids": [
    "uuid-answer-correctness",
    "uuid-faithfulness", 
    "uuid-answer-relevancy"
  ],
  "config": {
    "metric_model_configs": [
      {
        "metric_id": "uuid-answer-correctness",
        "llm_config": {
          "name": "gpt-4",
          "parameters": {"temperature": 0.1}
        }
      },
      {
        "metric_id": "uuid-faithfulness",
        "llm_config": {
          "name": "gpt-3.5-turbo",
          "parameters": {"temperature": 0.0}
        }
      },
      {
        "metric_id": "uuid-answer-relevancy",
        "llm_config": {
          "name": "gpt-3.5-turbo",
          "parameters": {"temperature": 0.0}
        }
      }
    ]
  }
}
```
**成本节省**：相比全部使用 GPT-4，节省约 **60% 成本** 💰

##### 场景2：多模型组合评估器
```json
{
  "name": "多模型专家评估器",
  "description": "针对不同任务使用最擅长的模型",
  "metric_ids": [
    "uuid-code-quality",
    "uuid-creative-writing",
    "uuid-logic-reasoning"
  ],
  "config": {
    "metric_model_configs": [
      {
        "metric_id": "uuid-code-quality",
        "llm_config": {"name": "gpt-4"}
      },
      {
        "metric_id": "uuid-creative-writing",
        "llm_config": {"name": "claude-3-opus"}
      },
      {
        "metric_id": "uuid-logic-reasoning",
        "llm_config": {"name": "gpt-4-turbo"}
      }
    ]
  }
}
```
**优势**：每个维度使用最适合的模型，效果最优 🎯

##### 场景3：简化配置（推荐新手）
```json
{
  "name": "标准评估器",
  "description": "使用统一模型，配置简单",
  "metric_ids": [
    "uuid-answer-correctness",
    "uuid-faithfulness",
    "uuid-answer-relevancy"
  ],
  "config": {
    "default_llm_config": {
      "name": "gpt-3.5-turbo",
      "api_key": "sk-xxx"
    }
  }
}
```
**优势**：配置简单，适合 90% 的常规场景 ✨

##### 场景4：向后兼容（空配置）
```json
{
  "name": "旧版评估器",
  "metric_ids": ["uuid-1", "uuid-2"],
  "config": {}
}
```
**说明**：空配置时，使用任务级或系统默认配置，完全向后兼容 ✅

---

#### 4.1.5 任务相关

```python
from enum import Enum
from typing import Any

class TaskType(str, Enum):
    """任务类型"""
    EVALUATION = "evaluation"
    SYNTHESIS = "synthesis"
    BATCH_EVALUATION = "batch_evaluation"

class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ModelConfig(BaseModel):
    """模型配置"""
    name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    parameters: dict = Field(default_factory=dict)
    timeout: int = 300

class MetricConfig(BaseModel):
    """指标配置"""
    metric_name: str
    metric_type: str  # builtin_metric or custom_metric
    prompt: Optional[str] = None

class EvalCase(BaseModel):
    """评估样本"""
    user_input: Optional[str] = None
    actual_output: Optional[str] = None
    expected_output: Optional[str] = None
    context: Optional[list[str]] = None
    retrieval_context: Optional[list[str]] = None
    metadata: dict = Field(default_factory=dict)

class CreateEvaluationTaskRequest(BaseModel):
    """创建评估任务请求"""
    project_id: Optional[UUID] = None
    llm_config: Optional[ModelConfig] = None
    embedding_config: Optional[ModelConfig] = None
    metric_config: MetricConfig
    eval_case: EvalCase

class SynthesizerConfig(BaseModel):
    """合成器配置"""
    synthesizer_name: str
    config: dict = Field(default_factory=dict)

class InputData(BaseModel):
    """输入数据"""
    context: Optional[list[str]] = None
    themes: Optional[list[str]] = None

class CreateSynthesisTaskRequest(BaseModel):
    """创建合成任务请求"""
    project_id: Optional[UUID] = None
    llm_config: ModelConfig
    embedding_config: Optional[ModelConfig] = None
    synthesizer_config: SynthesizerConfig
    input_data: InputData
    metadata: dict = Field(default_factory=dict)

class TaskResponse(BaseModel):
    """任务响应"""
    id: UUID
    task_type: TaskType
    status: TaskStatus
    progress: float
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Optional[dict]
    error: Optional[str]
    total_tokens: int
    total_cost: float
    created_at: datetime
    
    model_config = {"from_attributes": True}
```

---

#### 4.1.6 结果相关

```python
class EvaluationResultResponse(BaseModel):
    """评估结果响应"""
    id: UUID
    task_id: UUID
    metric_name: str
    score: Optional[float]
    reason: Optional[str]
    user_input: Optional[str]
    actual_output: Optional[str]
    expected_output: Optional[str]
    context: Optional[list[str]]
    usages: Optional[list[dict]]
    created_at: datetime
    
    model_config = {"from_attributes": True}

class SynthesisResultResponse(BaseModel):
    """合成结果响应"""
    id: UUID
    task_id: UUID
    question: str
    answer: str
    source_context: Optional[list[str]]
    quality_score: Optional[float]
    usages: Optional[list[dict]]
    created_at: datetime
    
    model_config = {"from_attributes": True}


class CreateDatasetFromSynthesisRequest(BaseModel):
    """从合成结果创建数据集请求 🆕"""
    name: str = Field(..., min_length=1, max_length=100, description="数据集名称")
    description: Optional[str] = Field(None, description="数据集描述")
```

---

#### 4.1.7 分页

```python
from typing import Generic, TypeVar

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int
```

---

#### 4.1.8 数据集相关 🆕

```python
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

class AnnotationColumn(BaseModel):
    """标注列定义"""
    column_name: str = Field(..., description="标注列名称")
    column_type: str = Field(default="text", description="列类型：text/number/category/boolean")
    description: Optional[str] = Field(None, description="列描述")
    options: Optional[list[str]] = Field(None, description="分类选项（仅category类型）")

class AnnotationColumnCreate(BaseModel):
    """创建标注列"""
    column_name: str = Field(..., min_length=1, max_length=100, description="标注列名称")
    column_type: str = Field(default="text", description="列类型：text/number/category/boolean")
    description: Optional[str] = Field(None, description="列描述")
    options: Optional[list[str]] = Field(None, description="分类选项（仅category类型）")

class AnnotationColumnDelete(BaseModel):
    """删除标注列"""
    column_name: str = Field(..., description="要删除的标注列名称")

class DatasetResponse(BaseModel):
    """数据集响应"""
    id: UUID
    name: str
    description: Optional[str]
    project_id: Optional[UUID]
    file_path: str
    file_size: int
    row_count: int
    column_count: int
    metadata: dict  # 包含 annotation_columns 等元数据
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

class DatasetPreviewResponse(BaseModel):
    """数据集预览响应"""
    columns: list[str] = Field(..., description="所有列名（包含原始列和标注列）")
    data_types: dict[str, str] = Field(..., description="列的数据类型映射")
    preview_data: list[dict] = Field(..., description="预览数据（包含所有列的数据）")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页记录数")
    pages: int = Field(..., description="总页数")

class DatasetDataUpdate(BaseModel):
    """更新数据集数据"""
    preview_data: list[dict] = Field(..., description="更新后的预览数据")
    row_count: Optional[int] = Field(None, description="更新后的总行数")
```

**功能说明**：

1. **标注列管理**：
   - `AnnotationColumn`: 标注列的完整定义，存储在数据集 metadata 中
   - `AnnotationColumnCreate`: 创建标注列的请求体
   - `AnnotationColumnDelete`: 删除标注列的请求体

2. **数据集查询**：
   - `DatasetResponse`: 数据集基本信息响应
   - `DatasetPreviewResponse`: 数据集预览数据响应，支持分页和搜索

3. **数据集更新**：
   - `DatasetDataUpdate`: 更新数据集数据的请求体

4. **元数据结构**：
   ```python
   # dataset.metadata 结构示例
   {
       "annotation_columns": [
           {
               "column_name": "情感标注",
               "column_type": "category",
               "description": "情感分类标注",
               "options": ["正面", "负面", "中性"]
           }
       ]
   }
   ```

---

### 4.2 SQLAlchemy 模型示例

```python
from sqlalchemy import Column, String, Boolean, ForeignKey, Text, DECIMAL, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM, TIMESTAMPTZ
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import uuid
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    avatar_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(TIMESTAMPTZ, default=datetime.utcnow)
    updated_at = Column(TIMESTAMPTZ, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(TIMESTAMPTZ)
    
    # 关系
    projects = relationship("Project", back_populates="owner")
    tasks = relationship("Task", back_populates="creator")

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    settings = Column(JSONB, default={})
    is_public = Column(Boolean, default=False)
    created_at = Column(TIMESTAMPTZ, default=datetime.utcnow)
    updated_at = Column(TIMESTAMPTZ, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    owner = relationship("User", back_populates="projects")
    tasks = relationship("Task", back_populates="project")
    datasets = relationship("Dataset", back_populates="project")

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_type = Column(ENUM("evaluation", "synthesis", "batch_evaluation", name="task_type"), nullable=False)
    status = Column(ENUM("pending", "running", "completed", "failed", "cancelled", name="task_status"), default="pending")
    
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"))
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="SET NULL"))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    config = Column(JSONB, nullable=False)
    input_data = Column(JSONB)
    
    started_at = Column(TIMESTAMPTZ)
    completed_at = Column(TIMESTAMPTZ)
    job_id = Column(String(100))
    worker_id = Column(String(100))
    
    result = Column(JSONB)
    error = Column(Text)
    
    progress = Column(DECIMAL(5, 2), default=0.00)
    total_tokens = Column(Integer, default=0)
    total_cost = Column(DECIMAL(10, 4), default=0.00)
    
    metadata = Column(JSONB, default={})
    created_at = Column(TIMESTAMPTZ, default=datetime.utcnow, index=True)
    updated_at = Column(TIMESTAMPTZ, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    project = relationship("Project", back_populates="tasks")
    dataset = relationship("Dataset", back_populates="tasks")
    creator = relationship("User", back_populates="tasks")
    evaluation_results = relationship("EvaluationResult", back_populates="task")
    synthesis_results = relationship("SynthesisResult", back_populates="task")
```

---

## 5. 业务流程

### 5.1 评估任务完整流程

```
┌─────────┐
│ 1. 用户 │
│ 提交评估│
│ 请求    │
└────┬────┘
     │
     ↓
┌─────────────────────────────────────┐
│ 2. diting-web Backend (FastAPI)    │
│                                     │
│ POST /api/v1/tasks/evaluations     │
│                                     │
│ • 验证 JWT Token                   │
│ • 验证请求参数                     │
│ • 创建 Task 记录 (status=pending) │
│ • 发布到 arq 队列                  │
│ • 返回 task_id                     │
└────┬────────────────────────────────┘
     │
     ↓ 立即返回
┌─────────────────────────────────────┐
│ 响应给用户                          │
│ {"task_id": "uuid", "status": "pending"}│
└─────────────────────────────────────┘

    ∥ 同时异步处理

┌─────────────────────────────────────┐
│ 3. arq Worker (diting-web 内部)    │
│                                     │
│ • 从 Redis 队列消费任务            │
│ • 更新 Task 状态为 running         │
│ • 🔑 直接导入 diting-core SDK      │
│   from diting_core.metrics import  │
│        get_metric                   │
│ • 🔑 直接调用评估函数              │
│   result = metric.measure(...)     │
└────┬────────────────────────────────┘
     │
     ↓ 直接调用 SDK（函数调用）
┌─────────────────────────────────────┐
│ 4. diting-core SDK                 │
│                                     │
│ • 执行指标计算                     │
│ • 调用 LLM API                     │
│ • 返回评估结果对象                 │
└────┬────────────────────────────────┘
     │
     ↓ 返回结果对象
┌─────────────────────────────────────┐
│ 5. arq Worker 保存结果             │
│                                     │
│ • 接收评估结果对象                 │
│ • 保存结果到 PostgreSQL            │
│   - 更新 tasks 表                  │
│   - 插入 evaluation_results 表    │
│ • 缓存结果到 Redis                 │
│ • 发送 WebSocket 通知              │
└────┬────────────────────────────────┘
     │
     ↓ WebSocket 推送
┌─────────────────────────────────────┐
│ 6. 前端实时接收通知                 │
│                                     │
│ socket.on('task_completed', (data) =>│
│   updateUI(data)                    │
│ )                                   │
└─────────────────────────────────────┘
```

---

### 5.2 用户认证流程

```
1. 用户登录
   ↓
   POST /api/v1/auth/login
   {username, password}
   
2. 后端验证
   ↓
   • 查询用户
   • 验证密码 (bcrypt)
   • 生成 JWT Token
   
3. 返回 Token
   ↓
   {
     access_token: "...",  // 有效期 30 分钟
     refresh_token: "..."  // 有效期 7 天
   }
   
4. 后续请求携带 Token
   ↓
   Authorization: Bearer <access_token>
   
5. Token 过期
   ↓
   使用 refresh_token 刷新
   POST /api/v1/auth/refresh
```

---

### 5.2.5 模型配置优先级流程 ⭐ 新增

当使用评估器执行批量评估时，系统会为每个维度选择合适的模型配置，遵循以下优先级：

```
┌─────────────────────────────────────────────────────────────────┐
│ 批量评估任务执行（使用评估器）                                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 1. 获取评估器配置                                                │
│                                                                  │
│ evaluator = get_evaluator(evaluator_id)                        │
│ config = evaluator.config  # EvaluatorConfig                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. 遍历评估器的每个维度                                          │
│                                                                  │
│ for metric in evaluator.metrics:                               │
│     model_config = select_model_for_metric(metric)             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. 模型配置选择（按优先级）                                      │
│                                                                  │
│ 优先级1: 维度专属配置                                            │
│ ───────────────────────────────────────────────                 │
│ for config in evaluator.config.metric_model_configs:           │
│     if config.metric_id == metric.id:                          │
│         if metric.llm_required and config.llm_config:          │
│             return config.llm_config  ← 最高优先级              │
│         if metric.embedding_required and config.embedding_config:│
│             return config.embedding_config  ← 最高优先级        │
│                                                                  │
│ 优先级2: 评估器默认配置                                          │
│ ───────────────────────────────────────────────                 │
│ if metric.llm_required:                                         │
│     if evaluator.config.default_llm_config:                    │
│         return evaluator.config.default_llm_config             │
│ if metric.embedding_required:                                   │
│     if evaluator.config.default_embedding_config:              │
│         return evaluator.config.default_embedding_config       │
│                                                                  │
│ 优先级3: 任务级配置（兼容旧版）                                   │
│ ───────────────────────────────────────────────                 │
│ if task.config.llm_config:                                      │
│     return task.config.llm_config                              │
│ if task.config.embedding_config:                                │
│     return task.config.embedding_config                        │
│                                                                  │
│ 优先级4: 系统默认配置（兜底）                                     │
│ ───────────────────────────────────────────────                 │
│ return get_system_default_config()                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. 使用选定的模型执行评估                                         │
│                                                                  │
│ result = EvaluationRunner.run_evaluation(                      │
│     metric_name=metric.name,                                   │
│     llm_config=selected_llm_config,      ← 已选择的配置        │
│     embedding_config=selected_embedding_config,                │
│     test_case_data=row_data                                    │
│ )                                                               │
└─────────────────────────────────────────────────────────────────┘
```

**实际示例**：

假设有以下评估器配置：
```json
{
  "evaluator_id": "uuid-evaluator",
  "metrics": ["answer_correctness", "faithfulness", "answer_similarity"],
  "config": {
    "metric_model_configs": [
      {
        "metric_id": "uuid-answer-correctness",
        "llm_config": {"name": "gpt-4"}  // 专属配置
      }
    ],
    "default_llm_config": {"name": "gpt-3.5-turbo"},  // 默认
    "default_embedding_config": {"name": "text-embedding-ada-002"}
  }
}
```

**执行时的模型选择**：

| 维度 | 模型需求 | 使用的配置 | 优先级 |
|------|---------|-----------|--------|
| answer_correctness | LLM | `gpt-4` | ①专属配置 |
| faithfulness | LLM | `gpt-3.5-turbo` | ②默认配置 |
| answer_similarity | Embedding | `text-embedding-ada-002` | ②默认配置 |

**成本对比**：
- 如果全部使用 GPT-4：$0.15/条
- 使用上述配置：$0.06/条（节省 60%）

---

### 5.3 批量评估流程

```
1. 用户上传数据集
   ↓
   POST /api/v1/datasets
   • 文件上传到 MinIO
   • 解析文件（CSV/JSONL）
   • 保存元数据到 PostgreSQL
   
2. 创建批量评估任务
   ↓
   POST /api/v1/tasks/batch-evaluations
   {
     dataset_id: "uuid",
     metric_config: {...}
   }
   
3. arq Worker 处理
   ↓
   • 读取数据集（从 MinIO）
   • 逐行创建子任务
   • 并发调用 diting-server
   • 更新总任务进度
   
4. 结果汇总
   ↓
   • 保存每行结果
   • 计算统计数据
   • 生成报告
```

---

### 5.4 数据集标注流程 🆕

```
┌─────────────────────────────────────────────┐
│ 1. 用户上传数据集                           │
│    POST /api/v1/datasets                    │
│    • 上传CSV/JSONL文件                      │
│    • 解析并存储到MinIO（原始文件备份）      │
│    • 创建Dataset记录                        │
│    • 将每行数据插入到 dataset_rows 表       │
│    • 初始化metadata = {}                    │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│ 2. 查看数据集详情                           │
│    GET /api/v1/datasets/{dataset_id}        │
│    • 返回数据集基本信息                     │
│    • metadata.annotation_columns = []       │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│ 3. 添加标注列                               │
│    POST /api/v1/datasets/{id}/annotations/  │
│         columns                              │
│    请求体：                                  │
│    {                                         │
│      "column_name": "情感标注",             │
│      "column_type": "category",             │
│      "description": "情感分类",             │
│      "options": ["正面", "负面", "中性"]    │
│    }                                         │
│                                              │
│    后端处理：                                │
│    • 验证列名不重复                         │
│    • 更新dataset.metadata_["annotation_    │
│      columns"]                               │
│    • 在所有dataset_rows记录中初始化该列    │
│      (UPDATE dataset_rows SET data =        │
│       jsonb_set(data, '{column_name}', '""')│
│    • 返回更新后的数据集                     │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│ 4. 预览并编辑数据                           │
│    GET /api/v1/datasets/{id}/preview?       │
│        page=1&page_size=10&search=关键词    │
│                                              │
│    后端处理：                                │
│    • 从dataset_rows表查询数据               │
│    • 如果提供search参数，使用SQL WHERE     │
│      在数据库层面过滤                       │
│    • 支持分页和排序                         │
│                                              │
│    返回：                                    │
│    {                                         │
│      "columns": ["user_input",              │
│                  "expected_output",          │
│                  "情感标注"],  # 包含标注列 │
│      "preview_data": [                       │
│        {                                     │
│          "user_input": "这个产品很好",      │
│          "expected_output": "...",          │
│          "情感标注": ""  # 待标注           │
│        }                                     │
│      ],                                      │
│      "total": 100,                           │
│      "page": 1,                              │
│      "page_size": 10                         │
│    }                                         │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│ 5. 标注数据                                 │
│    PUT /api/v1/datasets/{id}/data           │
│    请求体：                                  │
│    {                                         │
│      "preview_data": [                       │
│        {                                     │
│          "user_input": "这个产品很好",      │
│          "expected_output": "...",          │
│          "情感标注": "正面"  # 已标注       │
│        }                                     │
│      ],                                      │
│      "row_count": 100                        │
│    }                                         │
│                                              │
│    后端处理：                                │
│    • 更新dataset_rows表中的对应记录         │
│      (UPDATE dataset_rows SET data = ...)   │
│    • 更新dataset.updated_at                 │
│    • 返回成功响应                           │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│ 6. 删除标注列（可选）                       │
│    DELETE /api/v1/datasets/{id}/annotations/│
│           columns                            │
│    请求体：                                  │
│    {                                         │
│      "column_name": "情感标注"              │
│    }                                         │
│                                              │
│    后端处理：                                │
│    • 从metadata_["annotation_columns"]移除 │
│    • 从所有dataset_rows记录中删除该列      │
│      (UPDATE dataset_rows SET data =        │
│       data - 'column_name')                 │
│    • 返回更新后的数据集                     │
└─────────────────────────────────────────────┘
```

**设计亮点**：

1. **灵活的标注列定义**：
   - 支持多种数据类型（text、number、category、boolean）
   - 分类类型可定义候选选项
   - 每列可添加描述说明

2. **非侵入式存储**：
   - 标注列信息存储在 `metadata.annotation_columns` 中
   - 标注数据与原始数据一起存储在 `dataset_rows.data` JSONB 字段中
   - 不影响原始数据集结构

3. **完整的CRUD支持**：
   - 添加标注列：使用 SQL UPDATE 初始化所有 dataset_rows 记录的该列
   - 查看数据：从 dataset_rows 表查询，支持数据库层面搜索
   - 编辑标注：直接 UPDATE dataset_rows 表中的记录
   - 删除标注列：使用 JSONB 操作从所有记录中删除该列

4. **前端友好**：
   - 分页查询支持（数据库层面分页）
   - 全文搜索支持（数据库层面搜索，性能好）
   - 明确区分原始数据和标注数据
   - 支持批量更新

---

### 5.5 数据导出流程 🆕

```
┌─────────────────────────────────────────────┐
│ 数据存储架构                                │
│                                              │
│  ┌──────────────┐         ┌──────────────┐ │
│  │   MinIO      │         │ PostgreSQL   │ │
│  │              │         │              │ │
│  │ 原始文件存储 │         │ 当前数据存储 │ │
│  │ (不可变)     │         │ (可编辑)     │ │
│  │              │         │              │ │
│  │              │         │ datasets表   │ │
│  │              │         │ dataset_rows │ │
│  │              │         │   表         │ │
│  └──────┬───────┘         └──────┬───────┘ │
│         │                        │         │
└─────────┼────────────────────────┼─────────┘
          │                        │
          ↓                        ↓
  
┌─────────────────┐        ┌──────────────────┐
│ 下载原始文件     │        │  导出当前数据     │
│                 │        │                  │
│ GET /download/  │        │  GET /export     │
│     original    │        │                  │
│                 │        │                  │
│ • 返回MinIO     │        │ • 从dataset_rows表 │
│   预签名URL     │        │   读取数据         │
│ • 原始上传文件  │        │ • 生成CSV/JSONL   │
│ • 不含编辑      │        │ • 包含所有编辑    │
│                 │        │ • 包含新增列      │
└─────────────────┘        └──────────────────┘
```

**设计原则**：

1. **双存储机制**：
   - MinIO：存储原始上传文件（只读）
   - PostgreSQL：存储可编辑的当前数据

2. **原始文件下载**：
   - 用途：保留原始数据备份
   - 方式：预签名URL（临时有效）
   - 内容：上传时的原始文件

3. **数据导出**：
   - 用途：获取标注/编辑后的数据
   - 方式：从 dataset_rows 表查询数据，生成文件流
   - 内容：PostgreSQL 中的最新数据（包含所有编辑和标注）

4. **使用场景**：
   ```
   上传数据 → 添加标注列 → 编辑标注 → 导出数据
                                       ↓
                                  下一轮处理
   
   如需恢复原始数据：下载原始文件 → 重新上传
   ```

---

### 5.6 数据增强结果导出和导入流程 🆕

```
┌─────────────────────────────────────────────┐
│ 1. 创建数据增强任务                          │
│    POST /api/v1/tasks/synthesis              │
│    • 配置LLM和合成器                        │
│    • 提供输入数据（主题、上下文）            │
│    • 返回 task_id                           │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│ 2. 任务执行完成                              │
│    • arq Worker 执行合成任务                │
│    • 结果保存到 synthesis_results 表        │
│    • 任务状态更新为 completed               │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│ 3. 获取合成结果                              │
│    方式1: 通过任务ID获取                     │
│    GET /api/v1/tasks/{task_id}/synthesis-   │
│         results                              │
│    • 返回该任务的所有合成结果                │
│                                              │
│    方式2: 通过项目查询                       │
│    GET /api/v1/results/synthesis?project_id= │
│    • 返回项目的所有合成结果                  │
└──────────────────┬──────────────────────────┘
                   ↓
        ┌──────────┴──────────┐
        │                     │
        ↓                     ↓
┌───────────────┐   ┌──────────────────┐
│ 4a. 导出结果   │   │ 4b. 导入为数据集  │
│                │   │                  │
│ GET /tasks/{id}│   │ POST /tasks/{id} │
│ /synthesis-    │   │ /synthesis-      │
│ results/export │   │ results/create-   │
│                │   │ dataset          │
│ • 格式: CSV/   │   │                  │
│   JSONL        │   │ • 输入数据集名称  │
│ • 直接下载     │   │ • 自动创建数据集  │
│                │   │ • 转换结果格式   │
└────────────────┘   └────────┬─────────┘
                               │
                               ↓
                  ┌────────────────────────┐
                  │ 5. 数据集管理          │
                  │                        │
                  │ • 查看和编辑数据集     │
                  │ • 添加标注列          │
                  │ • 导出数据集          │
                  │ • 用于批量评估         │
                  └────────────────────────┘
```

**设计亮点**：

1. **便捷的结果导出**：
   - 支持 CSV 和 JSONL 两种格式
   - CSV 格式包含 UTF-8 BOM，Excel 可直接打开
   - 一键下载，无需额外处理

2. **无缝的数据集集成**：
   - 一键将增强结果转换为数据集
   - 自动格式化数据（question, answer 等字段）
   - 数据集中标记来源（`metadata.source: "synthesis_results"`）

3. **完整的数据流转**：
   ```
   数据增强 → 导出文件 → 外部使用
            ↓
   数据增强 → 导入数据集 → 数据集管理 → 批量评估
   ```

4. **使用场景**：
   - **场景1**: 生成数据后直接导出，用于外部工具或分析
   - **场景2**: 生成数据后导入数据集，继续在平台内管理和使用
   - **场景3**: 生成数据后先导出备份，再导入数据集进行进一步处理

---

### 5.7 数据集导入用于数据增强流程 🆕

```
┌─────────────────────────────────────────────┐
│ 1. 用户进入数据增强页面                      │
│    • 选择"智能生成"标签页                    │
│    • 配置LLM和合成器                        │
└──────────────────┬──────────────────────────┘
                   ↓
        ┌──────────┴──────────┐
        │                     │
        ↓                     ↓
┌───────────────┐   ┌──────────────────┐
│ 方式1: 手动输入│   │ 方式2: 数据集导入 │
│                │   │                  │
│ • 直接输入主题  │   │ • 点击"从数据集   │
│ • 直接输入上下文│   │   导入"按钮      │
│                │   │ • 选择数据集     │
└───────────────┘   └────────┬─────────┘
                             │
                             ↓
                  ┌────────────────────────┐
                  │ 2. 数据集导入流程      │
                  │                        │
                  │ • GET /api/v1/datasets │
                  │   获取数据集列表        │
                  │                        │
                  │ • GET /api/v1/datasets/│
                  │   {id}/preview         │
                  │   获取数据集预览数据    │
                  │                        │
                  │ • 智能字段映射：        │
                  │   - 自动识别常见字段名  │
                  │   - 支持手动选择映射   │
                  │                        │
                  │ • 数据提取和填充：      │
                  │   - 从数据集提取上下文  │
                  │   - 从数据集提取主题    │
                  │   - 自动填充到表单     │
                  └────────┬───────────────┘
                           │
                           ↓
                  ┌────────────────────────┐
                  │ 3. 提交合成任务         │
                  │                        │
                  │ POST /api/v1/tasks/     │
                  │    synthesis            │
                  │                        │
                  │ • 请求格式与手动输入    │
                  │   模式相同              │
                  │ • 包含从数据集提取的    │
                  │   主题和上下文          │
                  └────────────────────────┘
```

**设计亮点**：

1. **双模式支持**：
   - **手动输入模式**：适合快速测试和少量数据
   - **数据集导入模式**：适合批量处理和复用已有数据

2. **智能字段映射**：
   - 自动识别常见字段名（context/content/text/document 用于上下文，theme/topic/category 用于主题）
   - 支持手动选择映射字段，灵活适配不同数据集结构
   - 字段映射可选，用户可以选择只映射上下文或只映射主题

3. **数据加载优化**：
   - 小数据集（≤100条）：自动加载全部数据
   - 大数据集：使用预览数据（前10条）提高性能
   - 支持预览数据展示，让用户确认映射正确性

4. **完整的数据流转**：
   ```
   数据集管理 → 数据集导入 → 数据增强 → 增强结果 → 导出/导入数据集 → 批量评估
   ```

5. **使用场景**：
   - **场景1**: 复用已有数据集中的上下文数据进行增强
   - **场景2**: 从知识库数据集中提取主题和上下文进行批量生成
   - **场景3**: 结合数据集管理和数据增强，形成完整的数据工作流

**技术实现**：
- 前端使用现有的数据集API，无需后端改动
- 字段映射和数据提取在前端完成，充分利用浏览器的计算能力
- 支持实时预览和验证，提升用户体验

---

## 6. 技术栈

### 6.1 核心依赖

```toml
[project]
dependencies = [
    # Web 框架
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    
    # 数据库
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    "psycopg2-binary>=2.9.0",
    
    # 任务队列
    "arq>=0.25.0",
    
    # 缓存
    "redis[hiredis]>=5.0.0",
    
    # HTTP 客户端
    "httpx>=0.27.0",
    
    # 对象存储
    "minio>=7.2.0",
    
    # WebSocket
    "python-socketio>=5.11.0",
    
    # 认证
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    
    # 数据验证
    "pydantic>=2.9.0",
    "pydantic-settings>=2.10.0",
    
    # 日志
    "structlog>=24.4.0",
    
    # 工具
    "python-multipart>=0.0.9",
    "email-validator>=2.1.0",
]
```

---

## 7. 附录

### 7.1 数据库迁移脚本

```bash
# 初始化 Alembic
alembic init alembic

# 生成迁移脚本
alembic revision --autogenerate -m "Initial schema"

# 执行迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

### 7.2 环境变量

```env
# 应用配置
ENVIRONMENT=Development
HOST=0.0.0.0
PORT=8000

# 数据库
DATABASE_URL=postgresql+asyncpg://admin:password@localhost:5432/diting_web

# Redis
REDIS_URL=redis://localhost:6379/0

# diting-server
DITING_SERVER_URL=http://localhost:3000

# JWT
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

---

---

## 📝 文档更新记录

### v4.2.0 (2025-01-XX) 🆕

**新增功能**: 数据集导入用于数据增强

#### 新增内容

**API 设计**:
- ✅ 更新创建合成任务 API (3.8.2)，说明支持从数据集导入数据
- ✅ 补充数据集预览 API 使用场景说明

**业务流程**:
- ✅ 添加数据集导入用于数据增强流程 (5.7)

**前端实现**:
- ✅ 添加数据集导入模式切换功能
- ✅ 实现智能字段映射（自动识别常见字段名）
- ✅ 实现数据预览和自动填充功能
- ✅ 优化用户体验：支持手动调整映射和编辑数据
- ✅ 添加数据加载优化（小数据集加载全部，大数据集使用预览）

#### 功能说明

1. **双模式支持**：
   - 手动输入模式：适合快速测试和少量数据
   - 数据集导入模式：适合批量处理和复用已有数据

2. **智能字段映射**：
   - 自动识别常见字段名（context/content/text/document 用于上下文，theme/topic/category 用于主题）
   - 支持手动选择映射字段，灵活适配不同数据集结构
   - 字段映射可选，用户可以选择只映射上下文或只映射主题

3. **数据加载优化**：
   - 小数据集（≤100条）：自动加载全部数据
   - 大数据集：使用预览数据（前10条）提高性能
   - 支持预览数据展示，让用户确认映射正确性

4. **完整的数据流转**：
   ```
   数据集管理 → 数据集导入 → 数据增强 → 增强结果 → 导出/导入数据集 → 批量评估
   ```

#### 兼容性说明

- ✅ 向后兼容：所有现有 API 保持不变
- ✅ 前端功能增强：不影响现有功能使用
- ✅ 无需后端改动：利用现有数据集API实现

---

### v4.1.0 (2025-01-XX) 🆕

**新增功能**: 数据增强结果导出和导入数据集

#### 新增内容

**API 设计**:
- ✅ 添加获取合成结果列表 API (3.8.7) - `GET /api/v1/tasks/{task_id}/synthesis-results`
- ✅ 添加导出合成结果 API (3.8.8) - `GET /api/v1/tasks/{task_id}/synthesis-results/export`
- ✅ 添加从合成结果创建数据集 API (3.8.9) - `POST /api/v1/tasks/{task_id}/synthesis-results/create-dataset`
- ✅ 更新结果查询 API 说明 (3.9.2, 3.9.3)，明确与任务级API的区别

**数据结构 Schema**:
- ✅ 添加 `CreateDatasetFromSynthesisRequest` Schema (4.1.6)

**业务流程**:
- ✅ 添加数据增强结果导出和导入流程 (5.6)

**后端实现**:
- ✅ `TaskService.get_synthesis_results()` - 获取合成结果方法
- ✅ `DatasetService.create_dataset_from_data()` - 从数据创建数据集方法

**前端实现**:
- ✅ 优化 Synthesis 页面，添加任务状态轮询
- ✅ 添加导出功能（CSV/JSONL）
- ✅ 添加导入为数据集功能

#### 功能说明

1. **导出功能**：
   - 支持 CSV 和 JSONL 两种格式导出
   - CSV 格式包含 UTF-8 BOM，兼容 Excel
   - 一键下载增强结果

2. **导入数据集功能**：
   - 一键将增强结果转换为数据集
   - 自动格式化数据字段
   - 数据集标记来源，便于追溯

3. **数据流转**：
   - 实现完整的数据增强 → 导出/导入 → 数据集管理 → 批量评估流程
   - 提升用户体验和数据资产复用性

#### 兼容性说明

- ✅ 向后兼容：所有现有 API 保持不变
- ✅ 新增功能：不影响现有功能使用

---

### v4.0.0 (2025-10-24) 🆕

**重大更新**: 采用单 Admin 模式，简化架构设计

#### 新增内容

**数据库设计**:
- ✅ 添加 `metrics` 表 (评估维度表) - 见 2.2.4
- ✅ 添加 `evaluators` 表 (评估器表) - 见 2.2.5
- ✅ 更新 ER 图,体现新增表的关系
- ✅ 添加内置指标初始化 SQL

**API 设计**:
- ✅ 添加健康检查 API (3.2) - `GET /api/v1/healthz`
- ✅ 添加评估维度管理 API (3.6) - CRUD 操作
- ✅ 添加评估器管理 API (3.7) - CRUD 操作
- ✅ 添加 Dashboard 统计 API (3.11.1) - `GET /api/v1/statistics/dashboard`
- ✅ 批量评估 API 支持 evaluator_id (3.8.3)

**数据结构 Schema**:
- ✅ 添加 MetricCategory 枚举 (4.1.3)
- ✅ 添加 Metric 相关 Schema (4.1.3)
- ✅ 添加 Evaluator 相关 Schema (4.1.4)

#### 修复的问题

1. **评估器管理功能缺失** ✅ 已解决
   - 添加了完整的评估器 CRUD API
   - 支持组合多个评估维度

2. **评估维度管理功能缺失** ✅ 已解决
   - 添加了完整的评估维度 CRUD API
   - 支持内置和自定义指标

3. **批量评估不支持评估器** ✅ 已解决
   - 批量评估 API 新增 `evaluator_id` 参数
   - 支持一次评估多个指标

4. **缺少健康检查 API** ✅ 已解决
   - 添加 `/api/v1/healthz` 端点

5. **Dashboard 统计数据缺失** ✅ 已解决
   - 添加 `/api/v1/statistics/dashboard` 端点

#### 兼容性说明

- ✅ 向后兼容: 所有现有 API 保持不变
- ✅ 数据库迁移: 需要执行新的迁移脚本添加两个新表
- ✅ 前端适配: 需要集成新的 API (详见 IMPLEMENTATION_TODO.md)

#### 相关文档

- 📄 [SUMMARY.md](./SUMMARY.md) - 执行摘要
- 📄 [BACKEND_FRONTEND_GAP_ANALYSIS.md](./BACKEND_FRONTEND_GAP_ANALYSIS.md) - 详细差异分析
- 📄 [IMPLEMENTATION_TODO.md](./IMPLEMENTATION_TODO.md) - 实施指南

---

**文档版本**: v4.2.0  
**最后更新**: 2025-01-XX  
**维护者**: DiTing Team

