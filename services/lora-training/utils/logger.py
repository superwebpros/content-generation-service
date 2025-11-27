"""
Logging utilities for LoRA extraction pipeline.

Provides consistent logging across all modules.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Setup a logger with consistent formatting.

    Args:
        name: Logger name (usually __name__)
        level: Logging level (default: INFO)
        log_file: Optional file to write logs to
        format_string: Custom format string (optional)

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Default format
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    formatter = logging.Formatter(format_string)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with default settings.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return setup_logger(name)


class ProgressLogger:
    """Simple progress logger for long-running operations."""

    def __init__(self, logger: logging.Logger, total: int, prefix: str = "Progress"):
        self.logger = logger
        self.total = total
        self.prefix = prefix
        self.current = 0

    def update(self, increment: int = 1, message: str = ""):
        """Update progress."""
        self.current += increment
        percentage = (self.current / self.total) * 100
        log_msg = f"{self.prefix}: {self.current}/{self.total} ({percentage:.1f}%)"
        if message:
            log_msg += f" - {message}"
        self.logger.info(log_msg)

    def complete(self, message: str = "Complete"):
        """Mark as complete."""
        self.logger.info(f"{self.prefix}: {message}")
