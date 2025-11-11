"""
Optimizer module for prompt optimization.
"""

# Initialize logging early to ensure all modules get proper logging
import logging

# Set up basic logging configuration immediately
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,  # Force reconfiguration even if already configured
)

# Import and apply detailed logging configuration
try:
    from .logging_config import setup_logging

    # Initialize logging when the module is imported
    # Use conservative defaults: INFO level, no HTTP logs
    setup_logging(level=logging.INFO, verbose_http=False)
except ImportError:
    # If logging_config is not available, use basic configuration
    logger = logging.getLogger(__name__)
    logger.info("Using basic logging configuration")
