# DiTing Web 本地开发指南

本指南介绍如何在本地环境调试 diting-web，使用 Docker 运行基础设施，本地运行应用代码。

## 🏗️ 架构说明

```
┌─────────────────────────────────────────┐
│  本地开发机器                            │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ 前端 (本地运行)                  │   │
│  │ pnpm dev  →  :5173              │   │
│  └─────────────┬───────────────────┘   │
│                │                        │
│  ┌─────────────▼───────────────────┐   │
│  │ 后端 (本地运行)                  │   │
│  │ uvicorn   →  :8000              │   │
│  └─────────────┬───────────────────┘   │
│                │                        │
│  ┌─────────────▼───────────────────┐   │
│  │ Worker (本地运行)                │   │
│  │ arq worker                      │   │
│  └─────────────┬───────────────────┘   │
│                │                        │
└────────────────┼────────────────────────┘
                 │
    ┌────────────▼────────────┐
    │  Docker 容器 (基础设施)  │
    │                         │
    │  • PostgreSQL  :5432    │
    │  • Redis       :6379    │
    │  • MinIO       :9000    │
    └─────────────────────────┘
```

## 📋 前置要求

- Python 3.11+
- Node.js 20+ 和 pnpm
- Docker 和 Docker Compose
- uv (Python 包管理器)

## 🚀 快速开始

### 第一步：启动基础设施

```bash
# 进入项目目录
cd diting/packages/diting-web

# 启动基础设施容器（PostgreSQL, Redis, MinIO）
docker-compose -f docker-compose.dev.yml up -d

# 检查容器状态
docker-compose -f docker-compose.dev.yml ps

# 查看日志
docker-compose -f docker-compose.dev.yml logs -f
```

### 第二步：配置环境变量

```bash
# 在 backend 目录创建 .env 文件
cd backend
cp .env.example .env

# 编辑 .env 文件
nano .env
```

**本地开发环境变量配置**：

```bash
# 应用配置
ENVIRONMENT=development
DEBUG=true
HOST=0.0.0.0
PORT=8000

# 数据库（连接到 Docker 容器）
DATABASE_URL=postgresql+asyncpg://admin:password@localhost:5432/diting_web
DATABASE_ECHO=true

# Redis（连接到 Docker 容器）
REDIS_URL=redis://localhost:6379/0

# MinIO（连接到 Docker 容器）
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
MINIO_BUCKET_NAME=diting-datasets

# JWT 认证
JWT_SECRET_KEY=dev-secret-key-not-for-production
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# 管理员账号
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123

# LLM 配置（必需）
DEFAULT_LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-openai-api-key

# Embedding 配置（必需）
DEFAULT_EMBEDDING_MODEL=text-embedding-ada-002
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_API_KEY=sk-your-openai-api-key

# CORS（允许前端开发服务器）
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# 日志
LOG_LEVEL=DEBUG
LOG_FORMAT=console
```

### 第三步：安装后端依赖

```bash
# 在 backend 目录
cd diting/packages/diting-web/backend

# 使用 uv 安装依赖
uv sync

# 或使用 pip
pip install -e .
```

### 第四步：初始化数据库

```bash
# 确保在 backend 目录
cd diting/packages/diting-web/backend

# 运行数据库迁移
uv run alembic upgrade head

# 初始化管理员账号
uv run python -m diting_web.scripts.init_admin

# 初始化内置指标
uv run python -m diting_web.scripts.init_metrics
```

### 第五步：启动后端服务

**终端 1 - 启动 API 服务**：

```bash
cd diting/packages/diting-web/backend

# 方式 1: 使用 uvicorn 直接运行（推荐开发）
uv run uvicorn diting_web.main:app --reload --port 8000

# 方式 2: 使用 Python 模块运行
uv run python -m diting_web.main
```

**终端 2 - 启动 Worker**：

```bash
cd diting/packages/diting-web/backend

# Linux/macOS
bash run_worker.sh

# Windows
.\run_worker.ps1

# 或直接运行
uv run python -m diting_web.scripts.run_worker
```

### 第六步：启动前端

**终端 3 - 启动前端开发服务器**：

```bash
cd diting/packages/diting-web/frontend

# 安装依赖（首次）
pnpm install

# 启动开发服务器
pnpm dev
```

### 第七步：验证

- 前端: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs
- MinIO 控制台: http://localhost:9001

默认账号：
- 用户名: `admin`
- 密码: `admin123`

## 🔧 开发工作流

### 修改后端代码

后端使用 `--reload` 模式运行，修改代码后会自动重启。

```bash
# 查看后端日志
# 在运行 uvicorn 的终端可以直接看到输出
```

### 修改前端代码

前端使用 Vite HMR，修改后自动热更新，无需刷新浏览器。

```bash
# Vite 会自动检测文件变化并热更新
```

### 数据库操作

```bash
# 创建新的迁移
cd backend
uv run alembic revision --autogenerate -m "描述你的修改"

# 应用迁移
uv run alembic upgrade head

# 回滚迁移
uv run alembic downgrade -1

# 查看迁移历史
uv run alembic history
```

### 连接到数据库

```bash
# 方式 1: 使用 Docker exec
docker-compose -f docker-compose.dev.yml exec postgres \
  psql -U admin -d diting_web

# 方式 2: 使用本地 psql
psql postgresql://admin:password@localhost:5432/diting_web

# 常用 SQL 命令
\dt              # 查看所有表
\d table_name    # 查看表结构
SELECT * FROM tasks LIMIT 10;  # 查询数据
```

