"""Task service for business logic."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from diting_web.common.exceptions import ResourceNotFoundError, ValidationError
from diting_web.common.logging import get_logger
from diting_web.common.response import PaginatedResponse
from diting_web.models.dataset import Dataset
from diting_web.models.evaluator import Evaluator
from diting_web.models.metric import Metric
from diting_web.models.task import EvaluationResult, SynthesisResult, Task, TaskStatus, TaskType
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
        """Create an evaluation task (unified path) and enqueue it as batch evaluation.

        为了统一"评估任务"概念,这里将单次评估请求包装为一个仅包含 1 行数据的
        批量评估任务(batch_evaluation),从而复用同一套执行与统计逻辑。

        - 会创建一个临时数据集(1 行),行内容来自 `eval_case`
        - 优先使用 `metric_config`(单指标);若未来扩展支持 evaluator,可在 schema 中增加字段
        """
        # 1) 创建临时数据集(1 行) - user-level
        from diting_web.models.dataset import Dataset, DatasetRow

        eval_case = task_data.eval_case
        dataset = Dataset(
            name="临时评估数据集",
            description=None,
            created_by=created_by,
            row_count=1,
            columns=None,
        )
        self.db.add(dataset)
        await self.db.flush()  # 拿到 dataset.id

        row_data = {
            "user_input": eval_case.user_input,
            "actual_output": eval_case.actual_output,
            "expected_output": eval_case.expected_output,
            "context": eval_case.context,
            "retrieval_context": eval_case.retrieval_context,
        }
        dataset_row = DatasetRow(dataset_id=dataset.id, row_index=0, data=row_data)
        self.db.add(dataset_row)

        await self.db.commit()
        await self.db.refresh(dataset)

        # 2) 以"批量评估"任务创建(但数据集只有 1 行),复用同一执行路径
        config: dict = {}
        # All evaluations bind to evaluator
        config["evaluator_id"] = str(task_data.evaluator_id)
        if task_data.llm_config is not None:
            config["llm_config"] = task_data.llm_config.model_dump(mode="json")
        if task_data.embedding_config is not None:
            config["embedding_config"] = task_data.embedding_config.model_dump(mode="json")

        task = Task(
            name=None,
            task_type=TaskType.BATCH_EVALUATION,
            status=TaskStatus.PENDING,
            created_by=created_by,
            dataset_id=dataset.id,
            config=config,
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)

        # 3) 入队批量评估 Worker
        try:
            job_id = await self.arq_client.enqueue_batch_evaluation(task.id)
            logger.info(
                "Unified evaluation task enqueued as batch",
                task_id=str(task.id),
                job_id=job_id,
            )
        except Exception as e:
            logger.error(
                "Failed to enqueue unified evaluation task",
                task_id=str(task.id),
                error=str(e),
            )
            task.status = TaskStatus.FAILED
            task.error = f"Failed to enqueue: {str(e)}"
            await self.db.commit()
            raise

        logger.info("Evaluation task created (unified)", task_id=str(task.id))
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
        # Create task (user-level)
        task = Task(
            task_type=TaskType.SYNTHESIS,
            status=TaskStatus.PENDING,
            created_by=created_by,
            config=task_data.model_dump(mode='json'),  # mode='json' converts UUID to str
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
        # Create task (user-level)
        task = Task(
            task_type=TaskType.NEGATIVE_MINING,
            status=TaskStatus.PENDING,
            created_by=created_by,
            config=task_data.model_dump(mode='json'),  # mode='json' converts UUID to str
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

        # Verify dataset exists
        dataset_result = await self.db.execute(
            select(Dataset).where(Dataset.id == task_data.dataset_id)
        )
        dataset = dataset_result.scalar_one_or_none()
        if not dataset:
            raise ResourceNotFoundError("Dataset", str(task_data.dataset_id))

        # Generate task name if not provided
        task_name = task_data.name
        if not task_name:
            # Auto-generate name from dataset
            task_name = f"批量评估 - {dataset.name}"
        
        # Create task
        task = Task(
            name=task_name,
            task_type=TaskType.BATCH_EVALUATION,
            status=TaskStatus.PENDING,
            created_by=created_by,
            dataset_id=task_data.dataset_id,
            config=task_data.model_dump(mode='json'),  # mode='json' converts UUID to str
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
        user_id: Optional[UUID] = None,
        is_admin: bool = False,
    ) -> Task:
        """Get task by ID.

        Args:
            task_id: Task ID
            user_id: User ID (for permission check)
            is_admin: If True, skip permission check

        Returns:
            Task

        Raises:
            ResourceNotFoundError: If task not found or user has no access
        """
        query = select(Task).where(Task.id == task_id)
        
        # If not admin and user_id provided, verify ownership
        if not is_admin and user_id is not None:
            query = query.where(Task.created_by == user_id)
        
        result = await self.db.execute(query)
        task = result.scalar_one_or_none()

        if task is None:
            raise ResourceNotFoundError("Task", str(task_id))

        return task

    async def get_tasks_list(
        self,
        user_id: UUID,
        is_admin: bool = False,
        task_type: Optional[TaskType] = None,
        status: Optional[TaskStatus] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> PaginatedResponse[TaskResponse]:
        """Get paginated list of tasks.

        Args:
            user_id: User ID
            is_admin: If True, return all tasks; otherwise only user's tasks
            task_type: Filter by task type
            status: Filter by status
            offset: Pagination offset
            limit: Pagination limit

        Returns:
            Paginated response with tasks
        """
        # Build query
        query = select(Task)
        
        # If not admin, filter by user_id
        if not is_admin:
            query = query.where(Task.created_by == user_id)

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
        user_id: Optional[UUID] = None,
        is_admin: bool = False,
    ) -> Task:
        """Cancel a task by ID.

        Args:
            task_id: Task ID
            user_id: User ID (for permission check)
            is_admin: If True, skip permission check

        Returns:
            Cancelled task

        Raises:
            ResourceNotFoundError: If task not found or user has no access
            ValidationError: If task cannot be cancelled
        """
        # Get task (with permission check)
        task = await self.get_task_by_id(task_id, user_id=user_id, is_admin=is_admin)

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
        user_id: Optional[UUID] = None,
        is_admin: bool = False,
    ) -> list[SynthesisResult]:
        """Get synthesis results for a task.

        Args:
            task_id: Task ID
            user_id: User ID (for permission check)
            is_admin: If True, skip permission check

        Returns:
            List of synthesis results

        Raises:
            ResourceNotFoundError: If task not found or user has no access
        """
        # Verify task exists and is synthesis type (with permission check)
        task = await self.get_task_by_id(task_id, user_id=user_id, is_admin=is_admin)
        if task.task_type != TaskType.SYNTHESIS:
            raise ValidationError(f"Task {task_id} is not a synthesis task")

        # Get synthesis results
        result = await self.db.execute(
            select(SynthesisResult)
            .where(SynthesisResult.task_id == task_id)
            .order_by(SynthesisResult.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_negative_mining_results(
        self,
        task_id: UUID,
        user_id: Optional[UUID] = None,
        is_admin: bool = False,
    ) -> list[dict]:
        """Get negative mining results for a task.

        Args:
            task_id: Task ID
            user_id: User ID (for permission check)
            is_admin: If True, skip permission check

        Returns:
            List of negative mining results (enhanced data with mined negatives)

        Raises:
            ResourceNotFoundError: If task not found or user has no access
            ValidationError: If task is not a negative mining task
        """
        # Verify task exists and is negative mining type (with permission check)
        task = await self.get_task_by_id(task_id, user_id=user_id, is_admin=is_admin)
        if task.task_type != TaskType.NEGATIVE_MINING:
            raise ValidationError(f"Task {task_id} is not a negative mining task")

        # Get results from task.result JSON field
        if not task.result or "enhanced_data" not in task.result:
            return []

        return task.result["enhanced_data"]

    async def get_evaluation_results(
        self,
        task_id: UUID,
        offset: int = 0,
        limit: int = 100,
        pivot: bool = False,
        user_id: Optional[UUID] = None,
        is_admin: bool = False,
    ) -> PaginatedResponse[dict]:
        """Get evaluation results for a task.

        Args:
            task_id: Task ID
            offset: Pagination offset
            limit: Pagination limit
            pivot: If True, group results by question
            user_id: User ID (for permission check)
            is_admin: If True, skip permission check

        Returns:
            Paginated evaluation results

        Raises:
            ResourceNotFoundError: If task not found or user has no access
            ValidationError: If task is not an evaluation task
        """
        # Verify task exists and is evaluation type (with permission check)
        task = await self.get_task_by_id(task_id, user_id=user_id, is_admin=is_admin)
        if task.task_type not in [TaskType.EVALUATION, TaskType.BATCH_EVALUATION]:
            raise ValidationError(
                f"Task {task_id} is not an evaluation task (type: {task.task_type})"
            )

        if not pivot:
            # Get total count
            count_result = await self.db.execute(
                select(func.count()).where(EvaluationResult.task_id == task_id)
            )
            total = count_result.scalar() or 0

            # Get paginated results
            result = await self.db.execute(
                select(EvaluationResult)
                .where(EvaluationResult.task_id == task_id)
                .order_by(EvaluationResult.created_at.asc())
                .offset(offset)
                .limit(limit)
            )
            items = result.scalars().all()

            # Convert to dict
            items_dict = []
            for item in items:
                items_dict.append({
                    "id": str(item.id),
                    "metric_name": item.metric_name,
                    "score": float(item.score) if item.score is not None else None,
                    "reason": item.reason,
                    "user_input": item.user_input,
                    "actual_output": item.actual_output,
                    "expected_output": item.expected_output,
                    "context": item.context,
                    "retrieval_context": item.retrieval_context,
                    "usages": item.usages,
                    "created_at": item.created_at.isoformat(),
                })

            # Calculate pagination info
            page = (offset // limit) + 1 if limit > 0 else 1
            page_size = limit

            return PaginatedResponse.create(
                items=items_dict,
                total=total,
                page=page,
                page_size=page_size,
            )

        # pivot mode: group multiple metric results under each question
        # Fetch ALL results for the task first, then group in memory (N is typically manageable)
        result_all = await self.db.execute(
            select(EvaluationResult)
            .where(EvaluationResult.task_id == task_id)
            .order_by(EvaluationResult.created_at.asc())
        )
        all_items = list(result_all.scalars().all())

        # Group by (user_input, expected_output, actual_output)
        grouped: dict[tuple, dict] = {}
        for item in all_items:
            key = (
                item.user_input or "",
                item.expected_output or "",
                item.actual_output or "",
            )
            group = grouped.get(key)
            if not group:
                group = {
                    "user_input": item.user_input,
                    "actual_output": item.actual_output,
                    "expected_output": item.expected_output,
                    "metrics": {},  # metric_name -> { score, reason }
                    "created_at": item.created_at.isoformat(),
                }
                grouped[key] = group
            group["metrics"][item.metric_name] = {
                "score": float(item.score) if item.score is not None else None,
                "reason": item.reason,
            }

        groups_list = list(grouped.values())
        total_groups = len(groups_list)

        # Apply pagination on groups
        sliced = groups_list[offset: offset + limit] if limit > 0 else groups_list

        page = (offset // limit) + 1 if limit > 0 else 1
        page_size = limit

        return PaginatedResponse.create(
            items=sliced,
            total=total_groups,
            page=page,
            page_size=page_size,
        )

    async def get_evaluation_summary(
        self,
        task_id: UUID,
        user_id: Optional[UUID] = None,
        is_admin: bool = False,
    ) -> dict:
        """Get evaluation summary statistics.

        Args:
            task_id: Task ID
            user_id: User ID (for permission check)
            is_admin: If True, skip permission check

        Returns:
            Summary statistics

        Raises:
            ResourceNotFoundError: If task not found or user has no access
        """
        # Verify task exists (with permission check)
        task = await self.get_task_by_id(task_id, user_id=user_id, is_admin=is_admin)
        if task.task_type not in [TaskType.EVALUATION, TaskType.BATCH_EVALUATION]:
            raise ValidationError(f"Task {task_id} is not an evaluation task")

        # Get all evaluation results
        result = await self.db.execute(
            select(EvaluationResult).where(EvaluationResult.task_id == task_id)
        )
        results = list(result.scalars().all())

        if not results:
            return {
                "total_count": 0,
                "average_score": None,
                "pass_rate": None,
                "score_distribution": {},
                "metrics_summary": {},
            }

        # Calculate statistics
        scores = [float(r.score) for r in results if r.score is not None]
        average_score = sum(scores) / len(scores) if scores else None

        # Pass rate (assuming score >= 0.7 is pass)
        pass_count = sum(1 for s in scores if s >= 0.7)
        pass_rate = pass_count / len(scores) if scores else None

        # Score distribution (bins: 0-0.2, 0.2-0.4, 0.4-0.6, 0.6-0.8, 0.8-1.0)
        score_distribution = {
            "0.0-0.2": 0,
            "0.2-0.4": 0,
            "0.4-0.6": 0,
            "0.6-0.8": 0,
            "0.8-1.0": 0,
        }
        for score in scores:
            if score < 0.2:
                score_distribution["0.0-0.2"] += 1
            elif score < 0.4:
                score_distribution["0.2-0.4"] += 1
            elif score < 0.6:
                score_distribution["0.4-0.6"] += 1
            elif score < 0.8:
                score_distribution["0.6-0.8"] += 1
            else:
                score_distribution["0.8-1.0"] += 1

        # Metrics summary (group by metric_name)
        metrics_summary = {}
        for result in results:
            metric_name = result.metric_name
            if metric_name not in metrics_summary:
                metrics_summary[metric_name] = {
                    "count": 0,
                    "scores": [],
                    "average_score": None,
                }
            metrics_summary[metric_name]["count"] += 1
            if result.score is not None:
                metrics_summary[metric_name]["scores"].append(float(result.score))

        # Calculate average for each metric
        for metric_name, data in metrics_summary.items():
            if data["scores"]:
                data["average_score"] = sum(data["scores"]) / len(data["scores"])
            del data["scores"]  # Remove raw scores from response

        return {
            "total_count": len(results),
            "average_score": average_score,
            "pass_rate": pass_rate,
            "score_distribution": score_distribution,
            "metrics_summary": metrics_summary,
        }

    async def delete_task(
        self,
        task_id: UUID,
        user_id: Optional[UUID] = None,
        is_admin: bool = False,
    ) -> None:
        """Delete a task and its results.

        Args:
            task_id: Task ID
            user_id: User ID (for permission check)
            is_admin: If True, skip permission check

        Raises:
            ResourceNotFoundError: If task not found or user has no access
            ValidationError: If task cannot be deleted (e.g., still running)
        """
        # Get task (with permission check)
        task = await self.get_task_by_id(task_id, user_id=user_id, is_admin=is_admin)

        # Check if task can be deleted
        if task.status == TaskStatus.RUNNING:
            raise ValidationError(
                f"Cannot delete task with status {task.status}. Cancel it first."
            )

        # Delete task (cascade will delete related results)
        await self.db.delete(task)
        await self.db.commit()

        logger.info("Task deleted", task_id=str(task_id))

    async def retry_task(
        self,
        task_id: UUID,
        user_id: Optional[UUID] = None,
        is_admin: bool = False,
    ) -> Task:
        """Retry a failed task.

        Args:
            task_id: Task ID
            user_id: User ID (for permission check)
            is_admin: If True, skip permission check

        Returns:
            Retried task

        Raises:
            ResourceNotFoundError: If task not found or user has no access
            ValidationError: If task cannot be retried
        """
        # Get task (with permission check)
        task = await self.get_task_by_id(task_id, user_id=user_id, is_admin=is_admin)

        # Check if task can be retried
        if task.status != TaskStatus.FAILED:
            raise ValidationError(f"Cannot retry task with status {task.status}")

        # Reset task status
        task.status = TaskStatus.PENDING
        task.error = None
        task.started_at = None
        task.completed_at = None
        task.progress = 0
        await self.db.commit()

        # Re-enqueue task
        try:
            # Determine which enqueue method to use
            # Use force=True to abort any existing job with the same ID
            if task.task_type == TaskType.EVALUATION:
                job_id = await self.arq_client.enqueue_evaluation(task.id, force=True)
            elif task.task_type == TaskType.SYNTHESIS:
                job_id = await self.arq_client.enqueue_synthesis(task.id, force=True)
            elif task.task_type == TaskType.BATCH_EVALUATION:
                job_id = await self.arq_client.enqueue_batch_evaluation(task.id, force=True)
            elif task.task_type == TaskType.NEGATIVE_MINING:
                job_id = await self.arq_client.enqueue_negative_mining(task.id, force=True)
            else:
                raise ValidationError(f"Unknown task type: {task.task_type}")

            task.job_id = job_id
            await self.db.commit()
            await self.db.refresh(task)

            logger.info("Task retried", task_id=str(task_id), job_id=job_id)
            return task
        except Exception as e:
            logger.error("Failed to retry task", task_id=str(task_id), error=str(e))
            task.status = TaskStatus.FAILED
            task.error = f"Failed to enqueue: {str(e)}"
            await self.db.commit()
            raise

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

