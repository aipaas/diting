# 🚀 DiTing Web - Windows 本地调试指南

> **适用于**: Windows 10/11 + PowerShell + 远程服务器已部署 PostgreSQL/Redis/MinIO

---

## ⚡ 快速开始（3分钟）

### 方式一：自动配置（推荐新手）

```powershell
# 1. 打开 PowerShell，进入项目目录
cd D:\pythonProject\aicoding\diting\diting\packages\diting-web\backend

# 2. 运行自动配置脚本
.\setup_local_env.ps1
```

**脚本会自动完成**:
- ✅ 引导你输入远程服务器信息
- ✅ 生成 `.env` 配置文件
- ✅ 安装 Python 依赖
- ✅ 执行数据库迁移
- ✅ 初始化管理员账号和评估指标

**你需要准备**:
- 远程服务器 IP 地址
- PostgreSQL 用户名/密码
- Redis 密码（如果有）
- MinIO Access Key/Secret Key
- OpenAI API Key

---

### 方式二：手动配置（推荐有经验的开发者）

#### 1️⃣ 创建后端配置文件

```powershell
cd D:\pythonProject\aicoding\diting\diting\packages\diting-web\backend

# 复制并编辑配置文件
copy .env.example .env
notepad .env
```

**修改以下内容为你的实际配置**:

```env
# PostgreSQL - 修改为你的远程服务器
DATABASE_URL=postgresql+asyncpg://admin:password@192.168.1.100:5432/diting_web

# Redis - 修改为你的远程服务器
REDIS_URL=redis://:your_password@192.168.1.100:6379/0
# 如果没有密码: redis://192.168.1.100:6379/0

# MinIO - 修改为你的远程服务器
MINIO_ENDPOINT=192.168.1.100:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# LLM API（必需）
LLM_API_KEY=sk-your-actual-openai-api-key
EMBEDDING_API_KEY=sk-your-actual-openai-api-key
```

#### 2️⃣ 安装依赖

```powershell
# 确保已安装 uv
pip install uv

# 安装项目依赖
uv sync
```

#### 3️⃣ 测试连接

```powershell
# 测试远程服务连接
uv run python test_remote_connection.py
```

**如果测试失败，请检查**:
- 远程服务器是否运行
- 防火墙端口是否开放（5432, 6379, 9000）
- 网络是否连通: `ping 192.168.1.100`

#### 4️⃣ 初始化数据库

```powershell
# 数据库迁移
uv run alembic upgrade head

# 初始化管理员（默认 admin/admin123）
uv run python -m diting_web.scripts.init_admin

# 初始化评估指标
uv run python -m diting_web.scripts.init_metrics
```

#### 5️⃣ 启动服务

**终端 1 - 启动后端 API**:
```powershell
cd D:\pythonProject\aicoding\diting\diting\packages\diting-web\backend
uv run uvicorn diting_web.main:app --reload --host 0.0.0.0 --port 8000
```

**终端 2 - 启动 Worker（新 PowerShell 窗口）**:
```powershell
cd D:\pythonProject\aicoding\diting\diting\packages\diting-web\backend
.\run_worker.ps1
```

**终端 3 - 启动前端（新 PowerShell 窗口，可选）**:
```powershell
cd D:\pythonProject\aicoding\diting\diting\packages\diting-web\frontend

# 首次运行需要安装依赖
pnpm install

# 启动开发服务器
pnpm dev
```

---

## 🎯 验证安装

### 1. 后端 API

打开浏览器访问:
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/api/v1/healthz

**测试登录**:
```powershell
# 使用 curl (Windows 10+ 自带) 或在 Swagger UI 中测试
curl -X POST http://localhost:8000/api/v1/auth/login `
  -H "Content-Type: application/json" `
  -d '{"username":"admin","password":"admin123"}'
```

### 2. 前端界面

打开浏览器: http://localhost:5173

### 3. 检查服务状态

```powershell
# 查看正在运行的服务
Get-Process | Where-Object {$_.ProcessName -match "uvicorn|python"}

# 查看端口占用
netstat -ano | findstr "8000"
netstat -ano | findstr "5173"
```

---

## 🛠️ Windows 常见问题

### Q1: PowerShell 脚本无法运行

**错误**: "无法加载文件，因为在此系统上禁止运行脚本"

**解决方案**:
```powershell
# 以管理员身份运行 PowerShell，执行:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 然后重新运行脚本
```

### Q2: uv 命令未找到

```powershell
# 安装 uv
pip install uv

# 如果 pip 也没有，先安装 Python 3.11+
# 下载: https://www.python.org/downloads/
```

### Q3: pnpm 命令未找到

```powershell
# 先安装 Node.js (v18+)
# 下载: https://nodejs.org/

# 然后安装 pnpm
npm install -g pnpm
```

### Q4: 端口被占用

```powershell
# 查找占用端口的进程
netstat -ano | findstr "8000"

# 终止进程 (PID 是上一步看到的进程ID)
taskkill /PID <PID> /F

# 或者修改端口
# 编辑 backend/.env 文件:
# PORT=8001
```

### Q5: 无法连接远程数据库

**检查防火墙**:
```powershell
# 测试连接
Test-NetConnection -ComputerName 192.168.1.100 -Port 5432
Test-NetConnection -ComputerName 192.168.1.100 -Port 6379
Test-NetConnection -ComputerName 192.168.1.100 -Port 9000
```

**如果连接失败，需要在远程服务器上**:
1. 开放防火墙端口
2. 配置服务允许远程访问（见下文）

---

## 🔐 远程服务器配置（Linux）

