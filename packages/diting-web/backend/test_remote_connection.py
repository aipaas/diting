"""测试远程服务连接的脚本"""

import asyncio
import sys
from typing import Any

# 测试配置


def print_header(title: str) -> None:
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(service: str, success: bool, message: str = "") -> None:
    """打印测试结果"""
    status = "✅ 成功" if success else "❌ 失败"
    print(f"{status} - {service}")
    if message:
        print(f"    {message}")


async def test_postgresql() -> bool:
    """测试 PostgreSQL 连接"""
    try:
        from sqlalchemy.ext.asyncio import create_async_engine

        from diting_web.config.settings import settings

        engine = create_async_engine(str(settings.database_url), echo=False)
        async with engine.begin() as conn:
            result = await conn.execute(
                __import__("sqlalchemy").text("SELECT version()")
            )
            version = result.scalar()
            print_result("PostgreSQL", True, version)
            return True
    except ImportError:
        print_result("PostgreSQL", False, "sqlalchemy 未安装")
        return False
    except Exception as e:
        print_result("PostgreSQL", False, str(e))
        return False


async def test_redis() -> bool:
    """测试 Redis 连接"""
    try:
        import redis.asyncio as redis

        from diting_web.config.settings import settings

        r = redis.from_url(str(settings.redis_url))
        pong = await r.ping()
        info = await r.info("server")
        version = info.get("redis_version", "unknown")
        await r.close()
        print_result("Redis", pong, f"版本: {version}")
        return pong
    except ImportError:
        print_result("Redis", False, "redis 未安装")
        return False
    except Exception as e:
        print_result("Redis", False, str(e))
        return False


async def test_minio() -> bool:
    """测试 MinIO 连接"""
    try:
        from minio import Minio

        from diting_web.config.settings import settings

        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )

        # 测试连接并获取桶列表
        buckets = client.list_buckets()
        bucket_names = [b.name for b in buckets]

        # 检查目标桶是否存在
        bucket_exists = settings.minio_bucket_name in bucket_names

        message = f"可访问的桶: {', '.join(bucket_names) if bucket_names else '无'}"
        if not bucket_exists:
            message += f"\n    ⚠️ 桶 '{settings.minio_bucket_name}' 不存在，将在首次使用时创建"

        print_result("MinIO", True, message)
        return True
    except ImportError:
        print_result("MinIO", False, "minio 未安装")
        return False
    except Exception as e:
        print_result("MinIO", False, str(e))
        return False


def test_env_config() -> dict[str, Any]:
    """检查环境配置"""
    try:
        from diting_web.config.settings import settings

        config = {
            "DATABASE_URL": str(settings.database_url),
            "REDIS_URL": str(settings.redis_url),
            "MINIO_ENDPOINT": settings.minio_endpoint,
            "MINIO_BUCKET": settings.minio_bucket_name,
            "LLM_MODEL": settings.default_llm_model,
            "LLM_API_KEY": "已配置" if settings.llm_api_key else "❌ 未配置",
            "EMBEDDING_MODEL": settings.default_embedding_model,
            "EMBEDDING_API_KEY": "已配置"
            if settings.embedding_api_key
            else "❌ 未配置",
        }
        return config
    except ImportError:
        print_result("环境配置", False, "无法导入 settings")
        return {}
    except Exception as e:
        print_result("环境配置", False, str(e))
        return {}


async def main() -> None:
    """主函数"""
    print_header("DiTing Web - 远程服务连接测试")

    # 1. 检查环境配置
    print("\n📋 环境配置检查:")
    config = test_env_config()
    if config:
        for key, value in config.items():
            # 隐藏密码信息
            if "URL" in key and "@" in str(value):
                # 隐藏密码部分
                parts = str(value).split("@")
                if ":" in parts[0]:
                    parts[0] = parts[0].rsplit(":", 1)[0] + ":****"
                value = "@".join(parts)
            print(f"  {key:20s}: {value}")
    else:
        print("  ❌ 无法加载配置，请检查 .env 文件")
        sys.exit(1)

    # 2. 测试服务连接
    print_header("服务连接测试")

    results = []
    results.append(("PostgreSQL", await test_postgresql()))
    results.append(("Redis", await test_redis()))
    results.append(("MinIO", await test_minio()))

    # 3. 总结
    print_header("测试总结")
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)

    print(f"\n总计: {success_count}/{total_count} 个服务连接成功\n")

    if success_count == total_count:
        print("✅ 所有服务连接正常！可以启动应用了。")
        print("\n下一步:")
        print("  1. 运行数据库迁移: uv run alembic upgrade head")
        print("  2. 初始化数据:     uv run python -m diting_web.scripts.init_admin")
        print("  3. 启动 API:       uv run uvicorn diting_web.main:app --reload")
        print("  4. 启动 Worker:    uv run python -m diting_web.scripts.run_worker")
        sys.exit(0)
    else:
        print("❌ 部分服务连接失败，请检查配置和网络连接。")
        print("\n故障排查:")
        print("  1. 检查 .env 文件中的配置是否正确")
        print("  2. 确认远程服务器防火墙已开放端口")
        print("  3. 测试网络连通性: ping <远程IP>")
        print("  4. 查看详细文档: ../LOCAL_SETUP.md")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ 测试已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

