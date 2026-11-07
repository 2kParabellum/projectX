"""Single place where logging is configured, so modules only call getLogger."""

from __future__ import annotations

import logging


def setup_logging(level: str = "INFO") -> None:
    """Configure root logging once, with rich formatting when available."""
    raise NotImplementedError


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
