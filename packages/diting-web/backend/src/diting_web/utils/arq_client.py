"""ARQ client for task queue operations.

Provides utilities to enqueue tasks to ARQ workers.
"""

import asyncio
from typing import Any, Optional
from urllib.parse import urlparse
from uuid import UUID

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from diting_web.common.logging import get_logger
from diting_web.config.settings import get_settings

logger = get_logger(__name__)


class ARQClient:
    """ARQ client for enqueueing tasks."""

    def __init__(self):
        """Initialize ARQ client."""
        settings = get_settings()
        
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
        
        self.redis_settings = RedisSettings(
            host=host,
            port=port,
            database=database,
            password=password,
            ssl=ssl,
        )
        self._pool: Optional[ArqRedis] = None

    async def get_pool(self) -> ArqRedis:
        """Get or create ARQ connection pool.
        
        Returns:
            ArqRedis connection pool
        """
        if self._pool is None:
            self._pool = await create_pool(self.redis_settings)
            logger.info("ARQ connection pool created")
        return self._pool

    async def close(self) -> None:
        """Close ARQ connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            logger.info("ARQ connection pool closed")

    async def enqueue_evaluation(
        self,
        task_id: UUID,
        priority: int = 0,
        force: bool = False,
    ) -> str:
        """Enqueue an evaluation task.
        
        Args:
            task_id: Task ID
            priority: Task priority (higher = more important)
            force: If True, abort existing job and create new one (for retry)
            
        Returns:
            Job ID
            
        Raises:
            RuntimeError: If force=True but job cannot be enqueued (retry failed)
        """
        pool = await self.get_pool()
        job_id = f"eval_{task_id}"
        
        # If force=True (retry), try to abort the old job first
        if force:
            try:
                await pool.abort_job(job_id)
                logger.info("Aborted existing job for retry", job_id=job_id)
                # Give ARQ a moment to clean up the aborted job
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.warning("Failed to abort existing job", job_id=job_id, error=str(e))
        
        job = await pool.enqueue_job(
            "evaluation_task",
            str(task_id),
            _job_id=job_id,
            _priority=priority,
        )
        
        # If job is None, it means the job is already in the queue
        if job is None:
            if force:
                # In force mode, this is a critical error - retry failed
                error_msg = (
                    f"Failed to enqueue evaluation task after abort: job_id={job_id} "
                    f"still exists in queue. This may indicate the old job was not properly cleaned up."
                )
                logger.error(error_msg, task_id=str(task_id), job_id=job_id)
                raise RuntimeError(error_msg)
            else:
                logger.warning(
                    "Evaluation task already in queue",
                    task_id=str(task_id),
                    job_id=job_id,
                )
                return job_id
        
        logger.info(
            "Evaluation task enqueued",
            task_id=str(task_id),
            job_id=job.job_id,
        )
        return job.job_id

    async def enqueue_synthesis(
        self,
        task_id: UUID,
        priority: int = 0,
        force: bool = False,
    ) -> str:
        """Enqueue a synthesis task.
        
        Args:
            task_id: Task ID
            priority: Task priority (higher = more important)
            force: If True, abort existing job and create new one (for retry)
            
        Returns:
            Job ID
            
        Raises:
            RuntimeError: If force=True but job cannot be enqueued (retry failed)
        """
        pool = await self.get_pool()
        job_id = f"synth_{task_id}"
        
        # If force=True (retry), try to abort the old job first
        if force:
            try:
                await pool.abort_job(job_id)
                logger.info("Aborted existing job for retry", job_id=job_id)
                # Give ARQ a moment to clean up the aborted job
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.warning("Failed to abort existing job", job_id=job_id, error=str(e))
        
        job = await pool.enqueue_job(
            "synthesis_task",
            str(task_id),
            _job_id=job_id,
            _priority=priority,
        )
        
        # If job is None, it means the job is already in the queue
        if job is None:
            if force:
                # In force mode, this is a critical error - retry failed
                error_msg = (
                    f"Failed to enqueue synthesis task after abort: job_id={job_id} "
                    f"still exists in queue. This may indicate the old job was not properly cleaned up."
                )
                logger.error(error_msg, task_id=str(task_id), job_id=job_id)
                raise RuntimeError(error_msg)
            else:
                logger.warning(
                    "Synthesis task already in queue",
                    task_id=str(task_id),
                    job_id=job_id,
                )
                return job_id
        
        logger.info(
            "Synthesis task enqueued",
            task_id=str(task_id),
            job_id=job.job_id,
        )
        return job.job_id

    async def enqueue_batch_evaluation(
        self,
        task_id: UUID,
        priority: int = 0,
        force: bool = False,
    ) -> str:
        """Enqueue a batch evaluation task.
        
        Args:
            task_id: Task ID
            priority: Task priority (higher = more important)
            force: If True, abort existing job and create new one (for retry)
            
        Returns:
            Job ID
            
        Raises:
            RuntimeError: If force=True but job cannot be enqueued (retry failed)
        """
        pool = await self.get_pool()
        job_id = f"batch_{task_id}"
        
        # If force=True (retry), try to abort the old job first
        if force:
            try:
                await pool.abort_job(job_id)
                logger.info("Aborted existing job for retry", job_id=job_id)
                # Give ARQ a moment to clean up the aborted job
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.warning("Failed to abort existing job", job_id=job_id, error=str(e))
        
        job = await pool.enqueue_job(
            "batch_evaluation_task",
            str(task_id),
            _job_id=job_id,
            _priority=priority,
        )
        
        # If job is None, it means the job is already in the queue
        if job is None:
            if force:
                # In force mode, this is a critical error - retry failed
                error_msg = (
                    f"Failed to enqueue batch evaluation task after abort: job_id={job_id} "
                    f"still exists in queue. This may indicate the old job was not properly cleaned up."
                )
                logger.error(error_msg, task_id=str(task_id), job_id=job_id)
                raise RuntimeError(error_msg)
            else:
                logger.warning(
                    "Batch evaluation task already in queue",
                    task_id=str(task_id),
                    job_id=job_id,
                )
                return job_id
        
        logger.info(
            "Batch evaluation task enqueued",
            task_id=str(task_id),
            job_id=job.job_id,
        )
        return job.job_id

    async def enqueue_negative_mining(
        self,
        task_id: UUID,
        priority: int = 0,
        force: bool = False,
    ) -> str:
        """Enqueue a negative mining task.
        
        Args:
            task_id: Task ID
            priority: Task priority (higher = more important)
            force: If True, abort existing job and create new one (for retry)
            
        Returns:
            Job ID
            
        Raises:
            RuntimeError: If force=True but job cannot be enqueued (retry failed)
        """
        pool = await self.get_pool()
        job_id = f"negmin_{task_id}"
        
        # If force=True (retry), try to abort the old job first
        if force:
            try:
                await pool.abort_job(job_id)
                logger.info("Aborted existing job for retry", job_id=job_id)
                # Give ARQ a moment to clean up the aborted job
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.warning("Failed to abort existing job", job_id=job_id, error=str(e))
        
        job = await pool.enqueue_job(
            "negative_mining_task",
            str(task_id),
            _job_id=job_id,
            _priority=priority,
        )
        
        # If job is None, it means the job is already in the queue
        if job is None:
            if force:
                # In force mode, this is a critical error - retry failed
                error_msg = (
                    f"Failed to enqueue negative mining task after abort: job_id={job_id} "
                    f"still exists in queue. This may indicate the old job was not properly cleaned up."
                )
                logger.error(error_msg, task_id=str(task_id), job_id=job_id)
                raise RuntimeError(error_msg)
            else:
                logger.warning(
                    "Negative mining task already in queue",
                    task_id=str(task_id),
                    job_id=job_id,
                )
                return job_id
        
        logger.info(
            "Negative mining task enqueued",
            task_id=str(task_id),
            job_id=job.job_id,
        )
        return job.job_id

    async def get_job_status(self, job_id: str) -> Optional[dict[str, Any]]:
        """Get job status from ARQ.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job status dict or None if not found
        """
        pool = await self.get_pool()
        job = await pool.get_job(job_id)
        
        if job is None:
            return None
        
        return {
            "job_id": job.job_id,
            "status": await job.status(),
            "result": await job.result(),
        }

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job.
        
        Args:
            job_id: Job ID
            
        Returns:
            True if cancelled, False otherwise
        """
        pool = await self.get_pool()
        job = await pool.get_job(job_id)
        
        if job is None:
            logger.warning("Job not found for cancellation", job_id=job_id)
            return False
        
        # ARQ doesn't have direct cancel, but we can abort it
        await job.abort()
        logger.info("Job cancelled", job_id=job_id)
        return True


# Singleton instance
_arq_client: Optional[ARQClient] = None


def get_arq_client() -> ARQClient:
    """Get ARQ client singleton instance.
    
    Returns:
        ARQClient instance
    """
    global _arq_client
    if _arq_client is None:
        _arq_client = ARQClient()
    return _arq_client


async def close_arq_client() -> None:
    """Close ARQ client connection."""
    global _arq_client
    if _arq_client is not None:
        await _arq_client.close()
        _arq_client = None


