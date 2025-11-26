# DiTing Web 生产环境部署文件总览

本文档列出了为生产环境部署创建的所有文件及其用途。

## 📁 文件结构

```
diting/
├── docker-compose.prod.yml           # 生产环境 Docker Compose 配置
├── env.production.template           # 环境变量配置模板
├── Makefile.prod                     # 生产环境 Makefile
├── .dockerignore                     # Docker 构建忽略文件
│
├── README-DEPLOYMENT.md              # 详细部署文档（推荐阅读）
├── QUICKSTART-PRODUCTION.md          # 快速部署指南
├── DEPLOYMENT-SUMMARY.md             # 本文件
│
└── docker/                           # Docker 相关配置目录
    ├── backend/
    │   └── Dockerfile                # Backend 生产环境 Dockerfile
    ├── worker/
    │   └── Dockerfile                # Worker 生产环境 Dockerfile
    ├── frontend/
    │   └── Dockerfile                # Frontend 生产环境 Dockerfile
    ├── nginx/
    │   ├── nginx.conf                # Nginx 主配置
    │   └── conf.d/
    │       └── default.conf          # 站点配置
    ├── redis/
    │   └── redis.conf                # Redis 生产配置
    ├── postgres/
    │   └── init/
    │       └── 01-init.sql           # PostgreSQL 初始化脚本
    └── scripts/
        └── deploy.sh                 # 部署管理脚本
```

## 📋 文件说明

### 核心配置文件

#### 1. `docker-compose.prod.yml`
**用途**: 生产环境 Docker Compose 配置文件  
**包含服务**:
- PostgreSQL 数据库
- Redis 缓存和任务队列
- MinIO 对象存储
- Backend API 服务
- ARQ Worker 服务
- Frontend Nginx 服务

**特点**:
- ✅ 健康检查配置
- ✅ 自动重启策略
- ✅ 资源限制
- ✅ 网络隔离
- ✅ 数据持久化

#### 2. `env.production.template`
**用途**: 环境变量配置模板  
**使用方法**:
```bash
cp env.production.template .env.production
vim .env.production  # 编辑配置
```

**必须修改的配置**:
- `JWT_SECRET_KEY`: JWT 密钥
- `POSTGRES_PASSWORD`: 数据库密码
- `MINIO_ROOT_PASSWORD`: MinIO 密码
- `ADMIN_PASSWORD`: 管理员密码
- `LLM_API_KEY`: LLM API 密钥
- `VITE_API_BASE_URL`: 前端 API 地址
- `CORS_ORIGINS`: CORS 允许的域名

### Dockerfile 文件

#### 3. `docker/backend/Dockerfile`
**用途**: Backend API 服务的生产环境镜像  
**特点**:
- 多阶段构建（builder + runtime）
- 使用 `uv` 包管理器（阿里云镜像）
- 非 root 用户运行
- 自动运行数据库迁移
- 自动初始化管理员和指标

**启动流程**:
1. 运行 Alembic 数据库迁移
2. 初始化评估指标
3. 初始化管理员账户
4. 启动 uvicorn 服务（4 workers）

#### 4. `docker/worker/Dockerfile`
**用途**: ARQ Worker 服务的生产环境镜像  
**特点**:
- 与 Backend 使用相同的依赖
- 支持水平扩展
- 资源限制配置
- 自动重试机制

**默认配置**:
- 最大并发任务: 10
- 任务超时: 3600 秒
- 支持多实例（默认 2 个）

#### 5. `docker/frontend/Dockerfile`
**用途**: Frontend 服务的生产环境镜像  
**特点**:
- 多阶段构建（Node.js build + Nginx runtime）
- 使用 pnpm 包管理器
- 生产环境优化
- Gzip 压缩
- 缓存策略

### Nginx 配置

#### 6. `docker/nginx/nginx.conf`
**用途**: Nginx 主配置文件  
**特点**:
- 性能优化（worker_connections, keepalive_timeout）
- Gzip 压缩
- 限流配置
- 上游服务器配置

#### 7. `docker/nginx/conf.d/default.conf`
**用途**: 站点配置文件  
**路由配置**:
- `/api/*` → Backend API
- `/api/v1/datasets/upload` → 文件上传（特殊配置）
- `/docs`, `/redoc` → API 文档
- `/` → 前端静态文件

**特点**:
- 安全头配置
- 静态资源缓存
- 文件上传大小限制（500MB）
- WebSocket 支持
- 限流保护

### 其他配置文件

#### 8. `docker/redis/redis.conf`
**用途**: Redis 生产环境配置  
**主要配置**:
- 最大内存: 2GB
- 内存淘汰策略: allkeys-lru
- 持久化: RDB + AOF
- 最大客户端: 10000

#### 9. `docker/postgres/init/01-init.sql`
**用途**: PostgreSQL 初始化脚本  
**功能**:
- 创建必要的扩展（uuid-ossp, pg_trgm）
- 设置时区
- 授予权限

#### 10. `docker/scripts/deploy.sh`
**用途**: 部署管理脚本  
**功能**:
- 启动/停止/重启服务
- 查看日志和状态
- 备份数据
- 健康检查

