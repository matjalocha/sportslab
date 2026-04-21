"""Tests for ``GET /api/v1/health``."""

from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient


def test_health_returns_200(client: TestClient) -> None:
    """Health endpoint is always reachable without auth."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_returns_version(client: TestClient) -> None:
    """Response includes the configured API version."""
    response = client.get("/api/v1/health")
    payload = response.json()
    assert payload["version"] == "0.1.0-test"
    assert payload["status"] == "ok"


def test_health_returns_iso_timestamp(client: TestClient) -> None:
    """Timestamp parses as an ISO-8601 datetime."""
    response = client.get("/api/v1/health")
    payload = response.json()
    # Will raise if not a valid ISO-8601 timestamp.
    parsed = datetime.fromisoformat(payload["timestamp"])
    assert parsed.tzinfo is not None, "Health timestamp must be timezone-aware"


def test_health_no_auth_required(client: TestClient) -> None:
    """No Authorization header — still 200, never 401."""
    response = client.get("/api/v1/health", headers={})
    assert response.status_code == 200
    assert "WWW-Authenticate" not in response.headers


def test_openapi_schema_public(client: TestClient) -> None:
    """OpenAPI schema is reachable without auth for codegen."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "SportsLab API"
