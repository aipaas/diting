#!/bin/bash

# ==================== DiTing Web 生产环境部署脚本 ====================
# 用途：一键部署 DiTing Web 到生产环境
# 使用方法：./docker/scripts/deploy.sh [start|stop|restart|logs|status]

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$PROJECT_ROOT"

# 配置文件
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查环境配置
check_env() {
    log_info "检查环境配置..."
    
    if [ ! -f "$ENV_FILE" ]; then
        log_error "环境配置文件 $ENV_FILE 不存在！"
        log_info "请先复制 .env.production.example 为 $ENV_FILE 并修改配置"
        exit 1
    fi
    
    # 检查必需的环境变量
    source "$ENV_FILE"
    
    if [ "$JWT_SECRET_KEY" = "your_secure_jwt_secret_key_here_CHANGE_ME" ]; then
        log_error "请修改 JWT_SECRET_KEY 为安全的密钥！"
        log_info "生成方式: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        exit 1
    fi
    
    if [ "$POSTGRES_PASSWORD" = "your_secure_postgres_password_here" ]; then
        log_warning "请修改 POSTGRES_PASSWORD 为安全的密码！"
    fi
    
    log_success "环境配置检查通过"
}

# 检查 Docker 和 Docker Compose
check_docker() {
    log_info "检查 Docker 环境..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装！请先安装 Docker"
        exit 1
    fi
    
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose 未安装或版本过低！请安装 Docker Compose v2+"
        exit 1
    fi
    
    log_success "Docker 环境检查通过"
}

# 启动服务
start_services() {
    log_info "启动 DiTing Web 服务..."
    
    # 构建镜像
    log_info "构建 Docker 镜像..."
    log_info "1/4 构建 Redis 镜像..."
    docker build -f packages/diting-web/docker/redis/Dockerfile -t diting-redis:latest .
    log_info "2/4 构建 Backend 镜像..."
    docker build -f packages/diting-web/docker/backend/Dockerfile -t diting-backend:latest .
    log_info "3/4 构建 Worker 镜像..."
    docker build -f packages/diting-web/docker/worker/Dockerfile -t diting-worker:latest .
    log_info "4/4 构建 Frontend 镜像..."
    docker build -f packages/diting-web/docker/frontend/Dockerfile -t diting-frontend:latest .
    
    # 启动服务
    log_info "启动服务..."
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d
    
    # 等待服务就绪
    log_info "等待服务就绪..."
    sleep 10
    
    # 检查服务状态
    check_health
    
    log_success "DiTing Web 服务启动成功！"
    log_info "访问地址："
    log_info "  - 前端: http://localhost:${FRONTEND_PORT:-80}"
    log_info "  - API 文档: http://localhost:${BACKEND_PORT:-8000}/docs"
    log_info "  - MinIO 控制台: http://localhost:${MINIO_CONSOLE_PORT:-9001}"
}

# 停止服务
stop_services() {
    log_info "停止 DiTing Web 服务..."
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down
    log_success "服务已停止"
}

# 重启服务
restart_services() {
    log_info "重启 DiTing Web 服务..."
    stop_services
    start_services
}

# 查看日志
view_logs() {
    log_info "查看服务日志（按 Ctrl+C 退出）..."
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs -f
}

# 检查服务健康状态
check_health() {
    log_info "检查服务健康状态..."
    
    services=("postgres" "redis" "minio" "backend" "worker" "frontend")
    
    for service in "${services[@]}"; do
        status=$(docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps -q "$service" 2>/dev/null)
        if [ -z "$status" ]; then
            log_error "$service: 未运行"
        else
            health=$(docker inspect --format='{{.State.Health.Status}}' $(docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps -q "$service" 2>/dev/null) 2>/dev/null || echo "N/A")
            if [ "$health" = "healthy" ] || [ "$health" = "N/A" ]; then
                log_success "$service: 运行中 (健康状态: $health)"
            else
                log_warning "$service: 运行中 (健康状态: $health)"
            fi
        fi
    done
}

# 清理数据（危险操作）
clean_data() {
    log_warning "⚠️  此操作将删除所有数据（数据库、Redis、MinIO）！"
    read -p "确定要继续吗？(yes/no): " confirm
    
    if [ "$confirm" = "yes" ]; then
        log_info "停止服务并清理数据..."
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down -v
        log_success "数据已清理"
    else
        log_info "操作已取消"
    fi
}

# 备份数据
backup_data() {
    log_info "备份数据..."
    
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # 备份数据库
    log_info "备份 PostgreSQL 数据库..."
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres \
        pg_dump -U "${POSTGRES_USER:-diting}" "${POSTGRES_DB:-diting_web}" \
        > "$BACKUP_DIR/database.sql"
    
    # 备份 MinIO 数据
    log_info "备份 MinIO 数据..."
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T minio \
        mc mirror --overwrite /data "$BACKUP_DIR/minio" || true
    
    log_success "备份完成: $BACKUP_DIR"
}

# 显示帮助信息
show_help() {
    cat << EOF
DiTing Web 生产环境部署脚本

用法: $0 [命令]

命令:
  start       启动所有服务
  stop        停止所有服务
  restart     重启所有服务
  logs        查看服务日志
  status      查看服务状态
  backup      备份数据
  clean       清理所有数据（危险操作）
  help        显示此帮助信息

示例:
  $0 start     # 启动服务
  $0 logs      # 查看日志
  $0 status    # 查看状态

更多信息请访问: https://github.com/your-org/diting
EOF
}

# 主函数
main() {
    case "${1:-help}" in
        start)
            check_docker
            check_env
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        logs)
            view_logs
            ;;
        status)
            check_health
            ;;
        backup)
            backup_data
            ;;
        clean)
            clean_data
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"