**使用方法**:
```bash
# 在 Linux 环境中需要先赋予执行权限
chmod +x docker/scripts/deploy.sh

# 使用命令
./docker/scripts/deploy.sh start    # 启动
./docker/scripts/deploy.sh stop     # 停止
./docker/scripts/deploy.sh logs     # 日志
./docker/scripts/deploy.sh status   # 状态
./docker/scripts/deploy.sh backup   # 备份
```

#### 11. `Makefile.prod`
**用途**: 简化部署操作  
**常用命令**:
```bash
make -f Makefile.prod init       # 初始化配置
make -f Makefile.prod start      # 启动服务
make -f Makefile.prod stop       # 停止服务
make -f Makefile.prod logs       # 查看日志
make -f Makefile.prod status     # 查看状态
make -f Makefile.prod backup     # 备份数据
make -f Makefile.prod upgrade    # 升级系统
make -f Makefile.prod health     # 健康检查
```

#### 12. `.dockerignore`
**用途**: Docker 构建时忽略的文件  
**忽略内容**:
- Git 相关文件
- 文档和 Markdown
- 测试文件
- IDE 配置
- 日志文件
- 备份文件

### 文档文件

#### 13. `README-DEPLOYMENT.md`
**用途**: 详细的生产环境部署文档  
**内容**:
- 系统架构说明
- 硬件和软件要求
- 详细的配置说明
- 各服务的配置
- 运维管理指南
- 安全加固建议
- 性能优化技巧
- 故障排查指南
- 监控和告警

#### 14. `QUICKSTART-PRODUCTION.md`
**用途**: 快速部署指南  
**内容**:
- 10 分钟快速部署步骤
- 最简配置说明
- 常用命令速查
- 快速故障排查

## 🚀 快速开始

### 方法 1: 使用 Makefile（推荐）

```bash
# 1. 初始化配置
make -f Makefile.prod init

# 2. 编辑配置文件
vim .env.production

# 3. 启动服务
make -f Makefile.prod start

# 4. 查看状态
make -f Makefile.prod status
```

### 方法 2: 使用部署脚本

```bash
# 1. 复制配置模板
cp env.production.template .env.production

# 2. 编辑配置
vim .env.production

# 3. 赋予执行权限（Linux）
chmod +x docker/scripts/deploy.sh

# 4. 启动服务
./docker/scripts/deploy.sh start
```

### 方法 3: 直接使用 Docker Compose

```bash
# 1. 复制配置
cp env.production.template .env.production

# 2. 编辑配置
vim .env.production

# 3. 构建并启动
docker compose -f docker-compose.prod.yml --env-file .env.production build
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

## 📊 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| Frontend | 80 | 前端界面 |
| Frontend (SSL) | 443 | HTTPS（需配置证书） |
| Backend API | 8000 | API 服务 |
| PostgreSQL | 5432 | 数据库（建议不暴露） |
| Redis | 6379 | 缓存（建议不暴露） |
| MinIO API | 9000 | 对象存储 API |
| MinIO Console | 9001 | MinIO 管理界面 |

## 🔒 安全检查清单

部署后请确认：

- [ ] 已修改 `JWT_SECRET_KEY`
- [ ] 已修改 `POSTGRES_PASSWORD`
- [ ] 已修改 `MINIO_ROOT_PASSWORD`
- [ ] 已修改 `ADMIN_PASSWORD`
- [ ] 已配置 `LLM_API_KEY`
- [ ] 已修改默认端口（可选）
- [ ] 已配置防火墙
- [ ] 已配置 SSL 证书（推荐）
- [ ] 已设置自动备份
- [ ] 已配置域名和 CORS

## 📦 Docker Volumes

生产环境创建的持久化卷：

| Volume | 用途 |
|--------|------|
| `postgres_data` | PostgreSQL 数据 |
| `redis_data` | Redis 数据 |
| `minio_data` | MinIO 对象存储 |
| `backend_logs` | Backend 日志 |
| `worker_logs` | Worker 日志 |
| `frontend_logs` | Nginx 日志 |

## 🔧 常见操作

### 查看日志
```bash
# 所有服务
make -f Makefile.prod logs

# 特定服务
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f worker
```

### 备份数据
```bash
# 使用 Makefile
make -f Makefile.prod backup

# 使用脚本
./docker/scripts/deploy.sh backup
```

### 健康检查
```bash
# 使用 Makefile
make -f Makefile.prod health

# 使用脚本
./docker/scripts/deploy.sh status
```

### 升级系统
```bash
# 使用 Makefile（包含自动备份）
make -f Makefile.prod upgrade

# 手动升级
git pull
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d
```

## 📖 更多信息

- **详细部署文档**: [README-DEPLOYMENT.md](README-DEPLOYMENT.md)
- **快速部署指南**: [QUICKSTART-PRODUCTION.md](QUICKSTART-PRODUCTION.md)
- **项目主页**: https://github.com/your-org/diting
- **问题反馈**: https://github.com/your-org/diting/issues

## 🆘 获取帮助

如果遇到问题：

1. 查看 [详细部署文档](README-DEPLOYMENT.md)
2. 查看 [故障排查指南](README-DEPLOYMENT.md#故障排查)
3. 查看服务日志
4. 提交 Issue
5. 联系技术支持: team@diting.ai

---

**部署愉快！** 🎉

