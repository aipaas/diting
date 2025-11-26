# Redis 生产环境镜像
FROM redis:7-alpine

# 复制Redis配置文件到镜像中
COPY packages/diting-web/docker/redis/redis.conf /usr/local/etc/redis/redis.conf

# 暴露端口
EXPOSE 6379

# 使用配置文件启动Redis
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]
