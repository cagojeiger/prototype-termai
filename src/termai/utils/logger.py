"""
Logging configuration for Terminal AI Assistant.
"""

import logging
import sys

from termai.config import get_settings


def setup_logger(name: str, level: str | None = None) -> logging.Logger:
    """Set up a logger with consistent formatting.

    Args:
        name: Logger name (usually __name__)
        level: Log level override (defaults to settings)

    Returns:
        Configured logger instance
    """
    settings = get_settings()
    log_level = level or settings.app_log_level

    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    return logger


# Root logger for the package
logger = setup_logger("termai")
