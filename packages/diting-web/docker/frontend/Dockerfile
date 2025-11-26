# ==================== Stage 1: Builder ====================
FROM node:20-alpine AS builder

ARG VITE_API_BASE_URL=http://localhost:8000

WORKDIR /app

# 安装 pnpm
RUN npm install -g pnpm

# 复制前端项目
COPY packages/diting-web/frontend/package.json packages/diting-web/frontend/pnpm-lock.yaml ./

# 安装依赖
RUN pnpm install --frozen-lockfile

# 复制源代码
COPY packages/diting-web/frontend ./

# 构建前端
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN pnpm build

# ==================== Stage 2: Runtime ====================
FROM nginx:1.25-alpine

# 安装 curl 用于健康检查
RUN apk add --no-cache curl

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 Nginx 配置
COPY docker/nginx/nginx.conf /etc/nginx/nginx.conf
COPY docker/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf

# 创建健康检查页面
RUN echo 'OK' > /usr/share/nginx/html/health

# 暴露端口
EXPOSE 80 443

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# 启动 Nginx
CMD ["nginx", "-g", "daemon off;"]

