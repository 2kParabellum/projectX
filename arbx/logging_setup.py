"""Single place where logging is configured, so modules only call getLogger."""

from __future__ import annotations

import logging


def setup_logging(level: str = "INFO") -> None:
    """Configure root logging once. Safe to call again: handlers are replaced."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s | %(message)s", "%H:%M:%S")
    )
    root.addHandler(handler)
    root.setLevel(level.upper())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
