"""
优化器模块的日志配置
"""

import logging


def setup_logging(level=logging.INFO, verbose_http=False):
    """
    设置优化器模块的日志配置

    Args:
        level: 日志级别，默认为 INFO
        verbose_http: 是否显示HTTP请求日志，默认为 False
    """
    # 配置根日志器
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,  # 确保重复调用也能生效
    )

    # 设置我们关心的模块为指定级别
    modules = [
        "diting_optimizer",
        "diting_optimizer.algorithms",
        "diting_optimizer.algorithms.prompt",
        "diting_optimizer.algorithms.prompt.prompt_messages",
        "diting_optimizer.algorithms.prompt.prompt_messages.hierarchical_reflective",
        "diting_optimizer.infra",
        "diting_optimizer.optimization_result",
    ]

    for module in modules:
        logger = logging.getLogger(module)
        logger.setLevel(level)

    # 根据配置设置第三方库的日志级别
    http_level = level if verbose_http else logging.WARNING

    # 设置 HTTP 相关库的日志级别
    http_modules = ["httpx", "httpcore", "urllib3.connectionpool"]

    for module in http_modules:
        logger = logging.getLogger(module)
        logger.setLevel(http_level)

    # 设置其他第三方库的日志级别为 WARNING
    third_party_modules = [
        "requests",
        "openai",
        "anthropic",
        "asyncio",
        "multipart",
        "urllib3",
    ]

    for module in third_party_modules:
        if module not in http_modules:  # 避免重复设置
            logger = logging.getLogger(module)
            logger.setLevel(logging.WARNING)

    # 设置 langchain 相关的日志级别
    langchain_modules = [
        "langchain",
        "langchain_community",
        "langchain_core",
        "langsmith",
    ]

    for module in langchain_modules:
        logger = logging.getLogger(module)
        logger.setLevel(logging.WARNING)

    # 记录初始化信息
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized with level: {logging.getLevelName(level)}")
    if verbose_http:
        logger.info("HTTP requests logging enabled")
    else:
        logger.info("HTTP requests logging disabled (set verbose_http=True to enable)")
