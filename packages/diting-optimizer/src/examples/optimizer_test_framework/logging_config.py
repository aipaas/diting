"""
统一的日志配置管理
"""

import logging
import sys
from typing import Optional


def setup_logging(
    level: int = logging.INFO,
    verbose_http: bool = False,
    format_string: Optional[str] = None,
) -> None:
    """设置统一的日志配置

    Args:
        level: 日志级别
        verbose_http: 是否启用HTTP详细日志
        format_string: 自定义日志格式
    """
    # 设置根日志级别
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 清除现有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 创建格式化器
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")

    # 添加控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 控制HTTP日志级别
    if not verbose_http:
        # 禁用详细的HTTP日志
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """获取日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        日志记录器实例
    """
    return logging.getLogger(name)
