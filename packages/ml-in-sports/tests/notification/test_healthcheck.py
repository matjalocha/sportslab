"""Tests for healthchecks.io integration."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from ml_in_sports.notification.healthcheck import ping_failure, ping_success
from ml_in_sports.settings import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()


def test_ping_success_skips_when_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No request is made when healthcheck_id is empty."""
    called = False
    monkeypatch.delenv("ML_IN_SPORTS_HEALTHCHECK_ID", raising=False)
    get_settings.cache_clear()

    def fake_get(url: str, timeout: float) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(httpx, "get", fake_get)

    ping_success()

    assert called is False


def test_ping_success_calls_healthchecks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Success ping should call healthchecks.io."""
    captured: dict[str, Any] = {}
    monkeypatch.setenv("ML_IN_SPORTS_HEALTHCHECK_ID", "abc123")
    get_settings.cache_clear()

    def fake_get(url: str, timeout: float) -> None:
        captured["url"] = url
        captured["timeout"] = timeout

    monkeypatch.setattr(httpx, "get", fake_get)

    ping_success()

    assert captured["url"] == "https://hc-ping.com/abc123"
    assert captured["timeout"] == 5


def test_ping_failure_posts_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Failure ping should POST a truncated error message."""
    captured: dict[str, Any] = {}
    monkeypatch.setenv("ML_IN_SPORTS_HEALTHCHECK_ID", "abc123")
    get_settings.cache_clear()

    def fake_post(url: str, content: str, timeout: float) -> None:
        captured["url"] = url
        captured["content"] = content
        captured["timeout"] = timeout

    monkeypatch.setattr(httpx, "post", fake_post)

    ping_failure("x" * 20_000)

    assert captured["url"] == "https://hc-ping.com/abc123/fail"
    assert len(str(captured["content"])) == 10_000
    assert captured["timeout"] == 5


def test_ping_failure_swallows_network_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Healthcheck network errors should not break the pipeline."""
    monkeypatch.setenv("ML_IN_SPORTS_HEALTHCHECK_ID", "abc123")
    get_settings.cache_clear()

    def fake_post(url: str, content: str, timeout: float) -> None:
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(httpx, "post", fake_post)

    ping_failure("boom")
