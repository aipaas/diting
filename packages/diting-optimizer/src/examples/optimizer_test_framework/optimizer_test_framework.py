"""
优化器测试框架
支持并发或串行执行不同dataset、不同metric下的optimizer效果测试
"""

import importlib
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from diting_core.models.embeddings.factory import embedding_factory
from diting_core.models.llms.factory import llm_factory
from diting_optimizer.target.prompt_config import PromptConfig
from .config import OptimizerTestConfig, TestTaskConfig, LLMConfig, EmbeddingConfig
from .executor import ExecutionMode, TaskExecutor
from .report import ReportGenerator
from .logging_config import setup_logging, get_logger

logger = get_logger(__name__)


class OptimizerTestFramework:
    """优化器测试框架主类"""

    def __init__(self, config: OptimizerTestConfig):
        self.config = config
        self.report_generator = ReportGenerator(
            output_dir=config.execution.report_dir,
            format=config.execution.report_format,
        )
        self._cached_models: Dict[str, Any] = {}
        self._cached_datasets: Dict[str, Any] = {}
        self._cached_metrics: Dict[str, Any] = {}
        self._cached_optimizers: Dict[str, Any] = {}
        self._test_timestamp = None  # 添加时间戳属性

    async def setup(self):
        """初始化框架，准备资源"""
        # 创建报告目录和生成时间戳
        self._test_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report_generator.setup()

        # 根据配置重新设置日志
        try:
            # 转换日志级别字符串
            log_level_map = {
                "DEBUG": logging.DEBUG,
                "INFO": logging.INFO,
                "WARNING": logging.WARNING,
                "ERROR": logging.ERROR,
            }
            level = log_level_map.get(
                self.config.execution.log_level.upper(), logging.INFO
            )

            setup_logging(level=level, verbose_http=self.config.execution.verbose_http)

            logger.info(
                f"日志配置完成 - 级别: {self.config.execution.log_level}, HTTP日志: {'启用' if self.config.execution.verbose_http else '禁用'}"
            )
        except Exception as e:
            logger.warning(f"日志配置失败: {e}")

        # 预加载LLM和Embedding
        if self.config.generate_llm:
            self._cached_models["generate"] = self._create_llm(self.config.generate_llm)
        if self.config.eval_llm:
            self._cached_models["eval"] = self._create_llm(self.config.eval_llm)
        if self.config.optimize_llm:
            self._cached_models["optimize"] = self._create_llm(self.config.optimize_llm)
        if self.config.embedding:
            self._cached_models["embedding"] = self._create_embedding(
                self.config.embedding
            )

    def _create_llm(self, config: LLMConfig):
        """创建LLM实例"""
        return llm_factory(
            model=config.model,
            base_url=config.base_url,
            api_key=config.api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout=config.timeout,
        )

    def _create_embedding(self, config: EmbeddingConfig):
        """创建Embedding实例"""
        return embedding_factory(
            model=config.model,
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=config.timeout,
        )

    def _load_dataset(self, dataset_config):
        """动态加载数据集"""
        key = f"{dataset_config.module_path}.{dataset_config.function_name}"
        if key not in self._cached_datasets:
            module = importlib.import_module(dataset_config.module_path)
            func = getattr(module, dataset_config.function_name)
            self._cached_datasets[key] = func()
        return self._cached_datasets[key]

    def _load_metric(self, metric_config):
        """动态加载评估指标"""
        key = f"{metric_config.module_path}.{metric_config.class_name}"
        if key not in self._cached_metrics:
            module = importlib.import_module(metric_config.module_path)
            metric_class = getattr(module, metric_config.class_name)

            # 准备参数
            params = metric_config.params.copy()

            # 如果需要模型，从缓存中获取
            if "model" in params and params["model"] == "eval":
                if "eval" not in self._cached_models:
                    raise ValueError("评估LLM未配置")
                params["model"] = self._cached_models["eval"]

            if "embedding_model" in params and params["embedding_model"] == "embedding":
                if "embedding" not in self._cached_models:
                    raise ValueError("Embedding模型未配置")
                params["embedding_model"] = self._cached_models["embedding"]

            self._cached_metrics[key] = metric_class(**params)
        return self._cached_metrics[key]

    def _load_optimizer(self, optimizer_config):
        """动态加载优化器"""
        key = f"{optimizer_config.module_path}.{optimizer_config.class_name}"
        if key not in self._cached_optimizers:
            module = importlib.import_module(optimizer_config.module_path)
            optimizer_class = getattr(module, optimizer_config.class_name)

            # 准备参数
            params = optimizer_config.params.copy()

            # 检查是否需要LLM参数
            import inspect

            sig = inspect.signature(optimizer_class.__init__)
            if "llm" in sig.parameters:
                # 优化器需要LLM参数
                if "optimize" not in self._cached_models:
                    raise ValueError("优化LLM未配置")
                params["llm"] = self._cached_models["optimize"]

            self._cached_optimizers[key] = optimizer_class(**params)
        return self._cached_optimizers[key]

    async def run_single_task(self, task_config: TestTaskConfig) -> Dict[str, Any]:
        """运行单个测试任务"""
        logger.info(f"{'=' * 50}")
        logger.info(f"开始执行任务: {task_config.name}")
        logger.info(f"数据集: {task_config.dataset.name}")
        logger.info(f"评估指标: {task_config.metric.name}")
        logger.info(f"优化器: {task_config.optimizer.name}")
        logger.info(f"{'=' * 50}")

        # 加载数据集
        dataset = self._load_dataset(task_config.dataset)

        # 创建提示配置
        generate_llm = self._cached_models.get("generate")
        if not generate_llm:
            raise ValueError("生成LLM未配置")

        prompt_config = PromptConfig(
            messages=[
                {"role": "system", "content": task_config.prompt_template},
                {"role": "user", "content": "{user_input}"},
            ],
            llm=generate_llm,
        )

        # 加载评估指标
        metric = self._load_metric(task_config.metric)

        # 加载优化器
        optimizer = self._load_optimizer(task_config.optimizer)

        # 执行优化
        start_time = datetime.now()

        # 准备优化参数
        optimize_kwargs = {
            "n_samples": task_config.n_samples,
            "verbose": False,
        }

        # 如果是ParameterOptimizer，添加parameter_space参数
        if task_config.parameter_space:
            optimize_kwargs["parameter_space"] = task_config.parameter_space

        optimization_result = await optimizer.optimize(
            prompt_config, dataset, metric, **optimize_kwargs
        )
        end_time = datetime.now()

        # 立即生成详细的优化报告（使用统一的时间戳）
        optimize_llm = self._cached_models.get("optimize")
        model_name = getattr(optimize_llm, "model_name", "unknown")
        # 清理文件名中的特殊字符
        safe_model_name = re.sub(r'[\\/:*?"<>|]', "-", model_name)
        report_filename = (
            f"{task_config.name}_{task_config.metric.name}_{safe_model_name}.md"
        )
        report_path = (
            Path(self.config.execution.report_dir)
            / "task_reports"
            / self._test_timestamp
        )
        report_path.mkdir(parents=True, exist_ok=True)

        if hasattr(optimization_result, "to_markdown"):
            try:
                optimization_result.to_markdown(str(report_path / report_filename))
                logger.info(
                    f"[报告] 任务详细报告已生成: {report_path / report_filename}"
                )
            except Exception as e:
                logger.warning(f"无法生成详细报告: {str(e)}")

        # 准备结果
        result = {
            "task_name": task_config.name,
            "dataset": task_config.dataset.name,
            "metric": task_config.metric.name,
            "optimizer": task_config.optimizer.name,
            "n_samples": task_config.n_samples,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": (end_time - start_time).total_seconds(),
            "best_score": getattr(optimization_result, "best_score", 0),
            "num_iterations": len(getattr(optimization_result, "histories", []))
            if hasattr(optimization_result, "histories")
            and optimization_result.histories
            else getattr(optimization_result, "iterations", 0),
            "optimization_result": optimization_result,
            "task_config": task_config,
            "report_file": str(report_path / report_filename),
        }

        logger.info(f"任务完成: {task_config.name}")
        logger.info(f"最佳分数: {result['best_score']:.4f}")
        logger.info(f"迭代次数: {result['num_iterations']}")
        logger.info(f"耗时: {result['duration_seconds']:.2f}秒")

        return result

    async def run_tasks(
        self, task_filter: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """运行测试任务"""
        # 过滤任务
        tasks_to_run = self.config.tasks
        if task_filter:
            tasks_to_run = [t for t in tasks_to_run if t.name in task_filter]

        if not tasks_to_run:
            logger.warning("没有找到要执行的任务")
            return []

        logger.info("开始执行优化器测试")
        logger.info(f"测试名称: {self.config.name}")
        logger.info(f"任务数量: {len(tasks_to_run)}")
        logger.info(f"执行模式: {self.config.execution.execution_mode}")

        # 选择执行模式
        execution_mode = ExecutionMode(self.config.execution.execution_mode)
        executor = TaskExecutor(
            max_workers=self.config.execution.max_workers, mode=execution_mode
        )

        # 执行任务
        results = await executor.execute(
            tasks=tasks_to_run, run_func=self.run_single_task
        )

        # 生成报告
        if self.config.execution.save_reports:
            await self.report_generator.generate_report(
                test_name=self.config.name,
                test_config=self.config,
                results=results,
                timestamp=self._test_timestamp,  # 传递统一的时间戳
            )

        # 打印汇总
        self._print_summary(results)

        return results

    def _print_summary(self, results: List[Dict[str, Any]]):
        """打印测试结果汇总"""
        logger.info(f"{'=' * 60}")
        logger.info("测试结果汇总")
        logger.info(f"{'=' * 60}")

        successful_results = []

        for result in results:
            logger.info(f"任务: {result.get('task_name', 'Unknown')}")

            if "error" in result:
                logger.error("状态: 失败")
                logger.error(f"错误: {result['error']}")
            else:
                successful_results.append(result)
                logger.info(f"  数据集: {result.get('dataset', 'Unknown')}")
                logger.info(f"  评估指标: {result.get('metric', 'Unknown')}")
                logger.info(f"  最佳分数: {result.get('best_score', 0):.4f}")
                logger.info(f"  迭代次数: {result.get('num_iterations', 0)}")
                logger.info(f"  耗时: {result.get('duration_seconds', 0):.2f}秒")

        if results:
            logger.info("总体统计:")
            logger.info(f"  总任务数: {len(results)}")
            logger.info(f"  成功任务数: {len(successful_results)}")
            logger.info(f"  失败任务数: {len(results) - len(successful_results)}")

            if successful_results:
                avg_score = sum(
                    r.get("best_score", 0) for r in successful_results
                ) / len(successful_results)
                total_time = sum(
                    r.get("duration_seconds", 0) for r in successful_results
                )
                logger.info(f"  平均分数: {avg_score:.4f}")
                logger.info(f"  总耗时: {total_time:.2f}秒")

    async def run(self, task_filter: Optional[List[str]] = None):
        """运行完整的测试流程"""
        await self.setup()
        await self.run_tasks(task_filter)
