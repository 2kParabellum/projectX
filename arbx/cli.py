"""Command line entry point.

    arbx fetch polymarket   save one raw snapshot from a source
    arbx parse polymarket   parse the newest saved snapshot, print the quotes
    arbx match              match events from the newest snapshots
    arbx scan               full cycle offline, print opportunities, no alerts
    arbx run                full cycle on a loop, with alerts
    arbx review             work through the pending-link queue
"""

from __future__ import annotations

import typer

app = typer.Typer(add_completion=False, help="Sports arbitrage monitor.")


@app.command()
def fetch(source: str) -> None:
    """Fetch and store one raw snapshot."""
    raise NotImplementedError


@app.command()
def parse(source: str) -> None:
    """Parse the newest stored snapshot and print the resulting quotes."""
    raise NotImplementedError


@app.command()
def match() -> None:
    """Match events across the newest stored snapshots."""
    raise NotImplementedError


@app.command()
def scan() -> None:
    """Run the full pipeline offline and print any opportunities found."""
    raise NotImplementedError


@app.command()
def run() -> None:
    """Run the pipeline on a schedule, sending alerts."""
    raise NotImplementedError


@app.command()
def review() -> None:
    """Confirm or reject queued candidate event links."""
    raise NotImplementedError


if __name__ == "__main__":
    app()
