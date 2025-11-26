# 生产环境快速部署指南

本指南帮助你在 10 分钟内完成 DiTing Web 生产环境的部署。

## 一、准备工作

### 1. 检查系统要求

- ✅ Linux 系统（Ubuntu 20.04+ / CentOS 8+）
- ✅ Docker 24.0+
- ✅ Docker Compose v2.20+
- ✅ 至少 8GB 内存和 50GB 磁盘空间

### 2. 安装 Docker（如未安装）

**Ubuntu/Debian**:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker
```

**验证安装**:
```bash
docker --version
docker compose version
```

## 二、配置环境

### 1. 克隆项目

```bash
git clone https://github.com/your-org/diting.git
cd diting
```

### 2. 创建环境配置文件

```bash
# 复制配置模板
cp env.production.template .env.production

# 生成 JWT 密钥
python3 -c 'import secrets; print(f"JWT_SECRET_KEY={secrets.token_urlsafe(32)}")' >> .env.production
```

### 3. 编辑配置文件

```bash
vim .env.production
```

**必须修改的配置**:

```bash
# 数据库密码（必改）
POSTGRES_PASSWORD=your_secure_password_123

# MinIO 密码（必改）
MINIO_ROOT_PASSWORD=your_secure_minio_password_123

# 管理员密码（必改）
ADMIN_PASSWORD=your_admin_password_123

# LLM API 密钥（必改）
LLM_API_KEY=sk-your-openai-api-key

# 域名配置（必改）
VITE_API_BASE_URL=http://your-domain.com
CORS_ORIGINS=["http://your-domain.com","https://your-domain.com"]
```

## 三、部署服务

### 方式 1: 使用部署脚本（推荐）

```bash
# 赋予执行权限
chmod +x docker/scripts/deploy.sh

# 启动服务
./docker/scripts/deploy.sh start
```

### 方式 2: 直接使用 Docker Compose

```bash
# 构建镜像
docker compose -f docker-compose.prod.yml --env-file .env.production build

# 启动服务
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

## 四、验证部署

### 1. 检查服务状态

```bash
# 查看所有服务
docker compose -f docker-compose.prod.yml ps

# 或使用脚本
./docker/scripts/deploy.sh status
```

期望输出：
```
NAME                 STATUS       HEALTH
diting-postgres      Up           healthy
diting-redis         Up           healthy
diting-minio         Up           healthy
diting-backend       Up           healthy
diting-worker        Up
diting-frontend      Up           healthy
```

### 2. 查看日志

```bash
# 查看所有服务日志
./docker/scripts/deploy.sh logs

# 查看特定服务
docker compose -f docker-compose.prod.yml logs -f backend
```

### 3. 访问服务

打开浏览器访问：

- **前端界面**: http://your-domain.com
- **API 文档**: http://your-domain.com:8000/docs
- **MinIO 控制台**: http://your-domain.com:9001

### 4. 登录系统

默认管理员账号：
- **用户名**: `admin` 
- **密码**: 你在 `.env.production` 中设置的 `ADMIN_PASSWORD`

## 五、常用命令

```bash
# 启动服务
./docker/scripts/deploy.sh start

# 停止服务
./docker/scripts/deploy.sh stop

# 重启服务
./docker/scripts/deploy.sh restart

# 查看日志
./docker/scripts/deploy.sh logs

# 查看状态
./docker/scripts/deploy.sh status

# 备份数据
./docker/scripts/deploy.sh backup
```

## 六、故障排查

### 问题 1: 服务无法启动

```bash
# 查看详细错误
docker compose -f docker-compose.prod.yml logs

# 检查端口占用
sudo netstat -tulpn | grep -E '80|443|5432|6379|8000|9000|9001'
```

### 问题 2: 数据库连接失败

```bash
# 测试数据库连接
docker compose -f docker-compose.prod.yml exec postgres \
  psql -U diting -d diting_web -c "SELECT version();"
```

### 问题 3: 前端无法访问

```bash
# 检查 Nginx 配置
docker compose -f docker-compose.prod.yml exec frontend nginx -t

# 重启前端服务
docker compose -f docker-compose.prod.yml restart frontend
```

