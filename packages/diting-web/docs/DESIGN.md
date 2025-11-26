# Diting-Web 后端设计文档

> 🎯 **架构版本**: v3.0  
> 📅 **更新日期**: 2025-11-10  
> 🔧 **架构模式**: Simple Single-Tenancy with Admin-Only User Management

## 📋 目录

1. [系统架构](#系统架构)
2. [数据库设计](#数据库设计)
3. [权限体系](#权限体系)
4. [API 设计](#api-设计)
5. [业务流程](#业务流程)
6. [与原设计的对比](#与原设计的对比)

---

## 1. 系统架构

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                      diting-web 后端架构                            │
│                   Simple Single-Tenancy                             │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │            Frontend (React)                                  │  │
│  │         http://localhost:5173                                │  │
│  │                                                               │  │
│  │  • 管理员登录                                                │  │
│  │  • 用户登录                                                  │  │
│  │  • 用户管理（仅管理员）                                      │  │
│  │  • 资源管理（所有用户）                                      │  │
│  └────────────────────┬─────────────────────────────────────────┘  │
│                       │ HTTP/WebSocket + JWT Token                 │
│                       ↓                                             │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │         Backend API (FastAPI) with Simple Auth              │  │
│  │         http://localhost:8000                                │  │
│  │                                                               │  │
│  │  Routes:                                                     │  │
│  │  • /api/v1/auth          - 认证授权 (登录)                  │  │
│  │  • /api/v1/users         - 用户管理 (仅管理员)              │  │
│  │  • /api/v1/datasets      - 数据集管理                       │  │
│  │  • /api/v1/tasks         - 任务管理                         │  │
│  │  • /api/v1/metrics       - 评估维度管理                     │  │
│  │  • /api/v1/evaluators    - 评估器管理                       │  │
│  │  • /api/v1/models        - 模型管理                         │  │
│  │  • /api/v1/prompts       - 提示词管理                       │  │
│  │  • /api/v1/results       - 结果查询                         │  │
│  │  • /api/v1/statistics    - 统计信息                         │  │
│  │  • /api/v1/healthz       - 健康检查                          │  │
│  │  • /ws                   - WebSocket                         │  │
│  │                                                               │  │
│  │  权限中间件:                                                  │  │
│  │  • 管理员权限检查（用户管理）                                │  │
│  │  • 用户认证检查（资源访问）                                  │  │
│  │  • 资源所有权验证（可选）                                    │  │
│  └──────────┬───────────────────────┬───────────────────────────┘  │
│             │                       │                               │
│             ↓                       ↓                               │
│  ┌──────────────────┐    ┌──────────────────┐                     │
│  │   PostgreSQL     │    │   Redis          │                     │
│  │   (数据持久化)   │    │   (队列+缓存)    │                     │
│  │                  │    │                  │                     │
│  │  • Simple Schema │    │  • Session       │                     │
│  │  • User-based    │    │  • Rate Limit    │                     │
│  │    Filtering     │    │  • Cache         │                     │
│  └──────────────────┘    └────────┬─────────┘                     │
│                                   │                                 │
│                                   ↓                                 │
│                          ┌──────────────────────────────┐           │
│                          │  arq Worker                  │           │
│                          │  (异步任务处理)              │           │
│                          │                              │           │
│                          │  • 直接集成 diting-core SDK  │           │
│                          │  • 执行评估和合成任务        │           │
│                          │  • 按用户隔离任务            │           │
│                          └──────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 架构特点

**简洁的用户体系**:
- 只有两种角色：管理员（admin）和普通用户（user）
- 管理员通过 `is_admin` 字段标识
- 移除组织、项目等复杂概念

**简单的权限控制**:
- 管理员可以：创建、查看、编辑、删除所有用户
- 普通用户可以：登录、管理自己的资源（数据集、任务、评估器等）
- 可选：资源级别的所有权验证（如果需要用户间资源隔离）

**数据访问**:
- 无需复杂的多租户隔离
- 可选：按 `created_by` 字段过滤用户自己的资源
- 管理员可以访问所有资源

---

## 2. 数据库设计

### 2.1 ER 图 (简化架构)

```
                            ┌────────────────────────────────┐
                            │   用户体系（简化）             │
                            └────────────────────────────────┘

       ┌─────────────┐
       │   users     │
       │             │
       │  • id       │
       │  • username │
       │  • email    │
       │  • password │
       │  • is_admin │──────► 管理员标识
       │  • is_active│
       └──────┬──────┘
              │created_by
              │
              └───────────────────────────────────┐
                                                  │
                            ┌────────────────────────────────┐
                            │   资源管理体系                 │
                            └────────────────────────────────┘

       ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
       │   models    │         │   metrics    │         │ evaluators  │
       │             │         │             │       n │             │
       │  • id       │         │  • id       │◄────────┤  • id       │
       │  • name     │         │  • name     │ metrics │  • name     │
       │  • type     │         │  • type     │         │  • config   │
       │  • provider │         │  • is_global│         │  • created  │
       │  • created  │         └─────────────┘         └──────┬──────┘
       └─────────────┘                                        │1
                                                              │
       ┌─────────────┐         ┌─────────────┐              │n
       │  datasets   │         │dataset_rows │       ┌──────┴──────┐
       │             │    1:n  │             │       │    tasks    │
       │  • id       │─────────│  • id       │       │             │
       │  • name     │         │  • dataset  │       │  • id       │
       │  • created  │         │  • row_index│       │  • type     │
       └──────┬──────┘         │  • data     │       │  • status   │
              │1               └─────────────┘       │  • created  │
              │                                      └──────┬──────┘
              │n                                            │1
       ┌──────┴──────┐                         ┌────────────┼────────────┐
       │   prompts   │                         │n           │n           │n
       │             │                   ┌─────┴─────┐ ┌────┴─────┐ ┌───┴─────┐
       │  • id       │                   │evaluation │ │synthesis │ │audit    │
       │  • name     │                   │_results   │ │_results  │ │_logs    │
       │  • content  │                   │           │ │          │ │         │
       │  • created  │                   │  • score  │ │• question│ │• action │
       └─────────────┘                   │  • reason │ │• answer  │ │• user   │
                                         └───────────┘ └──────────┘ └─────────┘

说明：
- users: 用户表，is_admin 字段区分管理员和普通用户
- 所有资源表（datasets, tasks, evaluators, prompts）都通过 created_by 关联到创建者
- metrics 支持全局（is_global=true）和用户自定义（is_global=false）
  - 系统内置维度（is_global=true）：所有用户可见，只有管理员可修改
  - 用户自定义维度（is_global=false）：仅创建者和管理员可见
- 移除了 organizations, projects, roles, permissions 等复杂表
- 简化的权限模型：管理员 vs 普通用户
```

### 2.2 数据表设计

#### 2.2.1 users (用户表)

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    avatar_url VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE NOT NULL,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    metadata JSONB DEFAULT '{}' NOT NULL
);

-- 索引
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active);
CREATE INDEX idx_users_admin ON users(is_admin);
CREATE INDEX idx_users_created ON users(created_at DESC);

-- 注释
COMMENT ON TABLE users IS '用户表（简化架构）';
COMMENT ON COLUMN users.username IS '用户名（全局唯一）';
COMMENT ON COLUMN users.email IS '邮箱（全局唯一）';
COMMENT ON COLUMN users.hashed_password IS 'bcrypt 哈希密码';
COMMENT ON COLUMN users.is_admin IS '管理员标识（true=管理员，false=普通用户）';
COMMENT ON COLUMN users.metadata IS '用户元数据（JSONB）';
```

**字段说明**：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | UUID | 是 | gen_random_uuid() | 主键 |
| username | VARCHAR(50) | 是 | - | 用户名（全局唯一） |
| email | VARCHAR(100) | 是 | - | 邮箱（全局唯一） |
| hashed_password | VARCHAR(255) | 是 | - | bcrypt 哈希密码 |
| full_name | VARCHAR(100) | 否 | NULL | 用户全名 |
| avatar_url | VARCHAR(500) | 否 | NULL | 头像 URL |
| is_active | BOOLEAN | 是 | TRUE | 账号是否激活 |
| is_admin | BOOLEAN | 是 | FALSE | **管理员标识** |
| last_login_at | TIMESTAMPTZ | 否 | NULL | 最后登录时间 |
| created_at | TIMESTAMPTZ | 是 | NOW() | 创建时间 |
| updated_at | TIMESTAMPTZ | 是 | NOW() | 更新时间 |
| metadata | JSONB | 是 | {} | 用户元数据 |

#### 2.2.2 datasets (数据集表)

```sql
CREATE TABLE datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    file_name VARCHAR(500),
    file_size BIGINT,
    file_path VARCHAR(1000),
    row_count INTEGER DEFAULT 0,
    column_count INTEGER DEFAULT 0,
    columns JSONB DEFAULT '[]' NOT NULL,
    status VARCHAR(50) DEFAULT 'active' NOT NULL,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    metadata JSONB DEFAULT '{}' NOT NULL
);

-- 索引
CREATE INDEX idx_datasets_name ON datasets(name);
CREATE INDEX idx_datasets_status ON datasets(status);
CREATE INDEX idx_datasets_created_by ON datasets(created_by);
CREATE INDEX idx_datasets_created_at ON datasets(created_at DESC);

-- 注释
COMMENT ON TABLE datasets IS '数据集表';
COMMENT ON COLUMN datasets.created_by IS '创建者用户ID';
```

#### 2.2.3 tasks (任务表)

```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' NOT NULL,
    config JSONB NOT NULL,
    result JSONB,
    error TEXT,
    progress INTEGER DEFAULT 0,
    total INTEGER,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    metadata JSONB DEFAULT '{}' NOT NULL
);

-- 索引
CREATE INDEX idx_tasks_type ON tasks(type);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created_by ON tasks(created_by);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);

-- 注释
COMMENT ON TABLE tasks IS '任务表';
COMMENT ON COLUMN tasks.type IS '任务类型：evaluation, synthesis';
COMMENT ON COLUMN tasks.created_by IS '创建者用户ID';
```

#### 2.2.4 evaluators (评估器表)

```sql
CREATE TABLE evaluators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    config JSONB NOT NULL,
    metrics UUID[] NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- 索引
CREATE INDEX idx_evaluators_name ON evaluators(name);
CREATE INDEX idx_evaluators_active ON evaluators(is_active);
CREATE INDEX idx_evaluators_created_by ON evaluators(created_by);

-- 注释
COMMENT ON TABLE evaluators IS '评估器表';
COMMENT ON COLUMN evaluators.created_by IS '创建者用户ID';
```

#### 2.2.5 metrics (评估维度表)

```sql
CREATE TABLE metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    display_name VARCHAR(200),
    description TEXT,
    type VARCHAR(50) NOT NULL,
    config JSONB DEFAULT '{}' NOT NULL,
    is_global BOOLEAN DEFAULT FALSE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- 索引
CREATE INDEX idx_metrics_name ON metrics(name);
CREATE INDEX idx_metrics_type ON metrics(type);
CREATE INDEX idx_metrics_global ON metrics(is_global);
CREATE INDEX idx_metrics_created_by ON metrics(created_by);

-- 注释
COMMENT ON TABLE metrics IS '评估维度表';
COMMENT ON COLUMN metrics.is_global IS '是否全局维度（系统内置=true，用户自定义=false）';
COMMENT ON COLUMN metrics.created_by IS '创建者用户ID（全局维度为NULL）';
```

**访问控制**：
- **系统内置维度** (is_global=true)：所有用户可见，只有管理员可以修改
- **用户自定义维度** (is_global=false)：只有创建者和管理员可以查看、修改、删除

#### 2.2.6 prompts (提示词表)

```sql
CREATE TABLE prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    variables JSONB DEFAULT '[]' NOT NULL,
    template_type VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    metadata JSONB DEFAULT '{}' NOT NULL
);

