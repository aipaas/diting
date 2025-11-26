"""ARQ task definitions.

These are the actual worker tasks that process evaluations and synthesis using diting-core.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from diting_web.common.logging import get_logger
from diting_web.db.session import AsyncSessionLocal
from diting_web.workers.evaluation import EvaluationRunner
from diting_web.workers.synthesis import SynthesisRunner
from diting_web.utils.model_helpers import (
    create_embedding_from_config,
    get_default_embedding_config,
    get_default_llm_config,
)
from diting_web.services import NegativeMiningService
# Import token callbacks from diting-server (same as EvaluationRunner)
from diting_server.common.callback import (
    GetEmbedTokenCallbackHandler,
)
from diting_server.common.utils import compute_token_usage
from diting_web.models.dataset import Dataset
from diting_web.models.evaluator import Evaluator
from diting_web.models.metric import Metric
from diting_web.models.task import EvaluationResult, SynthesisResult, Task, TaskStatus
from diting_web.models.model import Model, ModelTypeEnum

logger = get_logger(__name__)


def _normalize_model_config(config: dict[str, Any]) -> dict[str, Any]:
    """Normalize model config keys to what core adapter expects.

    Frontend/evaluator config uses {"name": "model-display-name", ...} while
    core adapter expects {"model_name": "..."}. This helper maps name -> model_name
    when model_name is missing. It returns a shallow-copied dict to avoid mutating
    original objects.
    """
    if not isinstance(config, dict):
        return config
    normalized: dict[str, Any] = dict(config)
    if "model_name" not in normalized and "name" in normalized:
        normalized["model_name"] = normalized["name"]
    return normalized


async def _get_default_model_config(db: AsyncSession, model_type: ModelTypeEnum) -> Dict[str, Any] | None:
    """Read default model config from DB models table by is_default flag."""
    try:
        result = await db.execute(
            select(Model).where(Model.model_type == model_type, Model.is_default == True)
        )
        model: Model | None = result.scalar_one_or_none()
        if not model:
            logger.debug(f"No default {model_type} model found in DB")
            return None
        
        logger.info(
            f"Using default {model_type} model from DB", 
            model_name=str(model.name), 
            base_url="***" if model.base_url else None,
        )
        
        cfg: Dict[str, Any] = {
            "model_name": str(model.name),
            "base_url": str(model.base_url) if model.base_url else None,
            "api_key": str(model.api_key) if model.api_key else None,
            "timeout": int(model.timeout),
        }
        if model.parameters:
            cfg.update(model.parameters)
        
        logger.debug(f"Default {model_type} config assembled", config_keys=list(cfg.keys()))
        return cfg
    except Exception as e:
        logger.warning(f"Failed to fetch default {model_type} model from DB", error=str(e))
        return None


async def _get_model_config_by_name(db: AsyncSession, model_name: str, model_type: ModelTypeEnum) -> Dict[str, Any] | None:
    """Look up model config from DB by name (display name)."""
    try:
        result = await db.execute(
            select(Model).where(Model.name == model_name, Model.model_type == model_type)
        )
        model: Model | None = result.scalar_one_or_none()
        if not model:
            logger.debug(f"Model '{model_name}' ({model_type}) not found in DB")
            return None
        
        logger.info(
            f"Found model '{model_name}' in DB",
            base_url="***" if model.base_url else None,
        )
        
        cfg: Dict[str, Any] = {
            "model_name": str(model.name),
            "base_url": str(model.base_url) if model.base_url else None,
            "api_key": str(model.api_key) if model.api_key else None,
            "timeout": int(model.timeout),
        }
        if model.parameters:
            cfg.update(model.parameters)
        return cfg
    except Exception as e:
        logger.warning(f"Failed to fetch model '{model_name}' from DB", error=str(e))
        return None

async def update_task_status(
    task_id: UUID,
    status: TaskStatus,
    progress: Decimal | None = None,
    error: str | None = None,
) -> None:
    """Update task status in database.
    
    Args:
        task_id: Task ID
        status: New status
        progress: Progress percentage (0-100)
        error: Error message if failed
    """
    async with AsyncSessionLocal() as db:
        task = await db.get(Task, task_id)
        if task:
            task.status = status
            if progress is not None:
                task.progress = progress
            if error:
                task.error = error
            
            if status == TaskStatus.RUNNING and not task.started_at:
                task.started_at = datetime.now(timezone.utc)
            elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                task.completed_at = datetime.now(timezone.utc)
            
            await db.commit()
            logger.info("Task status updated", task_id=str(task_id), status=status)


async def evaluation_task(ctx: dict[str, Any], task_id: str, **kwargs: Any) -> dict[str, Any]:
    """Execute an evaluation task using diting-core.
    
    This worker task:
    1. Fetches the task from database
    2. Extracts configuration (LLM, embedding, metric)
    3. Runs evaluation using EvaluationRunner
    4. Saves result to EvaluationResult
    5. Updates task status
    
    Args:
        ctx: ARQ context
        task_id: Task ID string
        **kwargs: Additional ARQ parameters (e.g., _priority)
        
    Returns:
        dict: Task execution result
    """
    task_uuid = UUID(task_id)
    
    async with AsyncSessionLocal() as db:
        task = await db.get(Task, task_uuid)
        if not task:
            logger.error("Task not found", task_id=task_id)
            return {"error": "Task not found"}
        
        try:
            # Update task status to running
            await update_task_status(task_uuid, TaskStatus.RUNNING, Decimal("10"))
            
            # Extract configuration
            config = task.config
            metric_config = config.get("metric_config", {})
            metric_name: str = str(metric_config.get("metric_name", "answer_correctness"))
            
            # Get LLM config (from task or defaults)
            llm_config = config.get("llm_config")
            
            # If we have a config with "name" but no api_key, look up model in DB by name
            if llm_config and llm_config.get("name") and not llm_config.get("api_key"):
                model_name = str(llm_config.get("name"))
                db_model_cfg = await _get_model_config_by_name(db, model_name, ModelTypeEnum.LLM)
                if db_model_cfg:
                    # Found the model in DB, use its full config
                    llm_config = db_model_cfg
                else:
                    # Model not found in DB, try default
                    db_default_llm = await _get_default_model_config(db, ModelTypeEnum.LLM)
                    if db_default_llm:
                        llm_config = db_default_llm
            
            # If still no config, use DB default or settings default
            if not llm_config:
                db_default_llm = await _get_default_model_config(db, ModelTypeEnum.LLM)
                llm_config = db_default_llm or get_default_llm_config()
            
            # Get embedding config if needed
            embedding_config = config.get("embedding_config")
            
            # If we have a config with "name" but no api_key, look up model in DB by name
            if embedding_config and embedding_config.get("name") and not embedding_config.get("api_key"):
                model_name = str(embedding_config.get("name"))
                db_model_cfg = await _get_model_config_by_name(db, model_name, ModelTypeEnum.EMBEDDING)
                if db_model_cfg:
                    # Found the model in DB, use its full config
                    embedding_config = db_model_cfg
                else:
                    # Model not found in DB, try default
                    db_default_emb = await _get_default_model_config(db, ModelTypeEnum.EMBEDDING)
                    if db_default_emb:
                        embedding_config = db_default_emb
            
            # If still no config, use DB default or settings default
            if not embedding_config:
                db_default_emb = await _get_default_model_config(db, ModelTypeEnum.EMBEDDING)
                embedding_config = db_default_emb or get_default_embedding_config()
            
            # Get test cases
            test_cases: list[Any] = config.get("test_cases", [])  # type: ignore
            if not test_cases:
                raise ValueError("No test cases provided")
            
            logger.info(
                "Running evaluation",
                metric_name=metric_name,
                test_cases_count=len(test_cases),
            )
            
            await update_task_status(task_uuid, TaskStatus.RUNNING, Decimal("30"))
            
            # Process test cases (use first one for single evaluation)
            test_case_data: Dict[str, Any] = test_cases[0]  # type: ignore
            
            # Run evaluation using diting-core
            result = await EvaluationRunner.run_evaluation(
                metric_name=metric_name,
                test_case_data=test_case_data,
                llm_config=llm_config,
                embedding_config=embedding_config,
                metric_params=metric_config.get("params", {}),
            )
            
            await update_task_status(task_uuid, TaskStatus.RUNNING, Decimal("80"))
            
            # Save evaluation result (result is a dict, not an object)
            eval_result = EvaluationResult(
                task_id=task.id,
                metric_name=metric_name,
                score=result["score"],
                reason=result["reason"],
                user_input=test_case_data.get("user_input"),
                actual_output=test_case_data.get("actual_output"),
                expected_output=test_case_data.get("expected_output"),
                context=test_case_data.get("context"),
                retrieval_context=test_case_data.get("retrieval_context"),
                run_logs=result["run_logs"],
                usages=result["usages"],
            )
            db.add(eval_result)
            
            # Update task
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc)
            task.progress = Decimal("100.00")
            task.result = {
                "metric_name": metric_name,
                "score": float(result["score"]) if result["score"] is not None else None,
                "reason": result["reason"],
            }
            
            # Calculate tokens (cost temporarily disabled)
            total_tokens = 0
            if result["usages"]:
                for usage in result["usages"]:
                    total_tokens += usage.get("total_tokens", 0)
            
            task.total_tokens = total_tokens
            task.total_cost = Decimal("0.00")  # Cost tracking disabled
            
            await db.commit()
            
            logger.info(
                "Evaluation task completed",
                task_id=task_id,
                metric_name=metric_name,
                score=result["score"],
            )
            return {"status": "success", "result": result}
            
        except Exception as e:
            logger.error("Evaluation task failed", task_id=task_id, error=str(e), exc_info=True)
            
            # Update task status to failed
            await update_task_status(task_uuid, TaskStatus.FAILED, error=str(e))
            
            return {"status": "error", "error": str(e)}


async def synthesis_task(ctx: dict[str, Any], task_id: str, **kwargs: Any) -> dict[str, Any]:
    """Execute a synthesis task using diting-core.
    
    This worker task:
    1. Fetches the task from database
    2. Extracts configuration (LLM, synthesizer, input data)
    3. Runs synthesis using SynthesisRunner
    4. Saves results to SynthesisResult
    5. Updates task status
    
    Args:
        ctx: ARQ context
        task_id: Task ID string
        **kwargs: Additional ARQ parameters (e.g., _priority)
        
    Returns:
        dict: Task execution result
    """
    task_uuid = UUID(task_id)
    
    async with AsyncSessionLocal() as db:
        task = await db.get(Task, task_uuid)
        if not task:
            logger.error("Task not found", task_id=task_id)
            return {"error": "Task not found"}
        
        try:
            # Update task status to running
            await update_task_status(task_uuid, TaskStatus.RUNNING, Decimal("10"))
            
            # Extract configuration
            config: Dict[str, Any] = task.config  # type: ignore
            synthesizer_config: Dict[str, Any] = config.get("synthesizer_config", {})  # type: ignore
            # Note: synthesizer_type must match the snake_case name from SynthesizerFactory
            # For QASynthesizer, use "q_a_synthesizer" (not "qa" or "qa_synthesizer")
            synthesizer_type: str = str(synthesizer_config.get("type", "q_a_synthesizer"))
            num_generations: int = int(synthesizer_config.get("num_generations", 1))
            
            # Get LLM config
            llm_config = config.get("llm_config")
            
            # If we have a config with "name" but no api_key, look up model in DB by name
            if llm_config and llm_config.get("name") and not llm_config.get("api_key"):
                model_name = llm_config.get("name")
                db_model_cfg = await _get_model_config_by_name(db, model_name, ModelTypeEnum.LLM)
                if db_model_cfg:
                    # Found the model in DB, use its full config
                    llm_config = db_model_cfg
                else:
                    # Model not found in DB, try default
                    db_default_llm = await _get_default_model_config(db, ModelTypeEnum.LLM)
                    if db_default_llm:
                        llm_config = db_default_llm
            
            # If still no config, use DB default or settings default
            if not llm_config:
                db_default_llm = await _get_default_model_config(db, ModelTypeEnum.LLM)
                llm_config = db_default_llm or get_default_llm_config()
            
            # Get corpus data (supports three modes: manual, dataset, file)
            input_data = config.get("input_data")
            if not input_data:
                raise ValueError("No input data provided")
            
            corpus_data = {}
            
            # Mode 1: Manual input (direct context/themes)
            if input_data.get("context") or input_data.get("themes"):
                logger.info("Using manual input mode")
                if input_data.get("context"):
                    corpus_data["context"] = input_data["context"]
                if input_data.get("themes"):
                    corpus_data["themes"] = input_data["themes"]
            
            # Mode 2: Dataset import (from database)
            elif input_data.get("dataset_id"):
                dataset_id = input_data["dataset_id"]
                logger.info("Using dataset import mode", dataset_id=dataset_id)
                context_field = input_data.get("context_field")
                theme_field = input_data.get("theme_field")
                
                # Load data from dataset
                from uuid import UUID as PyUUID
                dataset = await db.get(Dataset, PyUUID(dataset_id))
                if not dataset:
                    raise ValueError(f"Dataset {dataset_id} not found")
                
                # Extract data from dataset rows
                contexts = []
                themes_set = set()
                
                for row in dataset.rows:
                    row_data = row.data
                    
                    # Extract context
                    if context_field and context_field in row_data:
                        context_value = row_data[context_field]
                        if isinstance(context_value, list):
                            context_value = '\n'.join(str(v) for v in context_value)
                        else:
                            context_value = str(context_value)
                        if context_value.strip():
                            contexts.append(context_value.strip())
                    
                    # Extract theme
                    if theme_field and theme_field in row_data:
                        theme_value = str(row_data[theme_field])
                        if theme_value.strip():
                            # Split by comma if multiple themes
                            for t in theme_value.split(','):
                                t = t.strip()
                                if t:
                                    themes_set.add(t)
                
                if contexts:
                    corpus_data["context"] = contexts
                if themes_set:
                    corpus_data["themes"] = list(themes_set)
            
            # Mode 3: File upload (temporary parsing)
            elif input_data.get("file_content"):
                logger.info("Using file upload mode", file_name=input_data.get("file_name"))
                import base64
                import pandas as pd
                from io import BytesIO
                from diting_web.utils.dataset_parser import DatasetParser
                
                # Decode base64 file content
                file_content = base64.b64decode(input_data["file_content"])
                file_type = input_data.get("file_type", "csv")
                context_field = input_data.get("file_context_field")
                theme_field = input_data.get("file_theme_field")
                
                # Parse file
                if file_type == "csv":
                    df = DatasetParser._read_csv_with_encoding(file_content)
                elif file_type in {"xls", "xlsx"}:
                    df = pd.read_excel(BytesIO(file_content), engine="openpyxl")
                elif file_type == "jsonl":
                    df = DatasetParser._read_jsonl(file_content)
                else:
                    raise ValueError(f"Unsupported file type: {file_type}")
                
                # Extract data
                contexts = []
                themes_set = set()
                
                for _, row in df.iterrows():
                    # Extract context
                    if context_field and context_field in row:
                        context_value = row[context_field]
                        if pd.notna(context_value):
                            if isinstance(context_value, list):
                                context_value = '\n'.join(str(v) for v in context_value)
                            else:
                                context_value = str(context_value)
                            if context_value.strip():
                                contexts.append(context_value.strip())
                    
                    # Extract theme
                    if theme_field and theme_field in row:
                        theme_value = row[theme_field]
                        if pd.notna(theme_value):
                            theme_value = str(theme_value)
                            if theme_value.strip():
                                for t in theme_value.split(','):
                                    t = t.strip()
                                    if t:
                                        themes_set.add(t)
                
                if contexts:
                    corpus_data["context"] = contexts
                if themes_set:
                    corpus_data["themes"] = list(themes_set)
            
            # Validate that at least one of context or themes is provided
            if not corpus_data.get("context") and not corpus_data.get("themes"):
                raise ValueError("No corpus data or context provided")
            
            logger.info(
                "Running synthesis",
                synthesizer_type=synthesizer_type,
                num_generations=num_generations,
                context_items=len(corpus_data.get("context", [])),
            )
            
            await update_task_status(task_uuid, TaskStatus.RUNNING, Decimal("30"))
            
            # Run synthesis using diting-core (token tracking handled internally)
            results, usages = await SynthesisRunner.run_synthesis(
                synthesizer_type=synthesizer_type,
                corpus_data=corpus_data,
                llm_config=llm_config,
                synthesizer_params=synthesizer_config.get("params", {}),
                num_generations=num_generations,
            )
            
            await update_task_status(task_uuid, TaskStatus.RUNNING, Decimal("80"))
            
            # Check if any results were generated
            if not results:
                error_msg = f"Failed to generate any samples (requested: {num_generations}, generated: 0). Please check model connectivity and configuration."
                logger.error(
                    "No synthesis results generated",
                    task_id=task_id,
                    requested=num_generations,
                )
                await update_task_status(task_uuid, TaskStatus.FAILED, error=error_msg)
                return {"status": "error", "error": error_msg}
            
            # Save synthesis results
            for item in results:
                # Extract optional fields
                source_context = item.get("context") or item.get("source_context")
                metadata = item.get("metadata") or {}
                quality_score = metadata.get("score") if isinstance(metadata, dict) else None

                synth_result = SynthesisResult(
                    task_id=task.id,
                    question=item.get("question", ""),
                    answer=item.get("answer", ""),
                    source_context=source_context if source_context else None,
                    quality_score=quality_score,
                )
                db.add(synth_result)
            
            # Calculate total tokens from usages returned by SynthesisRunner
            total_tokens = sum(u.total_tokens for u in usages) if usages else 0
            total_cost = Decimal("0.00")
            
            # Update task
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc)
            task.progress = Decimal("100.00")
            task.result = {
                "count": len(results),
                "results": results,
            }
            task.total_tokens = total_tokens
            task.total_cost = total_cost
            
            await db.commit()
            
            logger.info(
                "Synthesis task completed",
                task_id=task_id,
                count=len(results),
                tokens=total_tokens,
            )
            return {"status": "success", "result": results}
            
        except Exception as e:
            logger.error("Synthesis task failed", task_id=task_id, error=str(e), exc_info=True)
            
            # Update task status to failed
            await update_task_status(task_uuid, TaskStatus.FAILED, error=str(e))
            
            return {"status": "error", "error": str(e)}


async def batch_evaluation_task(ctx: dict[str, Any], task_id: str, **kwargs: Any) -> dict[str, Any]:
    """Execute a batch evaluation task using diting-core.

    This worker task:
    1. Fetches the task and dataset from database
    2. Gets evaluator and metrics
    3. Processes each row in the dataset with each metric
    4. Saves results for each evaluation
    5. Updates task status and progress

    Args:
        ctx: ARQ context
        task_id: Task ID string
        **kwargs: Additional ARQ parameters (e.g., _priority)

    Returns:
        dict: Task execution result
    """
    task_uuid = UUID(task_id)

    async with AsyncSessionLocal() as db:
        task = await db.get(Task, task_uuid)
        if not task:
            logger.error("Task not found", task_id=task_id)
            return {"error": "Task not found"}

        try:
            # Update task status to running
            await update_task_status(task_uuid, TaskStatus.RUNNING, Decimal("5"))

            # Get dataset
            dataset = await db.get(Dataset, task.dataset_id)
            if not dataset:
                raise ValueError(f"Dataset {task.dataset_id} not found")

            # Extract configuration
            config = task.config
            evaluator_id = config.get("evaluator_id")

            # Get LLM and embedding configs
            llm_config = config.get("llm_config")
            if not llm_config:
                llm_config = get_default_llm_config()

            embedding_config = config.get("embedding_config")
            if not embedding_config:
                embedding_config = get_default_embedding_config()

            # Get evaluator and its metrics/configs
            metrics_to_run = []
            if evaluator_id:
                evaluator = await db.get(Evaluator, evaluator_id)
                if not evaluator:
                    raise ValueError(f"Evaluator {evaluator_id} not found")
                
                # Get all metrics from evaluator's metric_ids
                if not evaluator.metric_ids:
                    raise ValueError(f"Evaluator {evaluator_id} has no metrics")
                
                # Query metrics by IDs
                metrics_query = select(Metric).where(Metric.id.in_(evaluator.metric_ids))
                metrics_result = await db.execute(metrics_query)
                metrics_to_run = list(metrics_result.scalars().all())
                
                if not metrics_to_run:
                    raise ValueError(f"Metrics not found for evaluator {evaluator_id}")
            else:
                raise ValueError("evaluator_id is required for evaluation tasks")

            # Get dataset rows (data is stored in DatasetRow table)
            dataset_rows = dataset.rows  # Already loaded via lazy="selectin"
            if not dataset_rows:
                raise ValueError(f"Dataset {task.dataset_id} has no data")

            total_items = len(dataset_rows)
            total_metrics = len(metrics_to_run)
            total_evaluations = total_items * total_metrics

            logger.info(
                "Running batch evaluation",
                task_id=task_id,
                dataset_id=str(task.dataset_id),
                items=total_items,
                metrics=total_metrics,
                total_evaluations=total_evaluations,
            )

            await update_task_status(task_uuid, TaskStatus.RUNNING, Decimal("10"))

            # Process each item with each metric
            results = []
            processed = 0
            total_tokens = 0
            failure_reasons: list[str] = []

            # Prepare evaluator-level configs (defaults + per-metric overrides)
            eval_config = evaluator.config if evaluator_id else {}
            metric_cfg_list = { (cfg.get("metric_id") or cfg.get("metric_id")): cfg for cfg in eval_config.get("metric_model_configs", []) } if isinstance(eval_config, dict) else {}
            default_llm_cfg = eval_config.get("default_llm_config") if isinstance(eval_config, dict) else None
            default_emb_cfg = eval_config.get("default_embedding_config") if isinstance(eval_config, dict) else None

            for item_idx, dataset_row in enumerate(dataset_rows):
                # Get actual data from DatasetRow.data (JSONB field)
                item = dataset_row.data
                
                for metric_idx, metric in enumerate(metrics_to_run):
                    # Update progress
                    progress = Decimal("10") + Decimal("80") * Decimal(str(processed / total_evaluations))
                    await update_task_status(task_uuid, TaskStatus.RUNNING, progress)

                    # Prepare test case
                    # Metric object from evaluator
                    metric_name = metric.name
                    metric_params = {}

                    # Resolve model configs priority: per-metric in evaluator -> evaluator defaults -> task config -> global defaults
                    per_metric_cfg = None
                    if metric_cfg_list:
                        # keys in list are strings (UUID); match against str(metric.id)
                        per_metric_cfg = metric_cfg_list.get(str(metric.id)) or next((m for m in metric_cfg_list.values() if (m.get("metric_id") == str(metric.id))), None)

                    # Resolve LLM config: evaluator -> task -> DB model by name -> DB default -> settings
                    llm_cfg_effective = None
                    if per_metric_cfg and per_metric_cfg.get("llm_config"):
                        llm_cfg_effective = per_metric_cfg.get("llm_config")
                    elif default_llm_cfg:
                        llm_cfg_effective = default_llm_cfg
                    elif llm_config:
                        llm_cfg_effective = llm_config
                    else:
                        llm_cfg_effective = None
                    
                    # If we have a config with "name" but no api_key, look up model in DB by name
                    if llm_cfg_effective and llm_cfg_effective.get("name") and not llm_cfg_effective.get("api_key"):
                        model_name = llm_cfg_effective.get("name")
                        db_model_cfg = await _get_model_config_by_name(db, model_name, ModelTypeEnum.LLM)
                        if db_model_cfg:
                            # Found the model in DB, use its full config
                            llm_cfg_effective = db_model_cfg
                        else:
                            # Model not found in DB, try default
                            db_default_llm = await _get_default_model_config(db, ModelTypeEnum.LLM)
                            if db_default_llm:
                                llm_cfg_effective = db_default_llm
                    
                    # If still no config, use DB default or settings default
                    if not llm_cfg_effective:
                        db_default_llm = await _get_default_model_config(db, ModelTypeEnum.LLM)
                        llm_cfg_effective = db_default_llm or get_default_llm_config()

                    # Resolve Embedding config: evaluator -> task -> DB model by name -> DB default -> settings
                    emb_cfg_effective = None
                    if per_metric_cfg and per_metric_cfg.get("embedding_config"):
                        emb_cfg_effective = per_metric_cfg.get("embedding_config")
                    elif default_emb_cfg:
                        emb_cfg_effective = default_emb_cfg
                    elif embedding_config:
                        emb_cfg_effective = embedding_config
                    else:
                        emb_cfg_effective = None
                    
                    # If we have a config with "name" but no api_key, look up model in DB by name
                    if emb_cfg_effective and emb_cfg_effective.get("name") and not emb_cfg_effective.get("api_key"):
                        model_name = emb_cfg_effective.get("name")
                        db_model_cfg = await _get_model_config_by_name(db, model_name, ModelTypeEnum.EMBEDDING)
                        if db_model_cfg:
                            emb_cfg_effective = db_model_cfg
                        else:
                            db_default_emb = await _get_default_model_config(db, ModelTypeEnum.EMBEDDING)
                            if db_default_emb:
                                emb_cfg_effective = db_default_emb
                    
                    # If still no config, use DB default or settings default
                    if not emb_cfg_effective:
                        db_default_emb = await _get_default_model_config(db, ModelTypeEnum.EMBEDDING)
                        emb_cfg_effective = db_default_emb or get_default_embedding_config()

                    test_case_data = {
                        "user_input": item.get("user_input") or item.get("query") or item.get("question"),
                        "actual_output": item.get("actual_output") or item.get("answer"),
                        "expected_output": item.get("expected_output"),
                        "context": item.get("context"),
                        "retrieval_context": item.get("retrieval_context"),
                    }

                    # Run evaluation
                    try:
                        result = await EvaluationRunner.run_evaluation(
                            metric_name=metric_name,
                            test_case_data=test_case_data,
                            llm_config=_normalize_model_config(llm_cfg_effective),
                            embedding_config=_normalize_model_config(emb_cfg_effective),
                            metric_params=metric_params,
                        )

                        # Save result (result is a dict, not an object)
                        eval_result = EvaluationResult(
                            task_id=task.id,
                            metric_name=metric_name,
                            score=result["score"],
                            reason=result["reason"],
                            user_input=test_case_data.get("user_input"),
                            actual_output=test_case_data.get("actual_output"),
                            expected_output=test_case_data.get("expected_output"),
                            context=test_case_data.get("context"),
                            retrieval_context=test_case_data.get("retrieval_context"),
                            run_logs=result["run_logs"],
                            usages=result["usages"],
                        )
                        db.add(eval_result)

                        # Accumulate tokens
                        if result["usages"]:
                            for usage in result["usages"]:
                                total_tokens += usage.get("total_tokens", 0)

                        results.append({
                            "item_idx": item_idx,
                            "metric_name": metric_name,
                            "score": float(result["score"]) if result["score"] is not None else None,
                        })

                    except Exception as e:
                        logger.warning(
                            "Evaluation failed for item",
                            task_id=task_id,
                            item_idx=item_idx,
                            metric_name=metric_name,
                            error=str(e),
                        )
                        # Collect first-level reason for later error surfacing
                        error_msg = str(e)
                        try:
                            # truncate very long SDK call stacks to avoid excessive logging
                            if len(error_msg) > 200:
                                error_msg = error_msg[:200] + "..."
                            failure_reasons.append(f"{metric_name}: {error_msg}")
                        except Exception:
                            pass
                        
                        # IMPORTANT: Save failed evaluation to database too
                        # This ensures all metrics appear in statistics even if they failed
                        eval_result = EvaluationResult(
                            task_id=task.id,
                            metric_name=metric_name,
                            score=None,  # No score for failed evaluation
                            reason=f"评估失败: {error_msg}",
                            user_input=test_case_data.get("user_input"),
                            actual_output=test_case_data.get("actual_output"),
                            expected_output=test_case_data.get("expected_output"),
                            context=test_case_data.get("context"),
                            retrieval_context=test_case_data.get("retrieval_context"),
                            run_logs=None,
                            usages=None,
                        )
                        db.add(eval_result)
                        
                        results.append({
                            "item_idx": item_idx,
                            "metric_name": metric_name,
                            "score": None,  # Failed evaluation has no score
                        })

                    processed += 1

            await update_task_status(task_uuid, TaskStatus.RUNNING, Decimal("95"))

            # Check if any evaluation succeeded
            if processed == 0:
                # All evaluations failed
                task.status = TaskStatus.FAILED
                # Surface the first failure reason to the UI for better diagnosability
                surfaced = failure_reasons[0] if failure_reasons else "未知错误"
                task.error = f"所有评估失败：{surfaced}"
                task.completed_at = datetime.now(timezone.utc)
                task.progress = Decimal("100.00")
                task.result = {
                    "total_items": total_items,
                    "total_metrics": total_metrics,
                    "total_evaluations": 0,
                    "results": [],
                    "error_summary": "所有评估都失败，未生成任何结果",
                    "error_details": failure_reasons,
                }
                await db.commit()
                
                logger.error(
                    "Batch evaluation task failed - no successful evaluations",
                    task_id=task_id,
                    total_items=total_items,
                    total_metrics=total_metrics,
                )
                return {
                    "status": "error",
                    "error": "所有评估都失败，未生成任何结果",
                }

            # Update task as completed
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc)
            task.progress = Decimal("100.00")
            task.result = {
                "total_items": total_items,
                "total_metrics": total_metrics,
                "total_evaluations": processed,
                "success_rate": processed / total_evaluations if total_evaluations > 0 else 0,
                "results": results,
            }
            task.total_tokens = total_tokens
            task.total_cost = Decimal("0.00")  # Cost tracking disabled

            await db.commit()

            logger.info(
                "Batch evaluation task completed",
                task_id=task_id,
                processed=processed,
                total_evaluations=total_evaluations,
                success_rate=f"{processed}/{total_evaluations}",
                tokens=total_tokens,
            )
            return {
                "status": "success",
                "result": {
                    "total_items": total_items,
                    "total_metrics": total_metrics,
                    "total_evaluations": processed,
                    "results": results,
                }
            }

        except Exception as e:
            logger.error(
                "Batch evaluation task failed",
                task_id=task_id,
                error=str(e),
                exc_info=True,
            )

            # Update task status to failed
            await update_task_status(task_uuid, TaskStatus.FAILED, error=str(e))

            return {"status": "error", "error": str(e)}


async def negative_mining_task(ctx: dict[str, Any], task_id: str, **kwargs: Any) -> dict[str, Any]:
    """Execute a negative mining task.

    This worker task:
    1. Fetches the task from database
    2. Creates embedding model from config
    3. Runs negative mining using NegativeMiningService
    4. Saves results to task.result
    5. Updates task status

    Args:
        ctx: ARQ context
        task_id: Task ID string
        **kwargs: Additional ARQ parameters (e.g., _priority)

    Returns:
        dict: Task execution result
    """
    task_uuid = UUID(task_id)

    async with AsyncSessionLocal() as db:
        task = await db.get(Task, task_uuid)
        if not task:
            logger.error("Task not found", task_id=task_id)
            return {"error": "Task not found"}

        try:
            # Update task status to running
            await update_task_status(task_uuid, TaskStatus.RUNNING, Decimal("10"))

            # Extract configuration
            config = task.config
            embedding_config = config.get("embedding_config")
            
            # If we have a config with "name" but no api_key, look up model in DB by name
            if embedding_config and embedding_config.get("name") and not embedding_config.get("api_key"):
                model_name = embedding_config.get("name")
                db_model_cfg = await _get_model_config_by_name(db, model_name, ModelTypeEnum.EMBEDDING)
                if db_model_cfg:
                    # Found the model in DB, use its full config
                    embedding_config = db_model_cfg
                else:
                    # Model not found in DB, try default
                    db_default_emb = await _get_default_model_config(db, ModelTypeEnum.EMBEDDING)
                    if db_default_emb:
                        embedding_config = db_default_emb
            
            # If still no config, use DB default or settings default
            if not embedding_config:
                db_default_emb = await _get_default_model_config(db, ModelTypeEnum.EMBEDDING)
                embedding_config = db_default_emb or get_default_embedding_config()

            input_data = config.get("input_data", {})
            
            # Load train_data from different sources
            train_data = []
            
            # Mode 1: Direct train_data input
            if input_data.get("train_data"):
                train_data = input_data.get("train_data", [])
            
            # Mode 2: Load from dataset with field mapping
            elif input_data.get("dataset_id"):
                logger.info("Loading train_data from dataset", dataset_id=input_data["dataset_id"])
                dataset_id = input_data["dataset_id"]
                query_field = input_data.get("query_field")
                pos_field = input_data.get("pos_field")
                neg_field = input_data.get("neg_field")
                
                if not query_field or not pos_field:
                    raise ValueError("query_field and pos_field are required when using dataset_id")
                
                # Load data from dataset
                from uuid import UUID as PyUUID
                from diting_web.models.dataset import Dataset, DatasetRow
                from sqlalchemy import select
                
                dataset = await db.get(Dataset, PyUUID(dataset_id))
                if not dataset:
                    raise ValueError(f"Dataset {dataset_id} not found")
                
                # Query all rows from dataset_rows table
                query = select(DatasetRow).where(
                    DatasetRow.dataset_id == PyUUID(dataset_id)
                ).order_by(DatasetRow.row_index)
                result = await db.execute(query)
                rows = result.scalars().all()
                
                # Convert to train_data format
                for row in rows:
                    query_val = str(row.data.get(query_field) or "").strip()
                    if not query_val:
                        continue
                    
                    # Process pos field (array or string)
                    pos_value = row.data.get(pos_field)
                    pos = []
                    if pos_value:
                        if isinstance(pos_value, list):
                            pos = [str(v).strip() for v in pos_value if str(v).strip()]
                        else:
                            import re
                            pos_str = str(pos_value)
                            pos = [v.strip() for v in re.split(r'[,\n]', pos_str) if v.strip()]
                    
                    # Process neg field (optional)
                    neg = []
                    if neg_field and row.data.get(neg_field):
                        neg_value = row.data.get(neg_field)
                        if isinstance(neg_value, list):
                            neg = [str(v).strip() for v in neg_value if str(v).strip()]
                        else:
                            import re
                            neg_str = str(neg_value)
                            neg = [v.strip() for v in re.split(r'[,\n]', neg_str) if v.strip()]
                    
                    if query_val and pos:
                        train_item = {
                            "query": query_val,
                            "pos": pos,
                        }
                        if neg:
                            train_item["neg"] = neg
                        train_data.append(train_item)
                
                logger.info(
                    "Loaded train_data from dataset",
                    dataset_id=dataset_id,
                    total_rows=len(rows),
                    converted_train_data=len(train_data),
                )
            
            candidate_pool = input_data.get("candidate_pool")

            sample_range = config.get("sample_range", "10-210")
            negative_number = config.get("negative_number", 15)
            use_gpu = config.get("use_gpu", False)
            embedding_batch_size = config.get("embedding_batch_size", 32)

            if not train_data:
                raise ValueError("No training data provided - check dataset_id/fields or train_data")

            logger.info(
                "Running negative mining",
                task_id=task_id,
                train_data_size=len(train_data),
                sample_range=sample_range,
                negative_number=negative_number,
            )

            await update_task_status(task_uuid, TaskStatus.RUNNING, Decimal("30"))

            # Create embedding model
            embedding_model = create_embedding_from_config(embedding_config)

            # Create callback handler to track token usage (same as EvaluationRunner)
            get_embed_token = GetEmbedTokenCallbackHandler()
            callbacks = [get_embed_token]

            # Run negative mining
            enhanced_data, _ = await NegativeMiningService.mine_negatives(
                embedding_model=embedding_model,
                train_data=train_data,
                candidate_pool=candidate_pool,
                sample_range=sample_range,
                negative_number=negative_number,
                use_gpu=use_gpu,
                embedding_batch_size=embedding_batch_size,
                callbacks=callbacks,
            )

            await update_task_status(task_uuid, TaskStatus.RUNNING, Decimal("90"))

            # Compute token usage from callbacks (same as EvaluationRunner)
            usages = compute_token_usage(
                llm_usages=[],  # Negative mining doesn't use LLM
                embed_usages=get_embed_token.usages,
            )
            
            # Calculate total tokens
            total_tokens = sum(u.total_tokens for u in usages) if usages else 0

            # Update task
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc)
            task.progress = Decimal("100.00")
            task.result = {
                "enhanced_data": enhanced_data,
                "count": len(enhanced_data),
            }
            task.total_tokens = total_tokens
            task.total_cost = Decimal("0.00")  # Embedding costs are typically separate

            await db.commit()

            logger.info(
                "Negative mining task completed",
                task_id=task_id,
                count=len(enhanced_data),
            )
            return {"status": "success", "result": enhanced_data}

        except Exception as e:
            logger.error(
                "Negative mining task failed",
                task_id=task_id,
                error=str(e),
                exc_info=True,
            )

            # Update task status to failed
            await update_task_status(task_uuid, TaskStatus.FAILED, error=str(e))

            return {"status": "error", "error": str(e)}
