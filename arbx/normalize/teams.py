"""Canonical team and league names.

A name is resolved in three steps, cheapest first:
  1. exact hit in the alias dictionary (curated YAML, then learned entries);
  2. deterministic cleanup from normalize.text;
  3. nothing - the cleaned string is returned and matching falls back to fuzzy.
"""

from __future__ import annotations


def canonical_team(raw: str, aliases: dict[str, str]) -> str:
    raise NotImplementedError


def canonical_league(raw: str, aliases: dict[str, str]) -> str:
    raise NotImplementedError
