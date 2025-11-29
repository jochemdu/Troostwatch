"""Logging utilities for Troostwatch.

This module provides centralised logging configuration and helpers for
structured, contextual logging throughout the project.
"""

from __future__ import annotations

import logging
import sys
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator


# ---------------------------------------------------------------------------
# Context variables for structured logging
# ---------------------------------------------------------------------------

_log_context: ContextVar[dict[str, Any]] = ContextVar(
    "log_context", default={})


class ContextualFormatter(logging.Formatter):
    """Formatter that appends context fields to log messages."""

    def format(self, record: logging.LogRecord) -> str:
        ctx = _log_context.get()
        if ctx:
            ctx_str = " ".join(f"{k}={v}" for k, v in ctx.items())
            record.msg = f"{record.msg} [{ctx_str}]"
        return super().format(record)


@contextmanager
def log_context(**fields: Any) -> Iterator[None]:
    """Temporarily add context fields to all log messages.

    Usage::

        with log_context(auction_code="ABC123", sync_run_id=42):
            logger.info("Starting sync")  # message includes context

    Fields are merged with any existing context and restored on exit.
    """
    current = _log_context.get()
    merged = {**current, **fields}
    token = _log_context.set(merged)
    try:
        yield
    finally:
        _log_context.reset(token)


# Alias for backwards compatibility and discoverability
LogContext = log_context


# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

_configured = False


def configure_logging(
    level: int = logging.INFO,
    third_party_level: int = logging.WARNING,
    use_json: bool = False,
) -> None:
    """Configure application-wide logging.

    Call this once at startup (CLI main, FastAPI lifespan, etc.) to set up
    consistent logging across the application.

    Args:
        level: Log level for application loggers (default INFO).
        third_party_level: Log level for third-party libraries (default WARNING).
        use_json: If True, output JSON lines instead of plain text (future use).
    """
    global _configured
    if _configured:
        return
    _configured = True

    # Root logger configuration
    root = logging.getLogger()
    root.setLevel(level)

    # Remove any existing handlers to avoid duplicates
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    # Stream handler with contextual formatter
    handler = logging.StreamHandler(sys.stderr)
    if use_json:
        # Placeholder for JSON formatter; for now use plain text
        formatter = ContextualFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    else:
        formatter = ContextualFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    handler.setFormatter(formatter)
    root.addHandler(handler)

    # Quieten noisy third-party loggers
    for name in ("httpx", "httpcore", "urllib3", "asyncio", "uvicorn.access"):
        logging.getLogger(name).setLevel(third_party_level)


def get_logger(name: str) -> logging.Logger:
    """Return a logger for the given name.

    If configure_logging() has not been called, a basic fallback configuration
    is applied to ensure the logger is usable.

    Args:
        name: Name of the logger (typically __name__).

    Returns:
        A logging.Logger instance.
    """
    logger = logging.getLogger(name)
    # Fallback if configure_logging was not called
    if not _configured and not logger.handlers and not logging.getLogger().handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------


def log_exception(
    logger: logging.Logger,
    message: str,
    exc: BaseException,
    **context: Any,
) -> None:
    """Log an exception with context fields.

    Args:
        logger: Logger instance.
        message: Human-readable message describing the error.
        exc: The exception that was raised.
        **context: Additional context fields to include.
    """
    with log_context(**context):
        logger.exception(f"{message}: {exc}")
