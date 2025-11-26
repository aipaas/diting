# DiTing Web 后端快速启动指南

## 🚀 快速开始（5分钟）

### 1. 启动基础设施（PostgreSQL, Redis, MinIO）

```bash
# 使用 Docker Compose 启动所有依赖服务
docker-compose up -d

# 等待服务启动完成（约10秒）
docker-compose ps
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 使用默认配置即可，或根据需要修改
# 默认配置已经配置好了 Docker Compose 的服务地址
```

### 3. 安装依赖

```bash
# 使用 uv 安装依赖（推荐）
uv sync

# 或使用 pip
pip install -e .
```

### 4. 初始化数据库

```bash
# 运行数据库迁移
make migrate

# 或手动运行
alembic upgrade head

# 初始化管理员和内置指标
make init-db

# 或手动运行
python -m diting_web.scripts.init_admin
python -m diting_web.scripts.init_metrics
```

### 5. 启动应用

```bash
# 方式1：使用 Makefile（推荐）
make run

# 方式2：直接运行
python -m diting_web.main

# 方式3：使用 uvicorn（支持热重载）
uvicorn diting_web.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. 启动 Worker（可选）

在另一个终端窗口中：

```bash
# 启动 ARQ worker 处理异步任务
make worker

# 或手动运行
python -m diting_web.workers.worker
```

## ✅ 验证安装

### 访问 API 文档

打开浏览器访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 测试登录

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

成功后会返回：
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "access_token": "eyJhbGc...",
    "token_type": "bearer",
    "expires_in": 86400
  }
}
```

### 测试健康检查

```bash
curl http://localhost:8000/api/v1/healthz
```

## 📝 常用命令

```bash
# 开发相关
make install      # 安装依赖
make dev          # 安装开发依赖
make run          # 运行应用
make worker       # 运行 worker

# 数据库相关
make migrate      # 运行迁移
make init-db      # 初始化数据库

# 代码质量
make lint         # 代码检查
make format       # 代码格式化
make test         # 运行测试

# 清理
make clean        # 清理生成文件
```

## 🔧 故障排查

### 问题1: 数据库连接失败

```bash
# 检查 PostgreSQL 是否运行
docker-compose ps postgres

# 查看日志
docker-compose logs postgres

# 重启服务
docker-compose restart postgres
```

### 问题2: Redis 连接失败

```bash
# 检查 Redis 是否运行
docker-compose ps redis

# 测试 Redis 连接
redis-cli ping
```

### 问题3: Alembic 迁移失败

```bash
# 查看当前迁移状态
alembic current

# 回滚到初始状态
alembic downgrade base

# 重新运行迁移
alembic upgrade head
```

### 问题4: 端口冲突

如果 8000 端口被占用，修改 `.env` 文件：
```env
PORT=8001
```

## 🎯 下一步

1. **创建评估器**：访问 `/docs` → `POST /api/v1/evaluators`
2. **上传数据集**：访问 `/docs` → `POST /api/v1/datasets`
3. **运行评估任务**：访问 `/docs` → `POST /api/v1/tasks/evaluations`
4. **查看统计数据**：访问 `/docs` → `GET /api/v1/statistics/dashboard`

## 📚 更多文档

- [完整 README](./README.md)
- [API 设计文档](../docs/BACKEND_DESIGN.md)
- [实施指南](../docs/IMPLEMENTATION_TODO.md)

## 🆘 获取帮助

如有问题，请查看：
1. API 文档：http://localhost:8000/docs
2. 日志输出：应用启动时会输出详细日志
3. Docker 日志：`docker-compose logs -f`

