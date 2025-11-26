# Diting-Web

> DiTing Web 是 DiTing LLM 评估框架的 Web 应用层，提供完整的任务管理、数据持久化和实时通知功能。

## 📁 项目结构

```
diting-web/
├── backend/                   # Python 后端
│   ├── src/diting_web/        # Python 包
│   └── pyproject.toml         # Python 配置
│
├── frontend/                  # React 前端
│   ├── src/                   # 前端源码
│   └── package.json           # Node.js 配置
│
├── docker/                    # Docker 配置
│   └── docker-compose.yml
│
├── docs/                      # 文档
│   ├── START_HERE.md          # 快速开始
│   ├── BACKEND_DESIGN.md      # 完整后端设计
│   ├── FINAL_ARCHITECTURE.md  # 最终架构
│   └── API_REFERENCE.md       # API 文档
│
└── README.md                  # 本文档
```

---

## 🎯 核心特性

- ✅ **完全异步架构** - FastAPI + SQLAlchemy 2.0 + arq
- ✅ **直接使用 SDK** - 导入 diting-core 和 diting-server
- ✅ **服务独立** - 与 diting-server HTTP 服务完全解耦
- ✅ **数据持久化** - PostgreSQL 存储（7张表）
- ✅ **实时通知** - WebSocket 推送任务状态
- ✅ **对象存储** - MinIO 管理数据集文件

---

## 🏗️ 系统架构

```
┌──────────────────┐
│   diting-core    │  核心算法 SDK
└────────┬─────────┘
         │
         ↓ pip install
┌──────────────────┐
│  diting-server   │  服务层 + HTTP 服务
│  • 服务层代码    │  ← diting-web 导入这个
│  • HTTP API      │  ← 其他平台调用这个
└────────┬─────────┘
         │
         ↓ pip install  
┌──────────────────┐
│   diting-web     │  Web 应用
│  • React 前端    │
│  • FastAPI 后端  │
│  • PostgreSQL    │
│  • Redis + arq   │
└──────────────────┘
```

---

## 🛠️ 技术栈

### 后端

| 组件 | 技术 | 版本 |
|------|------|------|
| 核心 SDK | diting-core | workspace |
| 服务层 | diting-server | workspace |
| Web 框架 | FastAPI | ≥0.115.0 |
| 数据库 | PostgreSQL | ≥16.0 |
| ORM | SQLAlchemy | ≥2.0.0 |
| 任务队列 | arq | ≥0.25.0 |
| 缓存 | Redis | ≥7.0 |
| WebSocket | python-socketio | ≥5.11.0 |
| 认证 | python-jose | ≥3.3.0 |

### 前端

| 组件 | 技术 | 版本 |
|------|------|------|
| UI 框架 | React | 19.2.0 |
| 语言 | TypeScript | 5.9.3 |
| 构建工具 | Vite | 7.1.12 |
| CSS 框架 | Tailwind CSS | 4.1.16 |
| 组件库 | daisyUI | 5.3.8 |
| 路由 | React Router | 7.9.4 |
| HTTP 客户端 | Axios | 1.12.2 |

---

## 🚀 快速开始

### 1. 安装后端依赖

```bash
cd backend
pip install -e .
```

### 2. 安装前端依赖

```bash
cd frontend
pnpm install
```

### 3. 启动基础设施

```bash
# 在项目根目录
docker-compose up -d  # PostgreSQL + Redis + MinIO
```

### 4. 数据库迁移

```bash
cd backend
alembic upgrade head
```

### 5. 启动服务

```bash
# 终端 1: 后端 API
cd backend
uvicorn diting_web.main:app --reload --port 8000

# 终端 2: arq Worker
cd backend
arq diting_web.worker.WorkerSettings

# 终端 3: 前端
cd frontend
pnpm dev
```

### 6. 访问

- 前端: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

---

## 📚 文档

所有文档位于 `docs/` 目录：

| 文档 | 说明 |
|------|------|
| [START_HERE.md](docs/START_HERE.md) | 快速入门指南 |
| [BACKEND_DESIGN.md](docs/BACKEND_DESIGN.md) | 完整后端设计（数据库、API、Schema） |
| [FINAL_ARCHITECTURE.md](docs/FINAL_ARCHITECTURE.md) | 最终架构方案 |
| [API_REFERENCE.md](docs/API_REFERENCE.md) | API 接口文档 |

**推荐阅读顺序**：
1. docs/START_HERE.md (5分钟)
2. docs/BACKEND_DESIGN.md (30分钟) ⭐
3. docs/FINAL_ARCHITECTURE.md (20分钟)

---

## 🔑 核心理解

### diting-web 如何使用 diting-server？

```python
# ✅ 正确：导入服务层代码（函数调用）
from diting_server.services.evaluation_service import evaluation_service

async def run_evaluation_task(ctx, task_id, config):
    result = await evaluation_service.run_evaluation(request)
    return result

# ❌ 错误：HTTP 调用
async with httpx.AsyncClient() as client:
    response = await client.post('http://diting-server/...')
```

### 依赖关系

```
diting-web
    ├── diting-core      (核心算法)
    └── diting-server    (服务层代码)
```

---

## 📄 许可证

MIT License

---

## 📞 联系方式

- 📧 Email: team@diting.ai
- 🐛 Issues: https://github.com/your-org/diting/issues

---

**版本**: v3.2.0  
**最后更新**: 2024-01-20
