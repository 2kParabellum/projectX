"""Shared HTTP session: retries, backoff, optional proxy.

The retry policy is the one that already proved itself in
fetching_old/fetching/gamma.py: urllib3 retries on 429 and 5xx, plus a
connection pool so pagination does not reconnect every page.
"""

from __future__ import annotations

import logging
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) arbx/0.1"
)


def build_session(
    total_retries: int = 5,
    backoff_factor: float = 1.0,
    proxy_url: str | None = None,
    user_agent: str | None = None,
) -> requests.Session:
    """Session with urllib3 retries on 429/5xx and a connection pool."""
    session = requests.Session()

    retry = Retry(
        total=total_retries,
        connect=total_retries,
        read=total_retries,
        status=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(
        {
            "User-Agent": user_agent or _DEFAULT_USER_AGENT,
            "Accept": "application/json",
            "Connection": "keep-alive",
        }
    )
    if proxy_url:
        session.proxies.update({"http": proxy_url, "https": proxy_url})
    return session


def get_json(
    session: requests.Session,
    url: str,
    params: dict[str, Any] | None = None,
    timeout: int = 30,
) -> Any:
    """GET returning parsed JSON. HTTP errors include the response body in the log."""
    response = session.get(url, params=params, timeout=timeout)
    if response.status_code >= 400:
        logger.warning(
            "GET %s -> %s | params=%s | body=%s",
            url,
            response.status_code,
            params,
            response.text[:500],
        )
        response.raise_for_status()
    return response.json()
