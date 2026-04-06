"""Healthchecks.io integration for pipeline monitoring."""

from __future__ import annotations

import httpx
import structlog

from ml_in_sports.settings import get_settings

logger = structlog.get_logger(__name__)


def ping_success() -> None:
    """Ping healthchecks.io on successful pipeline run."""
    healthcheck_id = get_settings().healthcheck_id
    if not healthcheck_id:
        return
    try:
        httpx.get(f"https://hc-ping.com/{healthcheck_id}", timeout=5)
        logger.info("healthcheck_pinged", status="success")
    except Exception as exc:
        logger.warning("healthcheck_failed", error=str(exc))


def ping_failure(error_message: str = "") -> None:
    """Ping healthchecks.io on pipeline failure."""
    healthcheck_id = get_settings().healthcheck_id
    if not healthcheck_id:
        return
    try:
        httpx.post(
            f"https://hc-ping.com/{healthcheck_id}/fail",
            content=error_message[:10000],
            timeout=5,
        )
        logger.info("healthcheck_pinged", status="fail")
    except Exception as exc:
        logger.warning("healthcheck_failed", error=str(exc))
