"""Raw collection of Polymarket sports and esports.

The old fetcher walked every active Gamma event (`/events/keyset`) and
flattened it into a table. Two things about that do not fit this project:

- most of the firehose is not sport (politics, crypto, culture);
- the column layout was decided up front, and we do not yet know the layout
  we want.

Gamma already publishes a league catalog at ``/sports``. Each row is one
competition (NBA, EPL, CS2, ...) with a ``series`` id. Esports leagues are in
that same catalog: their ``tags`` contain id ``64``. Fetching events by
``series_id`` returns the actual matches, markets included, and nothing else.

``closed=false`` is not enough. Gamma leaves finished matches open, so every
request also sends ``end_date_min`` a few hours behind now. That keeps a game
that is in progress and drops last month's results.

Nothing in the response is reshaped. The snapshot payload is::

    {"catalog": <raw /sports JSON>, "events": [<raw event>, ...]}

Limits are for the notebook. ``max_seconds=10`` stops between requests and
returns whatever was collected. ``max_events`` caps the number of events.
Omit both for a full pass.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterable
from datetime import datetime, timedelta
from typing import Any

import requests

from arbx.config import load_source_config
from arbx.http.session import build_session, get_json
from arbx.models import RawSnapshot, utcnow

logger = logging.getLogger(__name__)

SOURCE_NAME = "polymarket"

#: Gamma rejects page sizes above this.
MAX_PAGE_SIZE = 100

_DEFAULTS: dict[str, Any] = {
    "gamma_base_url": "https://gamma-api.polymarket.com",
    "page_size": 100,
    "request_timeout_seconds": 30,
    "sleep_between_pages_seconds": 0.2,
    "end_date_slack_hours": 12,
    "esports_tag_id": "64",
    "max_pages_per_series": 50,
    "priority_codes": [
        "nba",
        "nhl",
        "nfl",
        "mlb",
        "epl",
        "ucl",
        "lal",
        "bun",
        "sea",
        "mls",
        "cs2",
        "dota2",
        "lol",
        "val",
        "ufc",
        "atp",
        "wta",
    ],
}


def polymarket_config(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Defaults, then config/sources.yaml, then explicit overrides."""
    config = dict(_DEFAULTS)
    if overrides is None:
        try:
            overrides = load_source_config(SOURCE_NAME)
        except (OSError, KeyError):
            overrides = {}
    config.update(overrides or {})
    return config


def is_esports(sport_row: dict[str, Any], esports_tag_id: str = "64") -> bool:
    """True when a /sports catalog row (or an event's nested sport) is esports."""
    tags = str(sport_row.get("tags") or "")
    return esports_tag_id in {part.strip() for part in tags.split(",") if part.strip()}


def event_is_esports(event: dict[str, Any], esports_tag_id: str = "64") -> bool:
    for tag in event.get("tags") or []:
        if not isinstance(tag, dict):
            continue
        if str(tag.get("id")) == esports_tag_id or tag.get("slug") == "esports":
            return True
    sport = event.get("sport")
    if isinstance(sport, dict) and is_esports(sport, esports_tag_id):
        return True
    return False


