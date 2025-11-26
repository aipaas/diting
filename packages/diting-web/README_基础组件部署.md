# 基础组件 Docker Compose 部署指南

本文档说明如何启动基础设施组件（PostgreSQL、Redis、MinIO）用于本地开发调试 diting-web。

## 📦 包含的组件

- **PostgreSQL 16** - 数据库 (端口 5432)
- **Redis 7** - 缓存和任务队列 (端口 6379)
- **MinIO** - 对象存储 (端口 9000/9001)

## 🚀 快速启动

### 方式 1: 使用 docker-compose.yml（推荐）

```bash
cd diting/packages/diting-web/backend

# 启动所有基础组件
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 方式 2: 使用 docker-compose.dev.yml

```bash
cd diting/packages/diting-web

# 启动所有基础组件
docker-compose -f docker-compose.dev.yml up -d

# 查看服务状态
docker-compose -f docker-compose.dev.yml ps

# 查看日志
docker-compose -f docker-compose.dev.yml logs -f
```

## 📋 连接信息

### PostgreSQL
```
Host:     localhost
Port:     5432
Database: diting_web
User:     admin
Password: password

连接字符串:
postgresql://admin:password@localhost:5432/diting_web
postgresql+asyncpg://admin:password@localhost:5432/diting_web
```

### Redis
```
Host: localhost
Port: 6379
URL:  redis://localhost:6379/0
```

### MinIO
```
API 端口:     http://localhost:9000
控制台:       http://localhost:9001

Access Key:   minioadmin
Secret Key:   minioadmin

Bucket:       diting-datasets (自动创建)
```

## 🔧 后端环境变量配置

在 `backend/.env` 文件中使用以下配置：

```bash
# 数据库
DATABASE_URL=postgresql+asyncpg://admin:password@localhost:5432/diting_web

# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
MINIO_BUCKET_NAME=diting-datasets
```

## 📝 本地开发流程

### 1. 启动基础组件

```bash
cd diting/packages/diting-web/backend
docker-compose up -d
```

### 2. 初始化数据库

```bash
cd diting/packages/diting-web/backend

# 运行迁移
uv run alembic upgrade head

# 初始化管理员
uv run python -m diting_web.scripts.init_admin

# 初始化指标
uv run python -m diting_web.scripts.init_metrics
```

### 3. 启动后端服务

```bash
# 终端 1: API 服务
cd diting/packages/diting-web/backend
uv run uvicorn diting_web.main:app --reload --port 8000

# 终端 2: Worker
cd diting/packages/diting-web/backend
uv run python -m diting_web.scripts.run_worker
```

### 4. 启动前端服务

```bash
# 终端 3: 前端
cd diting/packages/diting-web/frontend
pnpm dev
```

## 🛠️ 常用命令

### 查看服务状态
```bash
docker-compose ps
```

### 查看日志
```bash
# 所有服务
docker-compose logs -f

# 特定服务
docker-compose logs -f postgres
docker-compose logs -f redis
docker-compose logs -f minio
```

### 连接到数据库
```bash
# 方式 1: 通过 Docker
docker-compose exec postgres psql -U admin -d diting_web

# 方式 2: 本地 psql
psql postgresql://admin:password@localhost:5432/diting_web
```

### 连接到 Redis
```bash
# 方式 1: 通过 Docker
docker-compose exec redis redis-cli

# 方式 2: 本地 redis-cli
redis-cli
```

### 访问 MinIO 控制台
浏览器打开: http://localhost:9001

- 用户名: `minioadmin`
- 密码: `minioadmin`

## 🔄 管理命令

### 停止服务
```bash
docker-compose down
```

### 重启服务
```bash
docker-compose restart
```

### 停止并删除所有数据
```bash
# ⚠️ 警告：这会删除所有数据！
docker-compose down -v
```

### 重启单个服务
```bash
docker-compose restart postgres
docker-compose restart redis
docker-compose restart minio
```

## 🐛 故障排查

### PostgreSQL 无法连接

```bash
# 检查容器状态
docker-compose ps postgres

# 查看日志
docker-compose logs postgres

# 测试连接
docker-compose exec postgres pg_isready -U admin

# 检查端口占用
lsof -i :5432  # Linux/macOS
netstat -ano | findstr :5432  # Windows
```

### Redis 无法连接

```bash
# 检查容器状态
docker-compose ps redis

# 测试连接
docker-compose exec redis redis-cli ping

# 应该返回: PONG
```

### MinIO 无法访问

```bash
# 检查容器状态
docker-compose ps minio

# 查看日志
docker-compose logs minio

# 测试健康状态
curl http://localhost:9000/minio/health/live
```

## 📊 数据持久化

数据会持久化到 Docker volumes：

```bash
# 查看 volumes
docker volume ls | grep diting

# 应该看到：
# postgres_data
# redis_data
# minio_data

# 删除所有数据
docker-compose down -v
```

## 💡 开发提示

1. **数据持久化**: 即使停止容器，数据也会保留在 Docker volumes 中
2. **快速重置**: 使用 `docker-compose down -v && docker-compose up -d` 快速重置环境
3. **查看日志**: 开发时保持日志窗口打开 `docker-compose logs -f`
4. **健康检查**: 所有服务都配置了健康检查，确保服务就绪后再启动应用

## 📚 更多信息

- [完整本地开发指南](LOCAL_DEV_GUIDE.md)
- [后端 README](backend/README.md)
- [完整部署指南](README_DEPLOYMENT.md)

---

**最后更新**: 2025-10-26

