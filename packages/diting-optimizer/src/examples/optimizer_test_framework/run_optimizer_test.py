"""
运行优化器测试的示例脚本
"""

import asyncio
import argparse
import logging
from pathlib import Path

from examples.optimizer_test_framework.logging_config import get_logger, setup_logging
from examples.optimizer_test_framework.optimizer_test_framework import (
    OptimizerTestFramework,
    OptimizerTestConfig,
)

logger = get_logger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="运行优化器测试")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/example_test_config.yaml",
        help="配置文件路径",
    )
    parser.add_argument("--tasks", nargs="+", help="指定要运行的任务名称（可选）")
    parser.add_argument(
        "--mode", choices=["sequential", "parallel", "batch"], help="覆盖执行模式"
    )
    parser.add_argument("--workers", type=int, help="覆盖最大并发数")
    parser.add_argument("--samples", type=int, help="覆盖每个任务的样本数")
    parser.add_argument(
        "--quiet", action="store_true", help="静默模式，只显示错误和最终结果"
    )
    args = parser.parse_args()

    # 设置静默模式
    log_level = "WARNING" if args.quiet else "INFO"
    setup_logging(level=getattr(logging, log_level))

    # 检查配置文件
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"配置文件不存在: {config_path}")
        logger.info("可用的配置文件:")
        configs_dir = Path("configs")
        if configs_dir.exists():
            for config_file in configs_dir.glob("*.yaml"):
                logger.info(f"  - {config_file}")
        return

    # 加载配置
    config = OptimizerTestConfig.from_file(config_path)

    # 应用命令行覆盖
    if args.mode:
        config.execution.execution_mode = args.mode
        logger.info(f"执行模式已覆盖为: {args.mode}")

    if args.workers:
        config.execution.max_workers = args.workers
        logger.info(f"最大并发数已覆盖为: {args.workers}")

    if args.samples:
        for task in config.tasks:
            task.n_samples = args.samples
        logger.info(f"样本数已覆盖为: {args.samples}")

    # 运行测试
    logger.info("=" * 60)
    logger.info("开始执行优化器测试")
    logger.info(f"配置文件: {config_path}")
    logger.info(f"测试名称: {config.name}")
    logger.info(f"任务数量: {len(config.tasks)}")
    logger.info(f"执行模式: {config.execution.execution_mode}")
    logger.info(f"最大并发数: {config.execution.max_workers}")

    # 开始执行

    if args.tasks:
        logger.info(f"指定任务: {', '.join(args.tasks)}")
        # 验证任务名称
        task_names = {t.name for t in config.tasks}
        invalid_tasks = set(args.tasks) - task_names
        if invalid_tasks:
            logger.warning(f"以下任务不存在: {', '.join(invalid_tasks)}")
            logger.warning(f"可用任务: {', '.join(task_names)}")

    # 创建框架并运行
    framework = OptimizerTestFramework(config)
    await framework.run(args.tasks)


if __name__ == "__main__":
    asyncio.run(main())
