"""The alias dictionary: curated YAML plus entries learned from confirmed links.

This dictionary is the asset that makes matching improve over time. Every
manually confirmed link should end up here so the same pair resolves instantly
on the next run.
"""

from __future__ import annotations

from pathlib import Path


def load_aliases(yaml_path: Path | None = None) -> dict[str, str]:
    """Flatten config/aliases.yaml plus learned rows into alias -> canonical."""
    raise NotImplementedError


def learn_alias(alias: str, canonical: str, kind: str = "team") -> None:
    """Persist a newly confirmed alias to storage."""
    raise NotImplementedError
