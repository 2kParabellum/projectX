"""Telegram delivery via the Bot API."""

from __future__ import annotations

from arbx.models import ArbOpportunity
from arbx.notify.base import Notifier


class TelegramNotifier(Notifier):
    def __init__(self, bot_token: str, chat_id: str) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send(self, opportunity: ArbOpportunity) -> None:
        raise NotImplementedError

    def send_text(self, text: str) -> None:
        raise NotImplementedError
