"""Telegram Bot API notifier."""

from __future__ import annotations

import httpx
import structlog

from ml_in_sports.settings import get_settings

logger = structlog.get_logger(__name__)

_MAX_TELEGRAM_CHARS = 4096


class TelegramNotifier:
    """Send Markdown messages via the Telegram Bot API.

    Environment variables:
        ML_IN_SPORTS_TELEGRAM_BOT_TOKEN: Telegram bot token.
        ML_IN_SPORTS_TELEGRAM_CHAT_ID: Target chat ID.
    """

    def __init__(self) -> None:
        """Initialize notifier from application settings."""
        settings = get_settings()
        self._token = settings.telegram_bot_token
        self._chat_id = settings.telegram_chat_id
        if not self._token or not self._chat_id:
            raise ValueError(
                "ML_IN_SPORTS_TELEGRAM_BOT_TOKEN and "
                "ML_IN_SPORTS_TELEGRAM_CHAT_ID must be set"
            )

    def send_message(self, text: str) -> bool:
        """Send a Markdown message to the configured Telegram chat.

        Args:
            text: Message text. Truncated to Telegram's 4096 character limit.

        Returns:
            True when Telegram returns HTTP 200, otherwise False.
        """
        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        payload = {
            "chat_id": self._chat_id,
            "text": text[:_MAX_TELEGRAM_CHARS],
            "parse_mode": "Markdown",
        }
        try:
            response = httpx.post(url, json=payload, timeout=10.0)
        except httpx.HTTPError:
            logger.warning("telegram_send_failed", exc_info=True)
            return False

        success = response.status_code == 200
        logger.info("telegram_send_complete", success=success, status_code=response.status_code)
        return success
