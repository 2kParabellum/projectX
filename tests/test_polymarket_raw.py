"""Raw Polymarket collection, against a fake Gamma. No network."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
import requests

from arbx.sources.polymarket.client import (
    collect_raw,
    event_is_esports,
    is_esports,
    market_type_counts,
    order_series,
    preview_rows,
    unique_series,
)
from arbx.storage.files import latest_raw, load_raw, save_raw


class FakeResponse:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)[:500]
        self.url = "https://gamma.test"

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} for {self.url}")


class FakeSession(requests.Session):
    """Routes /sports and /events. `pages` maps series_id to a list of pages."""

    def __init__(self, catalog, pages, clock=None):
        super().__init__()
        self.catalog = catalog
        self.pages = pages
        self.calls: list[tuple[str, dict]] = []
        self.clock = clock
        self._page_index: dict[str, int] = {}

    def get(self, url, params=None, timeout=None):
        params = dict(params or {})
        self.calls.append((url, params))
        if url.endswith("/sports"):
            return FakeResponse(self.catalog)
        series_id = str(params.get("series_id"))
        if series_id == "500":
            return FakeResponse({"error": "nope"}, status_code=500)
        batch = self.pages.get(series_id, [[]])
        index = self._page_index.get(series_id, 0)
        self._page_index[series_id] = index + 1
        if self.clock is not None:
            self.clock.t += 6
        if index >= len(batch):
            return FakeResponse([])
        return FakeResponse(batch[index])

    def close(self):
        return None


class Clock:
    def __init__(self, t: float = 0.0):
        self.t = t

    def __call__(self) -> float:
        return self.t


def _event(event_id, title, sport_code, esports=False, markets=1):
    tags = [{"id": "1", "slug": "sports"}]
    sport_tags = "1,100639"
    if esports:
        tags.append({"id": "64", "slug": "esports"})
        sport_tags = "1,64,100639"
    return {
        "id": str(event_id),
        "title": title,
        "slug": title.lower().replace(" ", "-"),
        "endDate": "2026-11-08T18:00:00Z",
        "tags": tags,
        "sport": {"sport": sport_code, "name": sport_code, "tags": sport_tags},
        "markets": [
            {
                "question": f"{title} moneyline",
                "sportsMarketType": "moneyline",
                "outcomes": '["Yes","No"]',
                "outcomePrices": '["0.4","0.6"]',
            }
            for _ in range(markets)
        ],
    }


CATALOG = [
    {"sport": "zzz", "series": "1", "tags": "1,100639", "name": "Zed"},
    {"sport": "nba", "series": "2", "tags": "1,745,100639", "name": "NBA"},
    {"sport": "cs2", "series": "3", "tags": "1,64,100780", "name": "CS2"},
    {"sport": "cs2-dup", "series": "3", "tags": "1,64,100780", "name": "CS2 again"},
    {"sport": "broken", "series": "500", "tags": "1", "name": "Broken"},
]

CONFIG = {
    "gamma_base_url": "https://gamma.test",
    "page_size": 2,
    "request_timeout_seconds": 5,
    "sleep_between_pages_seconds": 0,
    "end_date_slack_hours": 12,
    "esports_tag_id": "64",
    "max_pages_per_series": 5,
    "priority_codes": ["nba", "cs2"],
}


def test_esports_tag_and_unique_series():
    assert is_esports(CATALOG[2])
    assert not is_esports(CATALOG[1])
    rows = unique_series(CATALOG)
    assert [row["sport"] for row in rows] == ["zzz", "nba", "cs2", "broken"]
    ordered = order_series(rows, ["nba", "cs2"])
    assert [row["sport"] for row in ordered][:2] == ["nba", "cs2"]


def test_collects_sports_and_esports_and_skips_a_broken_series():
    pages = {
        "2": [[_event(10, "Celtics vs Knicks", "nba"), _event(11, "Lakers vs Heat", "nba")]],
        "3": [[_event(20, "NAVI vs Vitality", "cs2", esports=True)]],
        "1": [[]],
    }
    session = FakeSession(CATALOG, pages)
    snapshot = collect_raw(config=CONFIG, session=session, clock=Clock(), sleeper=lambda _s: None)

    assert snapshot.meta["stopped_reason"] == "complete"
    assert snapshot.meta["event_count"] == 3
    assert snapshot.meta["sports_events"] == 2
    assert snapshot.meta["esports_events"] == 1
    assert snapshot.meta["series_errors"]["broken"].startswith("HTTPError")
    assert snapshot.meta["series_fetched"] == ["nba", "cs2"]
    assert snapshot.payload["catalog"] == CATALOG
    titles = [row["title"] for row in preview_rows(snapshot)]
    assert titles == ["Celtics vs Knicks", "Lakers vs Heat", "NAVI vs Vitality"]
    assert preview_rows(snapshot)[2]["esports"] is True
    assert market_type_counts(snapshot) == [{"sportsMarketType": "moneyline", "n": 3}]

    event_calls = [params for url, params in session.calls if url.endswith("/events")]
    assert event_calls
    assert all("end_date_min" in params for params in event_calls)
    assert all(params["closed"] == "false" and params["active"] == "true" for params in event_calls)


def test_max_events_stops_before_the_next_series():
    pages = {
        "2": [[_event(10, "Celtics vs Knicks", "nba"), _event(11, "Lakers vs Heat", "nba")]],
        "3": [[_event(20, "NAVI vs Vitality", "cs2", esports=True)]],
    }
    session = FakeSession(CATALOG, pages)
    snapshot = collect_raw(
        max_events=1,
        config=CONFIG,
        session=session,
        clock=Clock(),
        sleeper=lambda _s: None,
    )
    assert snapshot.meta["stopped_reason"] == "max_events"
    assert [event["id"] for event in snapshot.payload["events"]] == ["10"]
    series_hit = {params.get("series_id") for url, params in session.calls if url.endswith("/events")}
    assert series_hit == {"2"}


def test_time_limit_stops_between_series():
    pages = {
        "2": [[_event(10, "Celtics vs Knicks", "nba")]],
        "3": [[_event(20, "NAVI vs Vitality", "cs2", esports=True)]],
        "1": [[_event(30, "Zed FC vs Zed", "zzz")]],
    }
    clock = Clock()
    session = FakeSession(CATALOG, pages, clock=clock)
    snapshot = collect_raw(
        max_seconds=10,
        config=CONFIG,
        session=session,
        clock=clock,
        sleeper=lambda _s: None,
    )
    assert snapshot.meta["stopped_reason"] == "time_limit"
    ids = {event["id"] for event in snapshot.payload["events"]}
    assert "10" in ids
    assert "30" not in ids


def test_duplicate_page_does_not_loop():
    same = [_event(10, "Celtics vs Knicks", "nba"), _event(11, "Lakers vs Heat", "nba")]
    pages = {"2": [same, same, same]}
    session = FakeSession(CATALOG, pages)
    snapshot = collect_raw(
        series_codes=["nba"],
        config=CONFIG,
        session=session,
        clock=Clock(),
        sleeper=lambda _s: None,
    )
    assert [event["id"] for event in snapshot.payload["events"]] == ["10", "11"]
    event_calls = [c for c in session.calls if c[0].endswith("/events")]
    assert len(event_calls) == 2


def test_series_code_filter_reports_unknown_codes():
    pages = {"3": [[_event(20, "NAVI vs Vitality", "cs2", esports=True)]]}
    session = FakeSession(CATALOG, pages)
    snapshot = collect_raw(
        series_codes=["cs2", "not-a-league"],
        config=CONFIG,
        session=session,
        clock=Clock(),
        sleeper=lambda _s: None,
    )
    assert snapshot.meta["unknown_codes"] == ["not-a-league"]
    assert snapshot.meta["event_count"] == 1
    assert event_is_esports(snapshot.payload["events"][0])


def test_raw_snapshot_roundtrip(tmp_path):
    pages = {"2": [[_event(10, "Celtics vs Knicks", "nba")]]}
    moment = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)
    snapshot = collect_raw(
        series_codes=["nba"],
        config=CONFIG,
        session=FakeSession(CATALOG, pages),
        now=moment,
        clock=Clock(),
        sleeper=lambda _s: None,
    )
    path = save_raw(snapshot, tmp_path)
    assert path.parent.name == "2026-11-08"
    loaded = load_raw(path)
    assert loaded.source == "polymarket"
    assert loaded.fetched_at == moment
    assert loaded.payload["events"][0]["title"] == "Celtics vs Knicks"
    assert latest_raw("polymarket", tmp_path) == path

    second = save_raw(snapshot, tmp_path)
    assert second != path
    assert second.exists()


def test_naive_timestamp_is_rejected(tmp_path):
    from arbx.models import RawSnapshot

    snapshot = RawSnapshot(
        source="polymarket",
        fetched_at=datetime(2026, 11, 8, 12, 0),
        payload={},
    )
    with pytest.raises(ValueError):
        save_raw(snapshot, tmp_path)