### 查看 Redis 队列

```bash
# 连接到 Redis
docker-compose -f docker-compose.dev.yml exec redis redis-cli

# 或本地连接
redis-cli

# 常用命令
KEYS arq:*              # 查看所有 ARQ 队列
LLEN arq:queue          # 查看队列长度
LRANGE arq:queue 0 -1   # 查看队列内容
```

### 访问 MinIO

浏览器访问: http://localhost:9001

- 用户名: `minioadmin`
- 密码: `minioadmin`

## 🧪 运行测试

### 后端测试

```bash
cd backend

# 运行所有测试
uv run pytest

# 运行特定测试文件
uv run pytest tests/services/test_metric_service.py

# 运行并查看覆盖率
uv run pytest --cov=diting_web --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### 代码检查

```bash
cd backend

# 格式化代码
uv run ruff format .

# 代码检查
uv run ruff check .

# 自动修复
uv run ruff check --fix .

# 类型检查
uv run mypy .
```

## 📊 监控和调试

### 查看基础设施日志

```bash
# 所有容器日志
docker-compose -f docker-compose.dev.yml logs -f

# PostgreSQL 日志
docker-compose -f docker-compose.dev.yml logs -f postgres

# Redis 日志
docker-compose -f docker-compose.dev.yml logs -f redis

# MinIO 日志
docker-compose -f docker-compose.dev.yml logs -f minio
```

### 调试后端

在代码中添加断点：

```python
# 使用 Python 调试器
import pdb; pdb.set_trace()

# 或使用 ipdb（更友好）
import ipdb; ipdb.set_trace()
```

### VS Code 调试配置

创建 `.vscode/launch.json`：

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "diting_web.main:app",
        "--reload",
        "--port",
        "8000"
      ],
      "jinja": true,
      "justMyCode": false,
      "cwd": "${workspaceFolder}/backend"
    }
  ]
}
```

## 🛠️ 常用命令

### 基础设施管理

```bash
# 启动基础设施
docker-compose -f docker-compose.dev.yml up -d

# 停止基础设施
docker-compose -f docker-compose.dev.yml down

# 停止并删除所有数据
docker-compose -f docker-compose.dev.yml down -v

# 重启某个服务
docker-compose -f docker-compose.dev.yml restart postgres

# 查看服务状态
docker-compose -f docker-compose.dev.yml ps

# 查看资源使用
docker stats
```

### 数据库重置

```bash
# 完全重置数据库
cd backend

# 1. 删除所有表
uv run alembic downgrade base

# 2. 重新创建
uv run alembic upgrade head

# 3. 重新初始化
uv run python -m diting_web.scripts.init_admin
uv run python -m diting_web.scripts.init_metrics
```

### 清理和重建

```bash
# 停止所有服务
docker-compose -f docker-compose.dev.yml down -v

# 重新启动
docker-compose -f docker-compose.dev.yml up -d

# 等待服务就绪
sleep 5

# 重新初始化数据库
cd backend
uv run alembic upgrade head
uv run python -m diting_web.scripts.init_admin
uv run python -m diting_web.scripts.init_metrics
```

## 🐛 常见问题

### 问题 1: 无法连接到 PostgreSQL

```bash
# 检查容器是否运行
docker-compose -f docker-compose.dev.yml ps postgres

# 检查端口是否被占用
lsof -i :5432  # Linux/macOS
netstat -ano | findstr :5432  # Windows

# 测试连接
psql postgresql://admin:password@localhost:5432/diting_web
```

### 问题 2: Worker 无法连接 Redis

```bash
# 检查 Redis 是否运行
docker-compose -f docker-compose.dev.yml ps redis

# 测试连接
redis-cli ping

# 检查 .env 中的 REDIS_URL
cat backend/.env | grep REDIS_URL
```

### 问题 3: 前端无法连接后端

```bash
# 检查后端是否运行
curl http://localhost:8000/api/v1/healthz

# 检查 CORS 配置
# 确保 .env 中的 CORS_ORIGINS 包含 http://localhost:5173
```

### 问题 4: MinIO 连接失败

```bash
# 检查 MinIO 是否运行
docker-compose -f docker-compose.dev.yml ps minio

# 访问 MinIO 控制台
open http://localhost:9001

# 检查 bucket 是否存在
# 如果不存在，MinIO Client 会自动创建
```

## 📚 相关文档

- [后端 README](backend/README.md)
- [前端 README](frontend/README.md)
- [完整部署指南](README_DEPLOYMENT.md)
- [架构设计](docs/BACKEND_DESIGN.md)

## 💡 开发提示

1. **使用热重载**: 后端和前端都支持热重载，修改代码后自动生效
2. **查看日志**: 开发模式下日志格式为 console，便于阅读
3. **API 文档**: 访问 http://localhost:8000/docs 查看和测试 API
4. **数据持久化**: Docker volumes 保存数据，即使重启容器数据也不会丢失
5. **端口冲突**: 如果端口被占用，修改 docker-compose.dev.yml 中的端口映射

## 🆘 获取帮助

- 📧 Email: team@diting.ai
- 🐛 Issues: https://github.com/your-org/diting/issues

---

**最后更新**: 2025-10-26  
**版本**: v1.0.0

