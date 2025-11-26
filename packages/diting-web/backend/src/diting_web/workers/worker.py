"""ARQ worker configuration.

Environment:
    - Production: Linux server
    - Local Development: Windows (本地调试 Windows 环境)

Cross-platform Compatibility:
    - This worker configuration is designed to work seamlessly on both Windows and Linux
    - All task handlers are async and platform-independent
"""

from urllib.parse import urlparse

import redis.asyncio as redis_async
from arq import create_pool
from arq.connections import RedisSettings

from diting_web.common.logging import configure_logging, get_logger
from diting_web.config import settings
from diting_web.workers.tasks import (
    batch_evaluation_task,
    evaluation_task,
    negative_mining_task,
    synthesis_task,
)

logger = get_logger(__name__)


async def startup(ctx: dict) -> None:
    """Worker startup handler."""
    configure_logging(
        log_level=settings.log_level,
        log_format=settings.log_format,
    )
    logger.info("ARQ worker starting up")


async def shutdown(ctx: dict) -> None:
    """Worker shutdown handler."""
    logger.info("ARQ worker shutting down")


class WorkerSettings:
    """ARQ worker settings."""

    # Parse Redis URL using urllib.parse for robust parsing
    # Supports: redis://host:port/db, redis://:password@host:port/db, rediss:// (TLS), etc.
    parsed = urlparse(str(settings.redis_url))
    
    # Extract connection parameters
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    database = int(parsed.path.lstrip("/")) if parsed.path and parsed.path != "/" else 0
    password = parsed.password
    
    # Determine if SSL/TLS is required (rediss://)
    ssl = parsed.scheme == "rediss"

    redis_settings = RedisSettings(
        host=host,
        port=port,
        database=database,
        password=password,
        ssl=ssl,
    )

    # Task functions
    functions = [
        evaluation_task,
        synthesis_task,
        batch_evaluation_task,
        negative_mining_task,
    ]

    # Startup and shutdown
    on_startup = startup
    on_shutdown = shutdown

    # Worker configuration
    max_jobs = 10
    job_timeout = 3600  # 1 hour
    keep_result = 3600  # Keep result for 1 hour


# For running the worker directly (alternative method)
# Usage: python -m diting_web.workers.worker
#
# Deployment:
#   - Production (Linux): python -m diting_web.scripts.run_worker
#   - Development (Windows 本地调试): python -m diting_web.scripts.run_worker
if __name__ == "__main__":
    from arq import run_worker

    # ✅ Cross-platform compatible: Works on both Windows and Linux
    # run_worker() manages its own event loop internally
    # ⚠️ Don't use asyncio.run() - causes "event loop already running" on Windows
    run_worker(WorkerSettings)

