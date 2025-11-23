"""Logging utilities for Troostwatch.

This module provides placeholders for setting up and using loggers
consistently throughout the project.
"""

import logging


def get_logger(name: str) -> logging.Logger:
    """Return a logger configured with a default format.

    Args:
        name: Name of the logger.

    Returns:
        A logging.Logger instance.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger