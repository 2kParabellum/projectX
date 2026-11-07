"""Message text for an opportunity.

The message has to carry enough for a human to act in under a minute: the
fixture, the market, which price to take at which source, the stake split,
the margin, and how old the quotes were when it was found.
"""

from __future__ import annotations

from arbx.models import ArbOpportunity


def format_opportunity(opportunity: ArbOpportunity) -> str:
    raise NotImplementedError
