-- DiTing Web 数据库初始化脚本

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 设置时区
SET timezone = 'UTC';

-- 注意: pg_stat_statements 扩展需要在 postgresql.conf 中预加载
-- 在标准 Docker 镜像中默认未启用,跳过创建以避免错误
-- 如需启用,需在 docker-compose.yml 中配置:
-- command: -c shared_preload_libraries=pg_stat_statements

-- 授予权限
GRANT ALL PRIVILEGES ON DATABASE diting_web TO diting;
GRANT ALL ON ALL TABLES IN SCHEMA public TO diting;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO diting;

-- 打印初始化完成信息
DO $$
BEGIN
    RAISE NOTICE 'DiTing Web database initialized successfully!';
END $$;

