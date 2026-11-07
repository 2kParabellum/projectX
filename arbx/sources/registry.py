"""Source name -> adapter class. The only place that knows all sources exist."""

from __future__ import annotations

from arbx.sources.base import BaseSource


def get_source_class(name: str) -> type[BaseSource]:
    """Look up an adapter class by its config name."""
    raise NotImplementedError


def build_source(name: str) -> BaseSource:
    """Instantiate an adapter with its block from config/sources.yaml."""
    raise NotImplementedError


def available_sources() -> list[str]:
    raise NotImplementedError
