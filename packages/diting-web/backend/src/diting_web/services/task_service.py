"""Task service for business logic."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from diting_web.common.exceptions import ResourceNotFoundError, ValidationError
from diting_web.common.logging import get_logger
from diting_web.common.response import PaginatedResponse
from diting_web.models.evaluator import Evaluator
from diting_web.models.metric import Metric
from diting_web.models.task import SynthesisResult, Task, TaskStatus, TaskType
from diting_web.schemas.task import (
    CreateBatchEvaluationTaskRequest,
    CreateEvaluationTaskRequest,
    CreateNegativeMiningTaskRequest,
    CreateSynthesisTaskRequest,
    SynthesisResultResponse,
    TaskResponse,
)
from diting_web.utils.arq_client import get_arq_client

logger = get_logger(__name__)


class TaskService:
    """Task service for business logic."""

    def __init__(self, db: AsyncSession):
        """Initialize task service.

        Args:
            db: Database session
        """
        self.db = db
        self.arq_client = get_arq_client()

    async def create_evaluation_task(
        self,
        task_data: CreateEvaluationTaskRequest,
        created_by: UUID,
    ) -> Task:
        """Create an evaluation task and enqueue it.

        Args:
            task_data: Task creation data
            created_by: User ID

        Returns:
            Created task
        """
        # Create task
        task = Task(
            task_type=TaskType.EVALUATION,
            status=TaskStatus.PENDING,
            created_by=created_by,
            config=task_data.model_dump(),
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)

        # Enqueue task to ARQ worker
        try:
            job_id = await self.arq_client.enqueue_evaluation(task.id)
            logger.info(
                "Evaluation task enqueued",
                task_id=str(task.id),
                job_id=job_id,
            )
        except Exception as e:
            logger.error(
                "Failed to enqueue evaluation task",
                task_id=str(task.id),
                error=str(e),
            )
            # Update task status to failed
            task.status = TaskStatus.FAILED
            task.error = f"Failed to enqueue: {str(e)}"
            await self.db.commit()
            raise

        logger.info("Evaluation task created", task_id=str(task.id))
        return task

    async def create_synthesis_task(
        self,
        task_data: CreateSynthesisTaskRequest,
        created_by: UUID,
    ) -> Task:
        """Create a synthesis task and enqueue it.

        Args:
            task_data: Task creation data
            created_by: User ID

        Returns:
            Created task
        """
        # Create task
        task = Task(
            task_type=TaskType.SYNTHESIS,
            status=TaskStatus.PENDING,
            created_by=created_by,
            config=task_data.model_dump(),
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)

        # Enqueue task to ARQ worker
        try:
            job_id = await self.arq_client.enqueue_synthesis(task.id)
            logger.info(
                "Synthesis task enqueued",
                task_id=str(task.id),
                job_id=job_id,
            )
        except Exception as e:
            logger.error(
                "Failed to enqueue synthesis task",
                task_id=str(task.id),
                error=str(e),
            )
            # Update task status to failed
            task.status = TaskStatus.FAILED
            task.error = f"Failed to enqueue: {str(e)}"
            await self.db.commit()
            raise

        logger.info("Synthesis task created", task_id=str(task.id))
        return task

    async def create_negative_mining_task(
        self,
        task_data: CreateNegativeMiningTaskRequest,
        created_by: UUID,
    ) -> Task:
        """Create a negative mining task and enqueue it.

        Args:
            task_data: Task creation data
            created_by: User ID

        Returns:
            Created task
        """
        # Create task
        task = Task(
            task_type=TaskType.NEGATIVE_MINING,
            status=TaskStatus.PENDING,
            created_by=created_by,
            config=task_data.model_dump(),
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)

        # Enqueue task to ARQ worker
        try:
            job_id = await self.arq_client.enqueue_negative_mining(task.id)
            logger.info(
                "Negative mining task enqueued",
                task_id=str(task.id),
                job_id=job_id,
            )
        except Exception as e:
            logger.error(
                "Failed to enqueue negative mining task",
                task_id=str(task.id),
                error=str(e),
            )
            # Update task status to failed
            task.status = TaskStatus.FAILED
            task.error = f"Failed to enqueue: {str(e)}"
            await self.db.commit()
            raise

        logger.info("Negative mining task created", task_id=str(task.id))
        return task

    async def create_batch_evaluation_task(
        self,
        task_data: CreateBatchEvaluationTaskRequest,
        created_by: UUID,
    ) -> Task:
        """Create a batch evaluation task and enqueue it.

        This creates a single batch evaluation task that will process
        multiple test cases using an evaluator (which may have multiple metrics).

        Args:
            task_data: Task creation data
            created_by: User ID

        Returns:
            Created task
        """
        # Verify evaluator exists (if provided)
        if task_data.evaluator_id:
            result = await self.db.execute(
                select(Evaluator).where(Evaluator.id == task_data.evaluator_id)
            )
            evaluator = result.scalar_one_or_none()
            if not evaluator:
                raise ResourceNotFoundError("Evaluator", str(task_data.evaluator_id))

            # Update evaluator usage stats
            evaluator.usage_count += 1
            evaluator.last_used_at = datetime.utcnow()

        # Create task
        task = Task(
            task_type=TaskType.BATCH_EVALUATION,
            status=TaskStatus.PENDING,
            created_by=created_by,
            dataset_id=task_data.dataset_id,
            config=task_data.model_dump(),
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)

        # Enqueue task to ARQ worker
        try:
            job_id = await self.arq_client.enqueue_batch_evaluation(task.id)
            logger.info(
                "Batch evaluation task enqueued",
                task_id=str(task.id),
                job_id=job_id,
            )
        except Exception as e:
            logger.error(
                "Failed to enqueue batch evaluation task",
                task_id=str(task.id),
                error=str(e),
            )
            # Update task status to failed
            task.status = TaskStatus.FAILED
            task.error = f"Failed to enqueue: {str(e)}"
            await self.db.commit()
            raise

        logger.info("Batch evaluation task created", task_id=str(task.id))
        return task

    async def get_task_by_id(
        self,
        task_id: UUID,
    ) -> Task:
        """Get task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task

        Raises:
            ResourceNotFoundError: If task not found
        """
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()

        if task is None:
            raise ResourceNotFoundError("Task", str(task_id))

        return task

    async def get_tasks_list(
        self,
        user_id: UUID,
        task_type: Optional[TaskType] = None,
        status: Optional[TaskStatus] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> PaginatedResponse[TaskResponse]:
        """Get paginated list of tasks.

        Args:
            user_id: User ID
            task_type: Filter by task type
            status: Filter by status
            offset: Pagination offset
            limit: Pagination limit

        Returns:
            Paginated response with tasks
        """
        # Build query
        query = select(Task).where(Task.created_by == user_id)

        # Apply filters
        if task_type:
            query = query.where(Task.task_type == task_type)
        if status:
            query = query.where(Task.status == status)

        # Order by creation time
        query = query.order_by(Task.created_at.desc())

        # Get total count
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar() or 0

        # Get paginated items
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        items = result.scalars().all()

        # Calculate pagination info
        page = (offset // limit) + 1 if limit > 0 else 1
        page_size = limit

        # Create response
        return PaginatedResponse.create(
            items=[TaskResponse.model_validate(item).model_dump() for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def cancel_task(
        self,
        task_id: UUID,
    ) -> Task:
        """Cancel a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Cancelled task

        Raises:
            ResourceNotFoundError: If task not found
            ValidationError: If task cannot be cancelled
        """
        # Get task
        task = await self.get_task_by_id(task_id)

        # Check if task can be cancelled
        if task.status not in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            raise ValidationError(f"Cannot cancel task with status {task.status}")

        # Update task status
        task.status = TaskStatus.CANCELLED
        await self.db.commit()

        # Try to cancel task in ARQ (best effort)
        try:
            job_id = self._get_job_id(task)
            await self.arq_client.cancel_job(job_id)
            logger.info("Task cancelled in ARQ", task_id=str(task_id), job_id=job_id)
        except Exception as e:
            logger.warning(
                "Failed to cancel task in ARQ (task already updated in DB)",
                task_id=str(task_id),
                error=str(e),
            )

        await self.db.refresh(task)
        logger.info("Task cancelled", task_id=str(task_id))
        return task

    async def get_synthesis_results(
        self,
        task_id: UUID,
    ) -> list[SynthesisResult]:
        """Get synthesis results for a task.

        Args:
            task_id: Task ID

        Returns:
            List of synthesis results

        Raises:
            ResourceNotFoundError: If task not found
        """
        # Verify task exists and is synthesis type
        task = await self.get_task_by_id(task_id)
        if task.task_type != TaskType.SYNTHESIS:
            raise ValidationError(f"Task {task_id} is not a synthesis task")

        # Get synthesis results
        result = await self.db.execute(
            select(SynthesisResult)
            .where(SynthesisResult.task_id == task_id)
            .order_by(SynthesisResult.created_at.asc())
        )
        return list(result.scalars().all())

    def _get_job_id(self, task: Task) -> str:
        """Get ARQ job ID for a task.

        Args:
            task: Task

        Returns:
            Job ID string
        """
        task_type_prefix = {
            TaskType.EVALUATION: "eval",
            TaskType.SYNTHESIS: "synth",
            TaskType.BATCH_EVALUATION: "batch",
            TaskType.NEGATIVE_MINING: "negmin",
        }
        prefix = task_type_prefix.get(task.task_type, "task")
        return f"{prefix}_{task.id}"
