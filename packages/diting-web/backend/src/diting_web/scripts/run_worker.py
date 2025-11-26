"""Script to run ARQ worker.

This script starts the ARQ worker to process background tasks.

Environment:
    - Production: Linux server
    - Local Development: Windows (also compatible with Linux/macOS)

Cross-platform Compatibility:
    - This script is designed to work on both Windows and Linux
    - Uses run_worker() directly (not with asyncio.run()) to avoid
      "event loop already running" errors on Windows
    - ARQ's run_worker() manages its own event loop internally
"""

from arq import run_worker

from diting_web.common.logging import configure_logging, get_logger
from diting_web.config.settings import get_settings
from diting_web.workers.worker import WorkerSettings

logger = get_logger(__name__)


def main() -> None:
    """Run the ARQ worker."""
    settings = get_settings()
    
    # Configure logging
    configure_logging(
        log_level=settings.log_level,
        log_format=settings.log_format,
    )
    
    logger.info("Starting ARQ worker...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Redis URL: {settings.redis_url}")
    logger.info(f"Max jobs: {WorkerSettings.max_jobs}")
    
    # Run worker - run_worker() manages its own event loop internally
    # ⚠️ IMPORTANT: Don't wrap with asyncio.run() or await
    # 
    # Production: Linux server
    # Development: Windows (本地调试)
    # 
    # This synchronous call works on both platforms:
    # - On Windows: Avoids "event loop already running" error
    # - On Linux: Works perfectly without any issues
    run_worker(WorkerSettings)


if __name__ == "__main__":
    main()


