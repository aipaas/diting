# DiTing Web Backend

**版本**: v1.0.0  
**状态**: 🚀 Production Ready  
**Python**: 3.11+

---

## 📖 项目简介

DiTing Web Backend 是 DiTing LLM 评估平台的 Web 后端服务，提供完整的 RESTful API、数据管理和任务调度功能。

### 核心特性

- ✅ **完整的 CRUD API** - 指标、评估器、数据集、任务管理
- ✅ **数据集文件处理** - CSV/Excel/JSONL 解析和MinIO存储
- ✅ **JWT 认证** - 安全的 API 访问
- ✅ **面向对象架构** - Service 层分离业务逻辑
- ✅ **MinIO 对象存储** - 文件上传下载管理
- ✅ **ARQ 任务队列** - 异步任务处理和实时进度追踪
- ✅ **diting-core 集成** - 7种评估指标 + QA合成器

---

## 🏗️ 架构设计

```
┌────────────────────────────────────────────────────┐
│                  API Layer (FastAPI)               │
│            请求验证 + 响应格式化                    │
│                 + 依赖注入                         │
├────────────────────────────────────────────────────┤
│              Service Layer (OO Classes)            │
│  ✅ MetricService        ✅ EvaluatorService      │
│  ✅ DatasetService       ✅ StatisticsService     │
│            业务逻辑 + 数据库操作                    │
├────────────────────────────────────────────────────┤
│                  Utility Layer                     │
│  ✅ DatasetParser (CSV/Excel/JSONL)               │
│  ✅ MinIOClient (文件存储)                        │
├────────────────────────────────────────────────────┤
│             Database Layer (SQLAlchemy)            │
│         8个表 + 关系 + 索引 + 约束                 │
└────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 1. 启动基础设施（5分钟快速部署）

```bash
# 进入项目目录
cd diting/packages/diting-web/backend

# 使用 Docker Compose 启动所有依赖服务（PostgreSQL, Redis, MinIO）
docker-compose up -d

# 等待服务启动完成（约10秒）
docker-compose ps
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，配置必要的参数（可选使用交互式脚本）
nano .env

# 或使用交互式配置向导（Windows）
.\setup_local_env.ps1
```

**关键配置**:
```bash
# LLM配置（必需）
DEFAULT_LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-your-openai-api-key

# Embedding配置（必需）
DEFAULT_EMBEDDING_MODEL=text-embedding-ada-002
EMBEDDING_API_KEY=sk-your-openai-api-key

# 数据库
DATABASE_URL=postgresql+asyncpg://admin:password@localhost:5432/diting_web

# Redis
REDIS_URL=redis://localhost:6379/0
```

### 3. 安装依赖并初始化数据库

```bash
# 安装依赖
uv sync

# 数据库迁移
uv run alembic upgrade head

# 初始化管理员（默认用户名：admin，密码：admin123）
uv run python -m diting_web.scripts.init_admin

# 初始化内置指标
uv run python -m diting_web.scripts.init_metrics

# 或使用 Makefile 一键初始化
make init-db
```

### 4. 启动服务

**Linux/Mac:**
```bash
# Terminal 1: 启动API服务（开发模式）
./run_web.sh

# Terminal 2: 启动ARQ Worker（处理后台任务）
./run_worker.sh

# 或使用 Makefile
make run      # Terminal 1
make worker   # Terminal 2
```

**Windows:**
```powershell
# Terminal 1: 启动API服务（开发模式）
.\run_web.ps1

# Terminal 2: 启动ARQ Worker（处理后台任务）
.\run_worker.ps1
```

### 5. 验证安装

```bash
# 健康检查
curl http://localhost:8000/api/v1/healthz

# 测试登录
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 查看API文档
# 浏览器打开: http://localhost:8000/docs
```

### 6. 常用命令

```bash
# 开发相关
make install      # 安装依赖
make run          # 运行API服务
make worker       # 运行Worker

# 数据库相关
make migrate      # 运行数据库迁移
make init-db      # 初始化数据库（管理员+指标）

# 代码质量
make lint         # 代码检查
make format       # 代码格式化
make test         # 运行测试

# 清理
make clean        # 清理生成文件
```

### 7. 故障排查

**问题1: 数据库连接失败**
```bash
docker-compose ps postgres     # 检查PostgreSQL状态
docker-compose logs postgres   # 查看日志
docker-compose restart postgres # 重启服务
```

**问题2: Redis连接失败**
```bash
docker-compose ps redis        # 检查Redis状态
redis-cli ping                 # 测试连接
```

**问题3: 端口冲突**
如果8000端口被占用，修改`.env`文件中的`PORT=8001`

---

## 📚 API 文档

### 核心端点

#### 认证
- `POST /api/v1/auth/login` - 登录获取token

#### 指标管理
- `POST /api/v1/metrics` - 创建指标
- `GET /api/v1/metrics` - 获取指标列表
- `GET /api/v1/metrics/{id}` - 获取指标详情
- `PUT /api/v1/metrics/{id}` - 更新指标
- `DELETE /api/v1/metrics/{id}` - 删除指标

#### 评估器管理
- `POST /api/v1/evaluators` - 创建评估器
- `GET /api/v1/evaluators` - 获取评估器列表
- `GET /api/v1/evaluators/{id}` - 获取评估器详情
- `PUT /api/v1/evaluators/{id}` - 更新评估器
- `DELETE /api/v1/evaluators/{id}` - 删除评估器

#### 数据集管理 ✨
- `POST /api/v1/datasets` - 上传数据集（CSV/Excel/JSONL）
- `GET /api/v1/datasets` - 获取数据集列表
- `GET /api/v1/datasets/{id}` - 获取数据集详情
- `GET /api/v1/datasets/{id}/download` - 获取下载URL（新）
- `GET /api/v1/datasets/{id}/preview` - 预览数据（新）
- `DELETE /api/v1/datasets/{id}` - 删除数据集

#### 任务管理
- `POST /api/v1/tasks/evaluations` - 创建评估任务
- `POST /api/v1/tasks/synthesis` - 创建合成任务
- `POST /api/v1/tasks/batch-evaluations` - 批量评估
- `GET /api/v1/tasks` - 获取任务列表
- `GET /api/v1/tasks/{id}` - 获取任务详情
- `POST /api/v1/tasks/{id}/cancel` - 取消任务

#### 统计信息
- `GET /api/v1/statistics/dashboard` - 仪表板统计

---

## 🧪 使用示例

### 1. 登录获取Token
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | jq -r '.data.access_token')
```

