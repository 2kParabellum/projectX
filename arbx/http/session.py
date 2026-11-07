"""Shared HTTP session: retries, backoff, rate limiting, optional proxy.

Adapted from fetching_old/fetching/gamma.py::build_retry_session.
"""

from __future__ import annotations

import requests


def build_session(
    total_retries: int = 5,
    backoff_factor: float = 1.0,
    proxy_url: str | None = None,
    user_agent: str | None = None,
) -> requests.Session:
    """Session with urllib3 retries on 429/5xx and a connection pool."""
    raise NotImplementedError


def get_json(
    session: requests.Session,
    url: str,
    params: dict | None = None,
    timeout: int = 30,
) -> object:
    """GET returning parsed JSON, raising on HTTP errors with the body logged."""
    raise NotImplementedError