-- 索引
CREATE INDEX idx_prompts_name ON prompts(name);
CREATE INDEX idx_prompts_active ON prompts(is_active);
CREATE INDEX idx_prompts_created_by ON prompts(created_by);

-- 注释
COMMENT ON TABLE prompts IS '提示词模板表';
COMMENT ON COLUMN prompts.created_by IS '创建者用户ID';
```

#### 2.2.7 models (模型配置表)

```sql
CREATE TABLE models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    provider VARCHAR(100) NOT NULL,
    model_type VARCHAR(100) NOT NULL,
    api_key_encrypted TEXT,
    api_base VARCHAR(500),
    config JSONB DEFAULT '{}' NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- 索引
CREATE INDEX idx_models_name ON models(name);
CREATE INDEX idx_models_provider ON models(provider);
CREATE INDEX idx_models_active ON models(is_active);
CREATE INDEX idx_models_created_by ON models(created_by);

-- 注释
COMMENT ON TABLE models IS '模型配置表';
COMMENT ON COLUMN models.created_by IS '创建者用户ID';
```

---

## 3. 权限体系

### 3.1 简化的权限模型

```
┌──────────────────────────────────────────────────────────────┐
│                     权限体系（简化）                         │
└──────────────────────────────────────────────────────────────┘

角色类型：
  ┌─────────────┐                    ┌─────────────┐
  │   管理员    │                    │  普通用户   │
  │  (is_admin  │                    │  (is_admin  │
  │   = true)   │                    │   = false)  │
  └──────┬──────┘                    └──────┬──────┘
         │                                  │
         │ 权限                             │ 权限
         │                                  │
         ├─► 用户管理                       ├─► 登录系统
         │   • 创建用户 ✓                   ├─► 管理自己的资源
         │   • 查看用户 ✓                   │   • 数据集 (CRUD)
         │   • 编辑用户 ✓                   │   • 任务 (CRUD)
         │   • 删除用户 ✓                   │   • 评估器 (CRUD)
         │                                  │   • 提示词 (CRUD)
         ├─► 资源访问                       │   • 模型配置 (CRUD)
         │   • 查看所有资源 ✓               │   • 自定义维度 (CRUD)
         │   • 管理所有资源 ✓               │
         │                                  ├─► 查看系统内置资源
         └─► 系统配置                       │   • 系统内置维度（所有人可见）
             • 系统设置 ✓                   │   • 其他全局配置（只读）
             • 内置维度管理 ✓               │
                                            └─► 查看自己的结果
