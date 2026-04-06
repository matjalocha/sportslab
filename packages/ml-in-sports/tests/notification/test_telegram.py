"""Tests for Telegram notifier."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from ml_in_sports.notification.telegram import TelegramNotifier
from ml_in_sports.settings import get_settings


class _Response:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()


def test_send_message_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """send_message should return True when Telegram returns 200."""
    captured: dict[str, Any] = {}
    monkeypatch.setenv("ML_IN_SPORTS_TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("ML_IN_SPORTS_TELEGRAM_CHAT_ID", "chat")
    get_settings.cache_clear()

    def fake_post(url: str, json: dict[str, object], timeout: float) -> _Response:
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return _Response(200)

    monkeypatch.setattr(httpx, "post", fake_post)

    assert TelegramNotifier().send_message("hello") is True
    assert captured["url"] == "https://api.telegram.org/bottoken/sendMessage"
    assert captured["json"]["text"] == "hello"
    assert captured["json"]["parse_mode"] == "Markdown"


def test_message_is_truncated(monkeypatch: pytest.MonkeyPatch) -> None:
    """Telegram payload should be truncated to 4096 characters."""
    captured: dict[str, Any] = {}
    monkeypatch.setenv("ML_IN_SPORTS_TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("ML_IN_SPORTS_TELEGRAM_CHAT_ID", "chat")
    get_settings.cache_clear()

    def fake_post(url: str, json: dict[str, object], timeout: float) -> _Response:
        captured["json"] = json
        return _Response(200)

    monkeypatch.setattr(httpx, "post", fake_post)

    assert TelegramNotifier().send_message("x" * 5000) is True
    assert len(str(captured["json"]["text"])) == 4096


def test_missing_token_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Notifier should fail fast when credentials are missing."""
    monkeypatch.delenv("ML_IN_SPORTS_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("ML_IN_SPORTS_TELEGRAM_CHAT_ID", raising=False)
    get_settings.cache_clear()

    with pytest.raises(ValueError):
        TelegramNotifier()


def test_network_error_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """Network errors should be reported as False, not raised."""
    monkeypatch.setenv("ML_IN_SPORTS_TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("ML_IN_SPORTS_TELEGRAM_CHAT_ID", "chat")
    get_settings.cache_clear()

    def fake_post(url: str, json: dict[str, object], timeout: float) -> _Response:
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(httpx, "post", fake_post)

    assert TelegramNotifier().send_message("hello") is False