def unique_series(catalog: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per series id. The catalog repeats a series under two league codes."""
    chosen: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for row in catalog:
        series_id = str(row.get("series") or "").strip()
        if not series_id:
            continue
        if series_id not in chosen:
            chosen[series_id] = row
            order.append(series_id)
    return [chosen[series_id] for series_id in order]


def order_series(
    rows: list[dict[str, Any]],
    priority_codes: Iterable[str],
) -> list[dict[str, Any]]:
    """Priority leagues first, so a short timed run still sees live matches."""
    rank = {code: index for index, code in enumerate(priority_codes)}
    fallback = len(rank)

    def sort_key(row: dict[str, Any]) -> tuple[int, str]:
        code = str(row.get("sport") or "")
        return (rank.get(code, fallback), code)

    return sorted(rows, key=sort_key)


def _deadline(max_seconds: float | None, clock: Callable[[], float]) -> float | None:
    if max_seconds is None:
        return None
    return clock() + max_seconds


def _timed_out(deadline: float | None, clock: Callable[[], float]) -> bool:
    return deadline is not None and clock() >= deadline


def _pause(
    seconds: float,
    deadline: float | None,
    clock: Callable[[], float],
    sleeper: Callable[[float], None],
) -> bool:
    """Sleep between requests. Returns True when the time budget is already spent."""
    if _timed_out(deadline, clock):
        return True
    if seconds <= 0:
        return False
    if deadline is not None:
        seconds = min(seconds, max(0.0, deadline - clock()))
    if seconds > 0:
        sleeper(seconds)
    return _timed_out(deadline, clock)


def fetch_catalog(
    session: requests.Session,
    gamma_base_url: str,
    timeout: int,
) -> list[dict[str, Any]]:
    payload = get_json(session, f"{gamma_base_url}/sports", timeout=timeout)
    if not isinstance(payload, list):
        raise RuntimeError(f"/sports returned {type(payload).__name__}, expected a list")
    return payload


def fetch_series_events(
    session: requests.Session,
    gamma_base_url: str,
    series_id: str,
    *,
    end_date_min: str,
    page_size: int,
    timeout: int,
    max_pages: int,
    sleep_seconds: float,
    deadline: float | None,
    clock: Callable[[], float],
    sleeper: Callable[[float], None],
    seen_ids: set[str],
    max_new: int | None,
) -> tuple[list[dict[str, Any]], str | None]:
    """Paginate one series.

    Returns ``(events, stop_reason)``. ``stop_reason`` is ``None`` when the
    series was exhausted, or ``time_limit`` / ``max_events`` when a global
    limit ended the page loop early.
    """
    page_size = min(page_size, MAX_PAGE_SIZE)
    offset = 0
    seen_signatures: set[tuple[str, ...]] = set()
    collected: list[dict[str, Any]] = []

    for page in range(1, max_pages + 1):
        if _timed_out(deadline, clock):
            return collected, "time_limit"
        if max_new is not None and len(collected) >= max_new:
            return collected, "max_events"

        params = {
            "series_id": series_id,
            "active": "true",
            "closed": "false",
            "limit": page_size,
            "offset": offset,
            "end_date_min": end_date_min,
            "order": "id",
            "ascending": "true",
        }
        batch = get_json(
            session,
            f"{gamma_base_url}/events",
            params=params,
            timeout=timeout,
        )
        if not isinstance(batch, list):
            raise RuntimeError(
                f"series {series_id} page {page} returned {type(batch).__name__}, expected a list"
            )
        if not batch:
            return collected, None

        signature = tuple(str(event.get("id")) for event in batch[:5])
        if signature in seen_signatures:
            logger.info("series %s duplicate page at offset=%s, stop", series_id, offset)
            return collected, None
        seen_signatures.add(signature)

        new_on_page = 0
        for event in batch:
            event_id = str(event.get("id"))
            if event_id in seen_ids:
                continue
            seen_ids.add(event_id)
            collected.append(event)
            new_on_page += 1
            if max_new is not None and len(collected) >= max_new:
                return collected, "max_events"

        if new_on_page == 0:
            logger.info("series %s no new ids at offset=%s, stop", series_id, offset)
            return collected, None
        if len(batch) < page_size:
            return collected, None

        offset += page_size
        if _pause(sleep_seconds, deadline, clock, sleeper):
            return collected, "time_limit"

    raise RuntimeError(f"series {series_id} exceeded max_pages={max_pages}")


def collect_raw(
    max_seconds: float | None = None,
    max_events: int | None = None,
    series_codes: list[str] | None = None,
    *,
    config: dict[str, Any] | None = None,
    session: requests.Session | None = None,
    now: datetime | None = None,
    clock: Callable[[], float] | None = None,
    sleeper: Callable[[float], None] | None = None,
) -> RawSnapshot:
    """Collect raw sports and esports events.

    ``max_seconds`` stops the walk between HTTP calls and keeps everything
    already downloaded. ``max_events`` caps how many events are kept.
    ``series_codes`` restricts the walk to catalog codes such as ``["cs2"]``.
    With none of the limits set, every league series is fetched.
    """
    config = polymarket_config(config)
    clock = clock or time.monotonic
    sleeper = sleeper or time.sleep
    started = clock()
    deadline = _deadline(max_seconds, clock)
    moment = now or utcnow()
    slack = timedelta(hours=float(config["end_date_slack_hours"]))
    end_date_min = (moment - slack).strftime("%Y-%m-%dT%H:%M:%SZ")
    esports_tag_id = str(config["esports_tag_id"])
    gamma_base_url = str(config["gamma_base_url"]).rstrip("/")
    timeout = int(config["request_timeout_seconds"])
    page_size = int(config["page_size"])
    sleep_seconds = float(config["sleep_between_pages_seconds"])
    max_pages = int(config["max_pages_per_series"])

    own_session = session is None
    session = session or build_session()
    try:
        return _collect_from_catalog(
            session,
            gamma_base_url=gamma_base_url,
            timeout=timeout,
            page_size=page_size,
            sleep_seconds=sleep_seconds,
            max_pages=max_pages,
            end_date_min=end_date_min,
            esports_tag_id=esports_tag_id,
            moment=moment,
            max_seconds=max_seconds,
            max_events=max_events,
            series_codes=series_codes,
            priority_codes=[str(code) for code in config["priority_codes"]],
            started=started,
            deadline=deadline,
            clock=clock,
            sleeper=sleeper,
        )
    finally:
        if own_session:
            session.close()


def _collect_from_catalog(
    session: requests.Session,
    *,
    gamma_base_url: str,
    timeout: int,
    page_size: int,
    sleep_seconds: float,
    max_pages: int,
    end_date_min: str,
    esports_tag_id: str,
    moment: datetime,
    max_seconds: float | None,
    max_events: int | None,
    series_codes: list[str] | None,
    priority_codes: list[str],
    started: float,
    deadline: float | None,
    clock: Callable[[], float],
    sleeper: Callable[[float], None],
) -> RawSnapshot:
    catalog = fetch_catalog(session, gamma_base_url, timeout)
    series_rows = unique_series(catalog)
    unknown_codes: list[str] = []
    if series_codes is not None:
        wanted = {code.strip().lower() for code in series_codes}
        known = {str(row.get("sport") or "").lower() for row in series_rows}
        unknown_codes = sorted(wanted - known)
        series_rows = [row for row in series_rows if str(row.get("sport") or "").lower() in wanted]
    series_rows = order_series(series_rows, priority_codes)

    events: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    series_fetched: list[str] = []
    series_empty: list[str] = []
    errors: dict[str, str] = {}
    stopped = "complete"

    logger.info(
        "polymarket collect start | series=%s | end_date_min=%s | max_seconds=%s | max_events=%s",
        len(series_rows),
        end_date_min,
        max_seconds,
        max_events,
    )

    for index, row in enumerate(series_rows, start=1):
        if _timed_out(deadline, clock):
            stopped = "time_limit"
            break
        if max_events is not None and len(events) >= max_events:
            stopped = "max_events"
            break

        code = str(row.get("sport") or "")
        series_id = str(row.get("series"))
        remaining = None if max_events is None else max_events - len(events)
        try:
            batch, reason = fetch_series_events(
                session,
                gamma_base_url,
                series_id,
                end_date_min=end_date_min,
                page_size=page_size,
                timeout=timeout,
                max_pages=max_pages,
                sleep_seconds=sleep_seconds,
                deadline=deadline,
                clock=clock,
                sleeper=sleeper,
                seen_ids=seen_ids,
                max_new=remaining,
            )
        except (requests.RequestException, RuntimeError) as exc:
            errors[code] = f"{type(exc).__name__}: {exc}"
            logger.warning("series %s failed: %s", code, errors[code])
            continue

        events.extend(batch)
        if batch:
            series_fetched.append(code)
        else:
            series_empty.append(code)
        logger.info(
            "[%s/%s] %s +%s total=%s elapsed=%.1fs",
            index,
            len(series_rows),
            code,
            len(batch),
            len(events),
            clock() - started,
        )
        if reason == "time_limit":
            stopped = "time_limit"
            break
        if reason == "max_events":
            stopped = "max_events"
            break
        if _pause(sleep_seconds, deadline, clock, sleeper):
            stopped = "time_limit"
            break

    if max_events is not None and len(events) > max_events:
        events = events[:max_events]
        stopped = "max_events"

    esports_count = sum(1 for event in events if event_is_esports(event, esports_tag_id))
    meta = {
        "stopped_reason": stopped,
        "elapsed_seconds": round(clock() - started, 3),
        "end_date_min": end_date_min,
        "series_total": len(series_rows),
        "series_fetched": series_fetched,
        "series_empty": len(series_empty),
        "series_errors": errors,
        "unknown_codes": unknown_codes,
        "event_count": len(events),
        "market_count": sum(len(event.get("markets") or []) for event in events),
        "sports_events": len(events) - esports_count,
        "esports_events": esports_count,
    }
    logger.info(
        "polymarket collect done | events=%s markets=%s sports=%s esports=%s reason=%s elapsed=%.1fs",
        meta["event_count"],
        meta["market_count"],
        meta["sports_events"],
        meta["esports_events"],
        stopped,
        meta["elapsed_seconds"],
    )
    return RawSnapshot(
        source=SOURCE_NAME,
        fetched_at=moment,
        payload={"catalog": catalog, "events": events},
        meta=meta,
    )


def preview_rows(snapshot: RawSnapshot) -> list[dict[str, Any]]:
    """Small flat view of a raw snapshot, for looking at what was collected.

    This is not the canonical schema. It only surfaces fields that are already
    on the raw event so a notebook can show them without deciding a layout.
    """
    events = (snapshot.payload or {}).get("events") or []
    rows: list[dict[str, Any]] = []
    for event in events:
        tags = event.get("tags") or []
        sport = event.get("sport") if isinstance(event.get("sport"), dict) else {}
        rows.append(
            {
                "id": event.get("id"),
                "title": event.get("title"),
                "sport": sport.get("sport"),
                "sport_name": sport.get("name"),
                "esports": event_is_esports(event),
                "end": event.get("endDate"),
                "n_markets": len(event.get("markets") or []),
                "tags": ", ".join(
                    str(tag.get("slug") or "")
                    for tag in tags
                    if isinstance(tag, dict) and tag.get("slug")
                ),
            }
        )
    return rows


def preview_markets(event: dict[str, Any], limit: int = 20) -> list[dict[str, Any]]:
    """First markets of one raw event, fields Gamma already provides."""
    rows: list[dict[str, Any]] = []
    for market in (event.get("markets") or [])[:limit]:
        rows.append(
            {
                "question": market.get("question"),
                "sportsMarketType": market.get("sportsMarketType"),
                "line": market.get("line"),
                "outcomes": market.get("outcomes"),
                "outcomePrices": market.get("outcomePrices"),
                "bestBid": market.get("bestBid"),
                "bestAsk": market.get("bestAsk"),
                "gameStartTime": market.get("gameStartTime"),
            }
        )
    return rows


def market_type_counts(snapshot: RawSnapshot) -> list[dict[str, Any]]:
    """How often each raw ``sportsMarketType`` appears. ``None`` stays ``None``."""
    counts: dict[Any, int] = {}
    for event in (snapshot.payload or {}).get("events") or []:
        for market in event.get("markets") or []:
            key = market.get("sportsMarketType")
            counts[key] = counts.get(key, 0) + 1
    return [
        {"sportsMarketType": key, "n": count}
        for key, count in sorted(counts.items(), key=lambda item: (-item[1], str(item[0])))
    ]
