"""Loading of config/*.yaml and .env into typed settings objects.

Everything tunable lives in YAML; only secrets come from the environment.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"


@dataclass(frozen=True, slots=True)
class MatchingSettings:
    start_time_window_minutes: int
    score_auto_link: float
    score_review: float


@dataclass(frozen=True, slots=True)
class ArbitrageSettings:
    min_margin: Decimal
    max_quote_age_seconds: int
    fee_polymarket: Decimal
    fee_bookmaker: Decimal
    bankroll: Decimal


@dataclass(frozen=True, slots=True)
class Settings:
    enabled_sources: tuple[str, ...]
    sports: tuple[str, ...]
    matching: MatchingSettings
    arbitrage: ArbitrageSettings
    cycle_interval_seconds: int
    data_dir: Path
    log_level: str


@dataclass(frozen=True, slots=True)
class Secrets:
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    proxy_url: str | None


def load_settings(path: Path | None = None) -> Settings:
    """Read config/settings.yaml into a Settings object."""
    raise NotImplementedError


def load_source_config(name: str, path: Path | None = None) -> dict[str, Any]:
    """Read one source's block from config/sources.yaml."""
    raise NotImplementedError


def load_secrets() -> Secrets:
    """Read secrets from .env / the environment."""
    raise NotImplementedError
