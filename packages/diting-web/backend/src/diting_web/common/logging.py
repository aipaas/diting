"""Logging configuration."""

import logging
import sys
from typing import Any

import structlog


def configure_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """Configure structured logging."""
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level.upper(),
    )
    
    # 降低第三方库的日志级别，避免刷屏
    # HTTP 请求库日志（httpx/httpcore）
    # 设置为 ERROR 以完全屏蔽 TRACE/DEBUG/INFO/WARNING 级别的详细日志
    logging.getLogger("httpx").setLevel(logging.ERROR)
    logging.getLogger("httpcore").setLevel(logging.ERROR)
    logging.getLogger("httpcore.connection").setLevel(logging.ERROR)
    logging.getLogger("httpcore.http11").setLevel(logging.ERROR)
    logging.getLogger("httpcore.proxy").setLevel(logging.ERROR)
    
    # LangChain 相关日志
    logging.getLogger("langchain").setLevel(logging.WARNING)
    logging.getLogger("langchain_core").setLevel(logging.WARNING)
    logging.getLogger("langchain_openai").setLevel(logging.WARNING)
    
    # OpenAI 客户端日志
    logging.getLogger("openai").setLevel(logging.WARNING)
    
    # ARQ worker 日志保持INFO级别（重要任务信息）
    logging.getLogger("arq").setLevel(logging.INFO)

    # Configure structlog
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.extend([
            structlog.dev.ConsoleRenderer(colors=True),
        ])

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a logger instance."""
    return structlog.get_logger(name)

