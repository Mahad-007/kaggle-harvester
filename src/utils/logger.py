"""
Logging setup module.
Configures application-wide logging with file rotation and console output.
Follows Single Responsibility Principle: Only handles logging configuration.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys


def setup_logger(logging_config) -> logging.Logger:
    """
    Setup and configure application logger with file rotation and console output.

    Args:
        logging_config: LoggingConfig instance with logging settings

    Returns:
        Configured root logger instance
    """
    # Create logs directory if it doesn't exist
    log_file = Path(logging_config.file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Capture all levels, handlers will filter

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler with rotation
    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=logging_config.max_bytes,
        backupCount=logging_config.backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, logging_config.level.upper()))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, logging_config.console_level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.info("Logger initialized successfully")

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Module name (usually __name__)

    Returns:
        Logger instance for the module
    """
    return logging.getLogger(name)