### 2. 上传CSV数据集
```bash
# 创建测试文件
echo "name,age,city
Alice,30,Beijing
Bob,25,Shanghai" > test.csv

# 上传
curl -X POST http://localhost:8000/api/v1/datasets \
  -H "Authorization: Bearer $TOKEN" \
  -F "name=Test Dataset" \
  -F "file=@test.csv"
```

### 3. 预览数据
```bash
DATASET_ID="your-dataset-id"

curl http://localhost:8000/api/v1/datasets/$DATASET_ID/preview \
  -H "Authorization: Bearer $TOKEN" | jq
```

### 4. 下载数据集
```bash
# 获取下载URL
DOWNLOAD_URL=$(curl -s http://localhost:8000/api/v1/datasets/$DATASET_ID/download \
  -H "Authorization: Bearer $TOKEN" | jq -r '.data.download_url')

# 下载文件
wget "$DOWNLOAD_URL" -O downloaded.csv
```

---

## 🛠️ 开发指南

### 项目结构

```
backend/
├── src/diting_web/
│   ├── api/v1/           # API路由
│   ├── services/         # 业务逻辑层（OO）
│   ├── models/           # SQLAlchemy模型
│   ├── schemas/          # Pydantic模式
│   ├── utils/            # 工具类
│   │   ├── dataset_parser.py    # CSV/Excel/JSONL解析
│   │   └── minio_client.py      # MinIO客户端
│   ├── core/             # 核心功能
│   ├── common/           # 公共模块
│   ├── config/           # 配置
│   ├── db/               # 数据库
│   ├── scripts/          # 初始化脚本
│   └── workers/          # ARQ任务
├── alembic/              # 数据库迁移
├── tests/                # 测试
└── pyproject.toml        # 项目配置
```

### 添加新功能

#### 1. 创建 Service 类
```python
# services/my_service.py
class MyService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def do_something(self, data):
        # 业务逻辑
        ...
```

#### 2. 添加依赖注入
```python
# core/dependencies.py
def get_my_service(db: Annotated[AsyncSession, Depends(get_db)]):
    return MyService(db)
```

#### 3. 创建 API 端点
```python
# api/v1/my_endpoints.py
@router.post("")
async def create(
    data: MySchema,
    service: Annotated[MyService, Depends(get_my_service)],
    current_user: Annotated[AdminUser, Depends(get_current_user)],
):
    result = await service.do_something(data)
    return success_response(data=result)
```

### 代码规范

- **格式化**: `ruff format .`
- **Lint**: `ruff check .`
- **类型检查**: `mypy .`
- **测试**: `pytest tests/`

---

## 📦 依赖包

### 核心依赖
- FastAPI 0.115.0+ - Web框架
- SQLAlchemy 2.0+ - 异步ORM
- PostgreSQL 16+ - 数据库
- Redis 7+ - 缓存和队列
- MinIO 7.2+ - 对象存储

### 数据处理
- Pandas 2.0+ - 数据分析
- openpyxl 3.1+ - Excel支持

### 认证和安全
- python-jose - JWT
- passlib - 密码加密

完整依赖列表见 `pyproject.toml`

---

## 🐳 Docker 部署

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:16
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: diting_web
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: password

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    command: server /data --console-address ":9001"
```

启动：
```bash
docker-compose up -d
```

---

## 📊 开发进度

```
项目整体进度: ████████████████████ 100% 🎉

✅ Phase 1: 基础架构 (100%)
✅ Phase 2: Service层OO + 解析器 (100%)
✅ Phase 3: MinIO集成 (100%)
✅ Phase 4: ARQ任务队列 (100%)
✅ Phase 5: diting-core集成 (100%)
✅ Phase 6: 测试+优化 (100%)

🚀 项目已完成，可投入生产使用！
```

---

## 📝 更多文档

- [架构设计文档](./ARCHITECTURE.md) - 分层架构和设计原则
- [后端设计文档](../docs/DESIGN.md) - 完整的数据库和API设计
- [Metric API使用指南](./METRIC_API_GUIDE.md) - 评估维度API详细说明
- [变更日志](./CHANGELOG.md) - 版本更新记录

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 开发流程
1. Fork 项目
2. 创建特性分支
3. 提交代码
4. 运行测试
5. 提交 PR

---

## 📄 许可证

MIT License

---

## 👥 团队

DiTing Team

---

**最后更新**: 2025-10-24  
**版本**: v1.0.0  
**状态**: 🚀 Production Ready
