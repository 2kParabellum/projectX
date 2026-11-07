from __future__ import annotations

import time
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import GAMMA_BASE_URL
from .parsing import _event_id_as_str, _page_signature


def build_retry_session(
    total_retries: int = 5,
    backoff_factor: float = 1.0,
) -> requests.Session:
    s = requests.Session()

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
    s.mount("https://", adapter)
    s.mount("http://", adapter)

    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Python requests market-fetcher",
        "Accept": "application/json",
        "Connection": "keep-alive",
    })
    return s


def fetch_events_page(
    session: requests.Session,
    offset: int,
    limit: int,
    timeout: int,
) -> List[Dict[str, Any]]:
    params = {
        "active": "true",
        "closed": "false",
        "limit": limit,
        "offset": offset,
        "order": "id",
        "ascending": "true",
    }
    resp = session.get(f"{GAMMA_BASE_URL}/events", params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def fetch_events_page_with_retry(
    session: requests.Session,
    offset: int,
    limit: int,
    timeout: int,
) -> List[Dict[str, Any]]:
    last_err = None
    for attempt in range(1, 6):
        try:
            batch = fetch_events_page(session, offset, limit, timeout)
            return batch
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.ChunkedEncodingError,
            requests.exceptions.RequestException,
        ) as e:
            last_err = e
            wait = min(2 ** attempt, 20)
            print(
                f"request failed | offset={offset} | attempt={attempt}/5 | wait={wait}s | err={type(e).__name__}"
            )
            time.sleep(wait)
    raise last_err


def fetch_events_keyset_page(
    session: requests.Session,
    limit: int,
    timeout: int,
    next_cursor: Optional[str] = None,
) -> Dict[str, Any]:
    params = {
        "active": "true",
        "closed": "false",
        "limit": limit,
        "order": "id",
        "ascending": "true",
    }

    if next_cursor:
        params["after_cursor"] = next_cursor

    resp = session.get(
        f"{GAMMA_BASE_URL}/events/keyset",
        params=params,
        timeout=timeout,
    )

    if resp.status_code >= 400:
        print("Gamma keyset error")
        print("status:", resp.status_code)
        print("url:", resp.url)
        print("text:", resp.text[:1000])

    resp.raise_for_status()
    return resp.json()


def iter_active_events_keyset(
    session: requests.Session,
    limit: int = 100,
    timeout: int = 30,
    max_pages: int = 10000,
    max_events: Optional[int] = None,
    sleep_seconds: float = 0.2,
    rows_for_logging: Optional[List[Any]] = None,
) -> Iterator[Dict[str, Any]]:
    page = 0
    yielded_count = 0
    next_cursor = None

    seen_event_ids: Set[str] = set()
    seen_cursors: Set[str] = set()

    while True:
        page += 1

        if page > max_pages:
            raise RuntimeError(
                f"Exceeded max_pages={max_pages}. Likely keyset pagination not progressing."
            )

        if next_cursor:
            if next_cursor in seen_cursors:
                print("duplicate next_cursor, stop")
                break
            seen_cursors.add(next_cursor)

        data = fetch_events_keyset_page(
            session=session,
            limit=limit,
            timeout=timeout,
            next_cursor=next_cursor,
        )

        batch = data.get("events") or []
        next_cursor = data.get("next_cursor")

        if not batch:
            print("empty keyset batch, stop")
            break

        new_ids_in_page = 0

        for ev in batch:
            if max_events is not None and yielded_count >= max_events:
                break

            ev_id = _event_id_as_str(ev)

            if ev_id is not None:
                if ev_id in seen_event_ids:
                    continue

                seen_event_ids.add(ev_id)
                new_ids_in_page += 1

            yield ev
            yielded_count += 1

        row_n = len(rows_for_logging) if rows_for_logging is not None else None
        rows_part = f" | rows={row_n}" if row_n is not None else ""

        print(
            f"keyset_page={page} | batch={len(batch)} | "
            f"yielded={yielded_count} | new_ids={new_ids_in_page} | "
            f"next_cursor={bool(next_cursor)}{rows_part}"
        )

        if max_events is not None and yielded_count >= max_events:
            print(f"max_events={max_events} reached, stop")
            break

        if not next_cursor:
            print("no next_cursor, stop")
            break

        if new_ids_in_page == 0:
            print("no new ids in keyset page, stop")
            break

        time.sleep(sleep_seconds)


def iter_active_events(
    session: requests.Session,
    limit: int = 100,
    timeout: int = 30,
    max_pages: int = 2000,
    max_events: Optional[int] = None,
    sleep_seconds: float = 0.2,
    rows_for_logging: Optional[List[Any]] = None,
) -> Iterator[Dict[str, Any]]:
    """Yield active Gamma events with offset pagination.

    ``limit`` is the API page size (capped at 100). ``max_events``, when set,
    stops after that many events have been yielded (deduplicated by event id).
    """
    page_size = min(limit,100)
    offset = 0
    page = 0
    yielded_count = 0

    seen_event_ids: Set[str] = set()
    seen_page_sigs: Set[Tuple[str, ...]] = set()

    while True:
        page += 1
        if page > max_pages:
            raise RuntimeError(
                f"Exceeded max_pages={max_pages}. Likely pagination not progressing."
            )

        batch = fetch_events_page_with_retry(session, offset, page_size, timeout)

        if not batch:
            print(f"empty batch at offset={offset}, stop")
            break

        sig = _page_signature(batch, n=min(5, len(batch)))
        if sig in seen_page_sigs:
            print(f"duplicate page signature at offset={offset}, stop")
            break
        seen_page_sigs.add(sig)

        new_ids_in_page = 0
        stop_after_page = False

        for ev in batch:
            if max_events is not None and yielded_count >= max_events:
                stop_after_page = True
                break

            ev_id = _event_id_as_str(ev)
            if ev_id is not None:
                if ev_id in seen_event_ids:
                    continue
                seen_event_ids.add(ev_id)
                new_ids_in_page += 1

            yield ev
            yielded_count += 1

        row_n = len(rows_for_logging) if rows_for_logging is not None else None
        rows_part = f" | rows={row_n}" if row_n is not None else ""
        print(
            f"page={page} | offset={offset} | page_size={page_size} | batch={len(batch)}"
            f" | yielded={yielded_count} | new_ids_in_page={new_ids_in_page}{rows_part}"
        )

        if stop_after_page or (max_events is not None and yielded_count >= max_events):
            print(f"max_events={max_events} reached, stop")
            break

        if new_ids_in_page == 0:
            print("no new ids in page, stop")
            break

        offset += page_size

        if len(batch) < page_size:
            print("last page reached, stop")
            break

        if offset > 100000:
            print("offset safety stop")
            break

        time.sleep(sleep_seconds)