```

### 3.2 权限检查实现

**中间件层级**:

1. **认证中间件**：验证 JWT Token，获取当前用户
2. **管理员权限中间件**：检查 `is_admin` 字段，用于用户管理接口
3. **资源所有权中间件**（可选）：检查 `created_by` 字段，确保用户只能访问自己的资源

**示例代码**:

```python
from functools import wraps
from fastapi import Depends, HTTPException, status
from diting_web.core.auth import get_current_user
from diting_web.models.user import User

def require_admin(current_user: User = Depends(get_current_user)):
    """要求管理员权限"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user

def require_auth(current_user: User = Depends(get_current_user)):
    """要求登录（普通用户或管理员）"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    return current_user

# 使用示例
@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_admin),  # 只有管理员可以创建用户
    db: Session = Depends(get_db)
):
    """创建用户（仅管理员）"""
    ...

@router.get("/datasets", response_model=List[DatasetResponse])
async def list_datasets(
    current_user: User = Depends(require_auth),  # 所有登录用户都可以访问
    db: Session = Depends(get_db)
):
    """获取数据集列表"""
    # 可选：过滤只显示用户自己的数据
    # query = db.query(Dataset).filter(Dataset.created_by == current_user.id)
    
    # 或者：管理员可以看到所有，普通用户只能看到自己的
    if current_user.is_admin:
        query = db.query(Dataset)
    else:
        query = db.query(Dataset).filter(Dataset.created_by == current_user.id)
    ...

