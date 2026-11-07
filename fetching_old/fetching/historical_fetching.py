from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set

import pandas as pd
import requests

from .config import GAMMA_BASE_URL
from .gamma import build_retry_session
from .parsing import (
    _event_id_as_str,
    _to_float,
    _token_ids_from_market,
    get_tag_labels,
)

_HISTORICAL_COLUMNS = [
    "event_slug",
    "event_id",
    "event_creationdate",
    "market_slug",
    "market_id",
    "market_decription",  # intentional spelling per export schema
    "market_startdate",
    "market_creationdate",
    "market_enddate",
    "market_active",
    "market_closed",
    "market_volume",
    "yes_price",
    "no_price",
    "yes_token",
    "no_token",
    "lasttradeprice",
    "tags",
]

_DATE_COLUMNS = [
    "event_creationdate",
    "market_startdate",
    "market_creationdate",
    "market_enddate",
]

_NUMERIC_COLUMNS = [
    "market_volume",
    "yes_price",
    "no_price",
    "lasttradeprice",
]


def _safe_json_list(x: Any) -> List[Any]:
    if isinstance(x, list):
        return x
    if isinstance(x, str):
        try:
            parsed = json.loads(x)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


def fetch_events_keyset_page_historical(
    session: requests.Session,
    limit: int = 100,
    timeout: int = 30,
    next_cursor: Optional[str] = None,
    active: Optional[bool] = None,
    closed: Optional[bool] = None,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "limit": limit,
        "order": "id",
        "ascending": "true",
    }

    if active is not None:
        params["active"] = str(active).lower()
    if closed is not None:
        params["closed"] = str(closed).lower()
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


def iter_events_keyset_historical(
    session: requests.Session,
    limit: int = 100,
    timeout: int = 30,
    max_pages: int = 100000,
    max_events: Optional[int] = None,
    sleep_seconds: float = 0.1,
    active: Optional[bool] = None,
    closed: Optional[bool] = None,
    rows_for_logging: Optional[List[Any]] = None,
) -> Iterator[Dict[str, Any]]:
    page = 0
    yielded_count = 0
    next_cursor: Optional[str] = None

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

        data = fetch_events_keyset_page_historical(
            session=session,
            limit=limit,
            timeout=timeout,
            next_cursor=next_cursor,
            active=active,
            closed=closed,
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
            f"historical_keyset_page={page} | batch={len(batch)} | "
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


def _extract_yes_no_prices(market: Dict[str, Any]) -> tuple[Optional[float], Optional[float]]:
    outcomes = _safe_json_list(market.get("outcomes"))
    prices = _safe_json_list(market.get("outcomePrices"))

    yes_price: Optional[float] = None
    no_price: Optional[float] = None

    if not outcomes or not prices or len(outcomes) != len(prices):
        return yes_price, no_price

    for outcome, price in zip(outcomes, prices):
        label = str(outcome).strip().lower()
        px = _to_float(price)
        if px is None:
            continue
        if label == "yes":
            yes_price = px
        elif label == "no":
            no_price = px

    return yes_price, no_price


def _extract_market_row(event: Dict[str, Any], market: Dict[str, Any]) -> Dict[str, Any]:
    yes_price, no_price = _extract_yes_no_prices(market)
    yes_token, no_token = _token_ids_from_market(market)
    tag_labels = get_tag_labels(event)

    return {
        "event_slug": event.get("slug"),
        "event_id": str(event.get("id")) if event.get("id") is not None else None,
        "event_creationdate": event.get("creationDate") or event.get("createdAt"),
        "market_slug": market.get("slug"),
        "market_id": str(market.get("id")) if market.get("id") is not None else None,
        "market_decription": market.get("description"),
        "market_startdate": market.get("startDate"),
        "market_creationdate": market.get("createdAt") or market.get("creationDate"),
        "market_enddate": market.get("endDate"),
        "market_active": market.get("active"),
        "market_closed": market.get("closed"),
        "market_volume": _to_float(
            market.get("volume") or market.get("volumeNum") or market.get("volumeClob")
        ),
        "yes_price": yes_price,
        "no_price": no_price,
        "yes_token": yes_token,
        "no_token": no_token,
        "lasttradeprice": _to_float(market.get("lastTradePrice")),
        "tags": ",".join(tag_labels) if tag_labels else None,
    }


def _event_only_row(event: Dict[str, Any]) -> Dict[str, Any]:
    tag_labels = get_tag_labels(event)
    return {
        "event_slug": event.get("slug"),
        "event_id": str(event.get("id")) if event.get("id") is not None else None,
        "event_creationdate": event.get("creationDate") or event.get("createdAt"),
        "market_slug": None,
        "market_id": None,
        "market_decription": None,
        "market_startdate": None,
        "market_creationdate": None,
        "market_enddate": None,
        "market_active": None,
        "market_closed": None,
        "market_volume": None,
        "yes_price": None,
        "no_price": None,
        "yes_token": None,
        "no_token": None,
        "lasttradeprice": None,
        "tags": ",".join(tag_labels) if tag_labels else None,
    }


def normalize_historical_event_to_rows(event: Dict[str, Any]) -> List[Dict[str, Any]]:
    markets = event.get("markets") or []

    if not markets:
        return [_event_only_row(event)]

    return [_extract_market_row(event, market) for market in markets]


def historical_rows_to_dataframe(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)

    for col in _HISTORICAL_COLUMNS:
        if col not in df.columns:
            df[col] = None

    df = df[_HISTORICAL_COLUMNS]

    for col in _DATE_COLUMNS:
        df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)

    for col in _NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def fetch_historical_markets_df(
    limit: Optional[int] = None,
    timeout: int = 30,
    max_pages: int = 100000,
    session: Optional[requests.Session] = None,
    sleep_seconds: float = 0.1,
    active: Optional[bool] = None,
    closed: Optional[bool] = None,
) -> pd.DataFrame:
    s = session or build_retry_session()
    rows: List[Dict[str, Any]] = []

    for ev in iter_events_keyset_historical(
        s,
        limit=100,
        timeout=timeout,
        max_pages=max_pages,
        max_events=limit,
        sleep_seconds=sleep_seconds,
        active=active,
        closed=closed,
        rows_for_logging=rows,
    ):
        rows.extend(normalize_historical_event_to_rows(ev))

    return historical_rows_to_dataframe(rows)


def fetch_and_save_historical_markets_csv(
    output_path: str = "data/historical_polymarket_markets.csv",
    limit: Optional[int] = None,
    timeout: int = 30,
    max_pages: int = 100000,
    sleep_seconds: float = 0.1,
    active: Optional[bool] = None,
    closed: Optional[bool] = None,
) -> pd.DataFrame:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    df = fetch_historical_markets_df(
        limit=limit,
        timeout=timeout,
        max_pages=max_pages,
        sleep_seconds=sleep_seconds,
        active=active,
        closed=closed,
    )

    df.to_csv(output_path, index=False)
    print(f"saved: {output_path} | shape={df.shape}")
    return df