### 问题 4: Worker 不执行任务

```bash
# 查看 Worker 日志
docker compose -f docker-compose.prod.yml logs worker

# 检查 Redis 连接
docker compose -f docker-compose.prod.yml exec redis redis-cli ping
```

## 七、性能优化建议

### 1. 调整 Worker 数量

编辑 `.env.production`:
```bash
WORKER_REPLICAS=4  # 根据任务负载调整
```

重启服务:
```bash
./docker/scripts/deploy.sh restart
```

### 2. 增加 Backend Workers

编辑 `docker/backend/Dockerfile`，修改启动命令：
```dockerfile
CMD ["uvicorn", "diting_web.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "8"]  # 增加 worker 数量
```

重新构建：
```bash
docker compose -f docker-compose.prod.yml build backend
docker compose -f docker-compose.prod.yml up -d backend
```

### 3. 数据库性能优化

根据服务器内存调整 PostgreSQL 配置（在 `docker-compose.prod.yml`）:

```yaml
# 16GB 内存服务器推荐配置
postgres:
  command:
    - "-c"
    - "shared_buffers=4GB"
    - "-c"
    - "effective_cache_size=12GB"
```

## 八、安全加固

### 1. 修改默认端口

编辑 `.env.production`:
```bash
BACKEND_PORT=8888      # 修改 Backend 端口
POSTGRES_PORT=5433     # 修改数据库端口
REDIS_PORT=6380        # 修改 Redis 端口
```

### 2. 启用防火墙

**Ubuntu/Debian**:
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

**CentOS/RHEL**:
```bash
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 3. 启用 HTTPS

参见 [README-DEPLOYMENT.md](README-DEPLOYMENT.md#sslhttps-配置)

## 九、备份策略

### 自动备份

```bash
# 设置定时备份（每天凌晨 2 点）
crontab -e

# 添加以下行
0 2 * * * cd /path/to/diting && ./docker/scripts/deploy.sh backup
```

### 手动备份

```bash
# 备份所有数据
./docker/scripts/deploy.sh backup

# 备份文件位置
ls -lh backups/
```

## 十、升级系统

```bash
# 1. 备份数据
./docker/scripts/deploy.sh backup

# 2. 拉取最新代码
git pull origin main

# 3. 重新构建镜像
docker compose -f docker-compose.prod.yml build --no-cache

# 4. 启动服务
docker compose -f docker-compose.prod.yml up -d

# 5. 运行数据库迁移
docker compose -f docker-compose.prod.yml exec backend \
  alembic upgrade head
```

## 十一、监控和维护

### 查看资源使用

```bash
# 查看容器资源使用
docker stats

# 查看磁盘使用
df -h
docker system df
```

### 清理磁盘空间

```bash
# 清理未使用的 Docker 资源
docker system prune -a

# 清理旧的备份文件（保留最近 30 天）
find backups/ -mtime +30 -delete
```

### 设置监控告警

推荐使用以下工具：
- **Prometheus + Grafana**: 指标监控
- **Uptime Kuma**: 可用性监控
- **Sentry**: 错误追踪

## 十二、获取帮助

如果遇到问题：

1. 查看详细部署文档: [README-DEPLOYMENT.md](README-DEPLOYMENT.md)
2. 查看日志: `./docker/scripts/deploy.sh logs`
3. 提交 Issue: https://github.com/your-org/diting/issues
4. 联系技术支持: team@diting.ai

## 检查清单

部署完成后，请确认以下事项：

- [ ] 所有服务都在运行（`./docker/scripts/deploy.sh status`）
- [ ] 可以访问前端界面
- [ ] 可以登录管理员账号
- [ ] API 文档可以访问
- [ ] 已修改所有默认密码
- [ ] 已配置 LLM API 密钥
- [ ] 已设置自动备份
- [ ] 已启用防火墙
- [ ] 已配置域名（如需要）
- [ ] 已配置 SSL 证书（如需要）

---

**祝部署顺利！** 🎉

如有问题，欢迎查阅 [完整部署文档](README-DEPLOYMENT.md) 或联系技术支持。