@router.get("/metrics", response_model=List[MetricResponse])
async def list_metrics(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """获取评估维度列表"""
    # 系统内置维度 + 用户自己的维度
    if current_user.is_admin:
        # 管理员可以看到所有维度
        query = db.query(Metric)
    else:
        # 普通用户可以看到：系统内置维度 + 自己创建的维度
        query = db.query(Metric).filter(
            or_(
                Metric.is_global == True,  # 系统内置维度
                Metric.created_by == current_user.id  # 自己创建的维度
            )
        )
    ...
```

---

## 4. API 设计

### 4.1 认证授权 API

#### POST /api/v1/auth/login
管理员和普通用户登录

**请求体**:
```json
{
  "username": "admin",
  "password": "password123"
}
```

**响应**:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "username": "admin",
    "email": "admin@example.com",
    "is_admin": true,
    "is_active": true
  }
}
```

### 4.2 用户管理 API（仅管理员）

#### POST /api/v1/users
创建用户（仅管理员）

**权限**: 需要管理员

**请求体**:
```json
{
  "username": "newuser",
  "email": "newuser@example.com",
  "password": "password123",
  "full_name": "New User",
  "is_admin": false
}
```

#### GET /api/v1/users
获取用户列表（仅管理员）

**权限**: 需要管理员

**查询参数**:
- `page`: 页码（默认1）
- `page_size`: 每页数量（默认20）
- `is_admin`: 过滤管理员（可选）
- `is_active`: 过滤激活状态（可选）

#### GET /api/v1/users/{user_id}
获取用户详情（仅管理员）

#### PUT /api/v1/users/{user_id}
更新用户信息（仅管理员）

**请求体**:
```json
{
  "full_name": "Updated Name",
  "is_active": true,
  "is_admin": false
}
```

#### DELETE /api/v1/users/{user_id}
删除用户（仅管理员）

### 4.3 资源管理 API（所有用户）

以下接口所有登录用户都可以访问，但可以选择性地：
- 管理员可以访问所有资源
- 普通用户只能访问自己创建的资源（通过 `created_by` 过滤）

#### 数据集 API
- `POST /api/v1/datasets` - 创建数据集
- `GET /api/v1/datasets` - 获取数据集列表
- `GET /api/v1/datasets/{id}` - 获取数据集详情
- `PUT /api/v1/datasets/{id}` - 更新数据集
- `DELETE /api/v1/datasets/{id}` - 删除数据集

#### 任务 API
- `POST /api/v1/tasks` - 创建任务
- `GET /api/v1/tasks` - 获取任务列表
- `GET /api/v1/tasks/{id}` - 获取任务详情
- `DELETE /api/v1/tasks/{id}` - 取消/删除任务

#### 评估器 API
- `POST /api/v1/evaluators` - 创建评估器
- `GET /api/v1/evaluators` - 获取评估器列表
- `GET /api/v1/evaluators/{id}` - 获取评估器详情
- `PUT /api/v1/evaluators/{id}` - 更新评估器
- `DELETE /api/v1/evaluators/{id}` - 删除评估器

#### 提示词 API
- `POST /api/v1/prompts` - 创建提示词
- `GET /api/v1/prompts` - 获取提示词列表
- `GET /api/v1/prompts/{id}` - 获取提示词详情
- `PUT /api/v1/prompts/{id}` - 更新提示词
- `DELETE /api/v1/prompts/{id}` - 删除提示词

#### 模型 API
- `POST /api/v1/models` - 创建模型配置
- `GET /api/v1/models` - 获取模型配置列表
- `GET /api/v1/models/{id}` - 获取模型配置详情
- `PUT /api/v1/models/{id}` - 更新模型配置
- `DELETE /api/v1/models/{id}` - 删除模型配置

#### 评估维度 API
- `GET /api/v1/metrics` - 获取维度列表
  - 所有用户可以看到：系统内置维度（is_global=true）
  - 用户还可以看到：自己创建的维度（created_by=当前用户）
  - 管理员可以看到：所有维度
- `GET /api/v1/metrics/{id}` - 获取维度详情
  - 系统内置维度：所有人可见
  - 自定义维度：仅创建者或管理员可见
- `POST /api/v1/metrics` - 创建自定义维度（所有登录用户）
- `PUT /api/v1/metrics/{id}` - 更新维度
  - 系统内置维度：仅管理员可以修改
  - 自定义维度：仅创建者或管理员可以修改
- `DELETE /api/v1/metrics/{id}` - 删除维度
  - 系统内置维度：不可删除
  - 自定义维度：仅创建者或管理员可以删除

---

## 5. 业务流程

### 5.1 系统初始化

```
1. 部署系统
   ↓
2. 运行数据库迁移
   ↓
3. 初始化管理员账号
   • 运行脚本: python scripts/init_admin.py
   • 创建管理员: username=admin, password=admin123
   ↓
4. 初始化系统内置维度
   • 运行脚本: python scripts/init_metrics.py
   • 创建全局维度 (is_global=true)
```

### 5.2 用户管理流程

```
管理员登录
   ↓
访问用户管理页面
   ↓
创建新用户
   • 输入用户名、邮箱、密码
   • 设置 is_admin（是否为管理员）
   ↓
用户创建成功
   ↓
（可选）编辑用户信息
   • 修改全名、头像
   • 启用/禁用账号
   • 修改管理员权限
   ↓
（可选）删除用户
   • 级联删除用户的所有资源
```

### 5.3 普通用户工作流程

```
用户登录
   ↓
上传数据集
   ↓
创建评估器
   • 选择评估维度
     - 系统内置维度（所有人可见）✓
     - 自己创建的自定义维度 ✓
   • 配置评估参数
   ↓
创建评估任务
   ↓
查看任务结果
   ↓
（可选）创建自定义维度
   • 自定义维度只有创建者和管理员可见
   • 系统内置维度对所有人可见，只有管理员可以修改
（可选）管理提示词模板
（可选）配置模型
```

### 5.4 资源可见性说明

| 资源类型 | 系统内置 | 用户创建 | 可见性规则 |
|---------|---------|---------|-----------|
| **评估维度** | is_global=true | is_global=false | • 系统内置：所有人可见<br>• 用户自定义：仅创建者和管理员可见 |
| **数据集** | - | created_by | • 创建者可见<br>• 管理员可见所有 |
| **评估器** | - | created_by | • 创建者可见<br>• 管理员可见所有 |
| **任务** | - | created_by | • 创建者可见<br>• 管理员可见所有 |
| **提示词** | - | created_by | • 创建者可见<br>• 管理员可见所有 |
| **模型配置** | - | created_by | • 创建者可见<br>• 管理员可见所有 |

---

## 6. 与原设计的对比

### 6.1 移除的复杂功能

| 原功能 | 简化方案 | 说明 |
|--------|---------|------|
| **Organizations（组织）** | ❌ 移除 | 不需要多租户隔离 |
| **Projects（项目）** | ❌ 移除 | 不需要项目级协作 |
| **OrganizationMember** | ❌ 移除 | 不需要组织成员关系 |
| **ProjectMember** | ❌ 移除 | 不需要项目成员关系 |
| **Roles（角色表）** | ❌ 移除 | 只保留 admin/user 两种角色 |
| **Permissions（权限表）** | ❌ 移除 | 简化为 is_admin 字段 |
| **RolePermissions** | ❌ 移除 | 不需要角色权限映射 |
| **用户注册** | ❌ 移除 | 只能由管理员创建用户 |
| **组织切换** | ❌ 移除 | 单一命名空间 |
| **项目切换** | ❌ 移除 | 单一命名空间 |
| **RBAC 中间件** | ✅ 简化 | 只需检查 is_admin |
| **行级安全策略** | ⚠️ 可选 | 可选择性实现资源所有权过滤 |

### 6.2 保留的核心功能

| 功能 | 实现方式 | 说明 |
|------|---------|------|
| **用户认证** | ✅ JWT Token | 保持不变 |
| **管理员权限** | ✅ is_admin 字段 | 简化为布尔标识 |
| **资源管理** | ✅ created_by 关联 | 跟踪创建者 |
| **数据集管理** | ✅ 完整保留 | 功能不变 |
| **任务管理** | ✅ 完整保留 | 功能不变 |
| **评估器管理** | ✅ 完整保留 | 功能不变 |
| **评估维度** | ✅ 全局+自定义 | is_global 标识（系统内置对所有人可见） |
| **提示词管理** | ✅ 完整保留 | 功能不变 |
| **模型管理** | ✅ 完整保留 | 功能不变 |
| **异步任务** | ✅ arq Worker | 功能不变 |

### 6.3 数据库表对比

**原设计（v2.0）**:
- users
- organizations ❌
- organization_members ❌
- projects ❌
- project_members ❌
- roles ❌
- permissions ❌
- role_permissions ❌
- datasets
- tasks
- evaluators
- metrics
- prompts
- models
- dataset_rows
- evaluation_results
- synthesis_results
- audit_logs

**简化设计（v3.0）**:
- users（添加 is_admin 字段）
- datasets（添加 created_by 字段）
- tasks（添加 created_by 字段）
- evaluators（添加 created_by 字段）
- metrics（添加 is_global 和 created_by 字段）
- prompts（添加 created_by 字段）
- models（添加 created_by 字段）
- dataset_rows
- evaluation_results
- synthesis_results
- audit_logs

**表数量**: 19 → 11 (减少 42%)

### 6.4 API 路由对比

**移除的路由**:
- `/api/v1/auth/register` - 注册（改为管理员创建）
- `/api/v1/organizations/*` - 组织管理
- `/api/v1/projects/*` - 项目管理
- `/api/v1/roles/*` - 角色管理
- `/api/v1/permissions/*` - 权限管理

**保留的路由**:
- `/api/v1/auth/login` - 登录
- `/api/v1/users/*` - 用户管理（仅管理员）
- `/api/v1/datasets/*` - 数据集管理
- `/api/v1/tasks/*` - 任务管理
- `/api/v1/evaluators/*` - 评估器管理
- `/api/v1/metrics/*` - 评估维度管理
- `/api/v1/prompts/*` - 提示词管理
- `/api/v1/models/*` - 模型管理
- `/api/v1/results/*` - 结果查询
- `/api/v1/statistics/*` - 统计信息

---

## 7. 迁移指南

### 7.1 从 v2.0 迁移到 v3.0

如果已经实现了 v2.0 的复杂架构，可以按以下步骤迁移：

#### 步骤 1：数据迁移
```sql
-- 1. 为 users 表添加 is_admin 字段
ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE NOT NULL;

-- 2. 将组织 owner 标记为管理员（可选）
UPDATE users SET is_admin = TRUE
WHERE id IN (SELECT owner_id FROM organizations);

-- 3. 为资源表添加 created_by 字段（如果没有）
ALTER TABLE datasets ADD COLUMN created_by UUID REFERENCES users(id);
ALTER TABLE tasks ADD COLUMN created_by UUID REFERENCES users(id);
ALTER TABLE evaluators ADD COLUMN created_by UUID REFERENCES users(id);
-- ... 其他表

-- 4. 迁移现有数据的创建者信息
-- （根据实际情况从 project_id 映射到 user_id）

-- 5. 为 metrics 表添加字段
ALTER TABLE metrics ADD COLUMN is_global BOOLEAN DEFAULT FALSE NOT NULL;
ALTER TABLE metrics ADD COLUMN created_by UUID REFERENCES users(id);

-- 6. 标记系统内置维度
UPDATE metrics SET is_global = TRUE WHERE created_by IS NULL;

-- 7. 删除多租户相关表（确保已备份！）
DROP TABLE IF EXISTS project_members;
DROP TABLE IF EXISTS projects;
DROP TABLE IF EXISTS organization_members;
DROP TABLE IF EXISTS organizations;
DROP TABLE IF EXISTS role_permissions;
DROP TABLE IF EXISTS permissions;
DROP TABLE IF EXISTS roles;
```

#### 步骤 2：代码修改

**移除的模块**:
- `models/organization.py`
- `models/project.py`
- `models/role.py`
- `schemas/organization.py`
- `schemas/project.py`
- `api/v1/organizations.py`
- `api/v1/projects.py`
- `api/v1/roles.py`
- `api/v1/permissions.py`
- `core/rbac.py`（如果存在）

**修改的模块**:

`models/user.py`:
```python
class User(Base):
    # ... 其他字段
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # 移除组织和项目关系
    # organization_memberships = ...
    # project_memberships = ...
```

`core/dependencies.py`:
```python
def require_admin(current_user: User = Depends(get_current_user)):
    """要求管理员权限"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user
```

`api/v1/users.py`:
```python
@router.post("", response_model=UserResponse, dependencies=[Depends(require_admin)])
async def create_user(...):
    """创建用户（仅管理员）"""
    ...
```

#### 步骤 3：前端修改

**移除的组件**:
- `TenancySelector.tsx` - 组织/项目选择器
- `ProjectGuard.tsx` - 项目权限守卫
- `contexts/TenancyContext.tsx` - 租户上下文

**简化的路由**:
```tsx
// 移除组织和项目相关页面
// 在用户管理中添加创建用户功能

// App.tsx
function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      
      {/* 管理员路由 */}
      <Route element={<AdminGuard />}>
        <Route path="/users" element={<Users />} />
      </Route>
      
      {/* 普通用户路由 */}
      <Route element={<AuthGuard />}>
        <Route path="/datasets" element={<Datasets />} />
        <Route path="/tasks" element={<Tasks />} />
        {/* ... */}
      </Route>
    </Routes>
  );
}
```

### 7.2 全新实现 v3.0

如果是从零开始实现，推荐以下步骤：

1. **数据库设置**
   ```bash
   # 创建数据库
   createdb diting_web
   
   # 运行迁移
   alembic upgrade head
   ```

2. **初始化管理员**
   ```bash
   python scripts/init_admin.py
   ```

3. **初始化系统维度**
   ```bash
   python scripts/init_metrics.py
   ```

4. **启动服务**
   ```bash
   # 启动后端
   uvicorn diting_web.main:app --reload
   
   # 启动 Worker
   python scripts/run_worker.py
   
   # 启动前端
   cd frontend && npm run dev
   ```

---

## 8. 总结

### 8.1 简化的优势

✅ **更简单的架构**:
- 表数量减少 42%
- 代码量减少约 40%
- 维护成本降低

✅ **更快的开发**:
- 不需要实现复杂的 RBAC
- 不需要组织/项目切换逻辑
- API 接口更直观

✅ **更好的性能**:
- 减少 JOIN 查询
- 减少权限检查开销
- 简化数据过滤

✅ **足够的灵活性**:
- 管理员可以管理所有用户
- 用户可以管理自己的资源
- 可以通过 created_by 实现资源隔离
- 系统内置资源（如评估维度）对所有人可见，降低重复配置

### 8.2 适用场景

**适合简化架构的场景**:
- 小型团队或个人使用
- 不需要多租户隔离
- 用户数量有限（< 100）
- 不需要复杂的权限控制
- 快速原型开发

**不适合简化架构的场景**:
- SaaS 多租户产品
- 需要严格的数据隔离
- 需要细粒度权限控制
- 大规模企业应用
- 需要按组织计费

### 8.3 可选的扩展方向

如果将来需要更多功能，可以逐步添加：

1. **用户组**：添加 `user_groups` 表，支持批量权限管理
2. **资源共享**：添加 `resource_shares` 表，支持用户间共享
3. **审计日志增强**：详细记录所有操作
4. **配额管理**：限制用户的资源数量
5. **工作空间**：轻量级的资源分组（不是完整的项目概念）

---

## 附录

### A. 初始化脚本

#### init_admin.py
```python
"""初始化管理员账号"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from diting_web.models.user import User
from diting_web.core.security import hash_password
from diting_web.config.settings import settings

async def init_admin():
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # 检查管理员是否存在
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        admin = result.scalar_one_or_none()
        
        if not admin:
            # 创建管理员
            admin = User(
                username="admin",
                email="admin@example.com",
                hashed_password=hash_password("admin123"),
                full_name="System Administrator",
                is_admin=True,
                is_active=True,
            )
            session.add(admin)
            await session.commit()
            print("✅ 管理员账号创建成功")
            print("   用户名: admin")
            print("   密码: admin123")
        else:
            print("ℹ️  管理员账号已存在")

if __name__ == "__main__":
    asyncio.run(init_admin())
```

#### init_metrics.py
```python
"""初始化系统内置评估维度"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from diting_web.models.metric import Metric
from diting_web.config.settings import settings

SYSTEM_METRICS = [
    {
        "name": "relevance",
        "display_name": "相关性",
        "description": "评估回答与问题的相关程度",
        "type": "llm_based",
        "config": {"weight": 1.0},
    },
    {
        "name": "accuracy",
        "display_name": "准确性",
        "description": "评估回答的事实准确性",
        "type": "llm_based",
        "config": {"weight": 1.0},
    },
    # ... 更多系统维度
]

async def init_metrics():
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        for metric_data in SYSTEM_METRICS:
            result = await session.execute(
                select(Metric).where(Metric.name == metric_data["name"])
            )
            metric = result.scalar_one_or_none()
            
            if not metric:
                metric = Metric(
                    **metric_data,
                    is_global=True,
                    created_by=None,
                )
                session.add(metric)
        
        await session.commit()
        print(f"✅ 初始化了 {len(SYSTEM_METRICS)} 个系统维度")

if __name__ == "__main__":
    asyncio.run(init_metrics())
```

---

**文档结束**

有任何问题或建议，请联系开发团队。