如果无法连接，需要在远程服务器上配置:

### PostgreSQL 配置

```bash
# SSH 登录远程服务器
ssh user@192.168.1.100

# 编辑配置文件
sudo nano /etc/postgresql/16/main/postgresql.conf
# 找到并修改:
listen_addresses = '*'

sudo nano /etc/postgresql/16/main/pg_hba.conf
# 添加:
host    all    all    0.0.0.0/0    md5

# 重启服务
sudo systemctl restart postgresql

# 开放防火墙（Ubuntu/Debian）
sudo ufw allow 5432/tcp
```

### Redis 配置

```bash
sudo nano /etc/redis/redis.conf
# 修改:
bind 0.0.0.0
protected-mode no

# 重启服务
sudo systemctl restart redis

# 开放防火墙
sudo ufw allow 6379/tcp
```

### MinIO 配置

```bash
# 如果使用 Docker
docker run -d \
  -p 9000:9000 \
  -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  -v /data/minio:/data \
  --name minio \
  minio/minio server /data --console-address ":9001"

# 开放防火墙
sudo ufw allow 9000/tcp
sudo ufw allow 9001/tcp
```

---

## 🔒 安全建议：使用 SSH 隧道（推荐）

相比直接暴露数据库端口，使用 SSH 隧道更安全:

### 1. 安装 SSH 客户端（Windows 10+ 自带）

```powershell
# 检查 SSH 是否可用
ssh -V
```

### 2. 建立 SSH 隧道

```powershell
# 在 PowerShell 中运行（保持窗口打开）
ssh -L 5432:localhost:5432 `
    -L 6379:localhost:6379 `
    -L 9000:localhost:9000 `
    user@192.168.1.100
```

### 3. 修改 .env 使用本地端口

```env
DATABASE_URL=postgresql+asyncpg://admin:password@localhost:5432/diting_web
REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000
```

这样所有流量都通过加密的 SSH 隧道传输，更安全！

---

## 📊 开发工作流

### 日常开发流程

```powershell
# 1. 启动 SSH 隧道（如果使用）
ssh -L 5432:localhost:5432 -L 6379:localhost:6379 -L 9000:localhost:9000 user@remote_ip

# 2. 启动后端（新窗口）
cd D:\pythonProject\aicoding\diting\diting\packages\diting-web\backend
uv run uvicorn diting_web.main:app --reload

# 3. 启动 Worker（新窗口）
cd D:\pythonProject\aicoding\diting\diting\packages\diting-web\backend
.\run_worker.ps1

# 4. 启动前端（新窗口，可选）
cd D:\pythonProject\aicoding\diting\diting\packages\diting-web\frontend
pnpm dev
```

### 代码修改后

- **后端修改**: 自动重载（如果使用 `--reload`）
- **前端修改**: 自动热更新
- **Worker 修改**: 需要手动重启 Worker

### 数据库修改

```powershell
cd backend

# 1. 修改 models/*.py 文件
# 2. 生成迁移脚本
uv run alembic revision --autogenerate -m "描述你的修改"

# 3. 应用迁移
uv run alembic upgrade head
```

---

## 🎨 使用 VS Code 开发

### 推荐扩展

- Python (Microsoft)
- Pylance
- TypeScript Vue Plugin (Volar)
- ESLint
- Prettier

### 配置 launch.json

创建 `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Backend: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "diting_web.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
      ],
      "cwd": "${workspaceFolder}/packages/diting-web/backend",
      "envFile": "${workspaceFolder}/packages/diting-web/backend/.env"
    },
    {
      "name": "Backend: Worker",
      "type": "python",
      "request": "launch",
      "module": "diting_web.scripts.run_worker",
      "cwd": "${workspaceFolder}/packages/diting-web/backend",
      "envFile": "${workspaceFolder}/packages/diting-web/backend/.env"
    }
  ]
}
```

然后按 `F5` 即可启动调试！

---

## 📚 快速参考

### 常用命令

```powershell
# 后端
cd backend
uv run uvicorn diting_web.main:app --reload    # 启动 API
.\run_worker.ps1                                # 启动 Worker
uv run alembic upgrade head                     # 数据库迁移
uv run python test_remote_connection.py        # 测试连接

# 前端
cd frontend
pnpm install                                    # 安装依赖
pnpm dev                                        # 启动开发服务器
pnpm build                                      # 构建生产版本

# 测试
cd backend
pytest tests/                                   # 运行测试

# 代码格式化
ruff format .                                   # 格式化代码
ruff check .                                    # 检查代码
```

### 重要端口

- **8000**: 后端 API
- **5173**: 前端开发服务器
- **5432**: PostgreSQL (远程)
- **6379**: Redis (远程)
- **9000**: MinIO API (远程)
- **9001**: MinIO 控制台 (远程)

### 默认账号

- **管理员**: admin / admin123
- **MinIO**: minioadmin / minioadmin

---

## 🎉 启动成功！

访问以下地址开始使用:

- 🌐 **后端 API 文档**: http://localhost:8000/docs
- 🎨 **前端界面**: http://localhost:5173
- 📦 **MinIO 控制台**: http://远程IP:9001

---

## 📖 更多资源

- **完整文档**: [LOCAL_SETUP.md](./LOCAL_SETUP.md)
- **快速开始**: [QUICK_START_LOCAL.md](./QUICK_START_LOCAL.md)
- **后端 README**: [backend/README.md](./backend/README.md)
- **问题反馈**: 查看项目 Issues

---

**祝开发顺利！** 🚀

遇到问题？运行测试脚本诊断:
```powershell
cd backend
uv run python test_remote_connection.py
```

