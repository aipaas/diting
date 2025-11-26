# ==================== Stage 1: Builder ====================
FROM python:3.11-slim-bookworm AS builder

ARG UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

# 配置 Debian 腾讯云镜像源
RUN sed -i 's|deb.debian.org|mirrors.tencent.com|g' /etc/apt/sources.list.d/debian.sources || \
    sed -i 's|deb.debian.org|mirrors.tencent.com|g' /etc/apt/sources.list

# 安装 uv (快速的 Python 包管理器)
COPY --from=ghcr.io/astral-sh/uv:0.7.17 /uv /uvx /bin/

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY pyproject.toml uv.lock ./
COPY packages ./packages

# 安装依赖
RUN --mount=type=cache,target=/root/.cache/uv \
    UV_INDEX_URL=${UV_INDEX_URL} \
    uv sync --frozen --no-install-workspace --no-install-project --no-editable --no-dev

# 同步项目
RUN --mount=type=cache,target=/root/.cache/uv \
    UV_INDEX_URL=${UV_INDEX_URL} \
    uv sync --frozen --package diting-web --no-editable --no-dev

# ==================== Stage 2: Runtime ====================
FROM python:3.11-slim-bookworm

# 配置 Debian 腾讯云镜像源
RUN sed -i 's|deb.debian.org|mirrors.tencent.com|g' /etc/apt/sources.list.d/debian.sources || \
    sed -i 's|deb.debian.org|mirrors.tencent.com|g' /etc/apt/sources.list

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN groupadd -r diting && useradd -r -g diting diting

# 设置工作目录
WORKDIR /app

# 从 builder 复制虚拟环境和项目代码
COPY --from=builder --chown=diting:diting /app/.venv /app/.venv
COPY --from=builder --chown=diting:diting /app/packages /app/packages

# 添加虚拟环境到 PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/packages/diting-web/backend/src"

# 创建日志目录
RUN mkdir -p /app/logs && chown -R diting:diting /app/logs

# 切换到非 root 用户
USER diting

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["sh", "-c", "\
    cd /app/packages/diting-web/backend && \
    python -c 'from diting_web.db.session import init_db; import asyncio; asyncio.run(init_db())' && \
    python -m diting_web.scripts.init_db_extensions && \
    alembic stamp head && \
    python -m diting_web.scripts.init_metrics && \
    python -m diting_web.scripts.init_admin && \
    uvicorn diting_web.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --log-level info \
        --access-log \
        --use-colors \
    "]

