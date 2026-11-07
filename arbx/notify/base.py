"""Notifier interface, so Telegram is one option rather than the only one."""

from __future__ import annotations

from abc import ABC, abstractmethod

from arbx.models import ArbOpportunity


class Notifier(ABC):
    @abstractmethod
    def send(self, opportunity: ArbOpportunity) -> None: ...


class ConsoleNotifier(Notifier):
    """Prints instead of sending. Default while developing."""

    def send(self, opportunity: ArbOpportunity) -> None:
        raise NotImplementedError
