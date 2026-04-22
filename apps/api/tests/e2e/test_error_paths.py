"""Cross-router error-path tests.

Per-router suites each cover their own 4xx surface. These tests assert
consistency across the edge: the same error shapes, the same headers,
the same auth-vs-validation ordering. A regression where, say, 422 leaks
as 400 or 404 gets swallowed into 500 surfaces here before it hits a
customer.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

_WARSAW = ZoneInfo("Europe/Warsaw")


def test_predictions_404_on_nonexistent_date_shape(e2e_user_client: TestClient) -> None:
    """Malformed date path -> 422 (Pydantic path-param validation).

    FastAPI rejects non-ISO dates at the path layer before the handler
    runs. We assert 422 (not 400, not 500) so the frontend can rely on
    "422 means you gave me garbage, 404 means not found, 425 means too
    early" as disjoint signals.
    """
    response = e2e_user_client.get("/api/v1/predictions/not-a-date")
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body


def test_results_425_on_future_date(e2e_user_client: TestClient) -> None:
    """``GET /predictions/{today}/results`` -> 425 Too Early.

    The handler refuses future or same-day dates so we never render
    half-settled slips. 425 is RFC-8470 and semantically "try again
    later" -- the frontend uses it to swap to a "check back after
    kickoff" CTA rather than a generic error toast.
    """
    future = (datetime.now(_WARSAW) + timedelta(days=3)).date().isoformat()
    response = e2e_user_client.get(f"/api/v1/predictions/{future}/results")
    assert response.status_code == 425
    assert "not yet available" in response.json()["detail"].lower()


def test_onboard_422_on_invalid_payload(e2e_user_client: TestClient) -> None:
    """POST /users/onboard with missing required field -> 422.

    ``bankrollTier`` is required by :class:`OnboardRequest`; omitting it
    MUST fail at the Pydantic layer before the handler body runs, so we
    never allow an un-tiered profile to be created.
    """
    response = e2e_user_client.post(
        "/api/v1/users/onboard",
        json={
            "email": "no-tier@sportslab.example.com",
            # ``bankrollTier`` deliberately missing.
            "experienceLevel": "beginner",
        },
    )
    assert response.status_code == 422
    body = response.json()
    detail = body["detail"]
    # Pydantic returns a list of issues; at least one must cite bankrollTier.
    assert any("bankrollTier" in str(issue) or "bankroll_tier" in str(issue) for issue in detail)


def test_onboard_422_on_invalid_email(e2e_user_client: TestClient) -> None:
    """Invalid email -> 422 before any profile state is created.

    EmailStr rejects obvious junk. This test also implicitly guards the
    [email] optional dep on Pydantic -- dropping the pydantic[email]
    extra would 500 instead of 422.
    """
    response = e2e_user_client.post(
        "/api/v1/users/onboard",
        json={
            "email": "not-an-email",
            "bankrollTier": "1k_5k",
            "experienceLevel": "beginner",
        },
    )
    assert response.status_code == 422

    # No profile was created as a side effect of the rejected request.
    follow_up = e2e_user_client.get("/api/v1/users/me")
    assert follow_up.status_code == 404


def test_patch_unknown_admin_user_returns_404(e2e_admin_client: TestClient) -> None:
    """PATCH /admin/users/{id} with unknown id -> 404, never 500.

    Cross-router concern: the admin PATCH MUST not silently create a new
    user row. A 404 here proves the handler went through the provider's
    existence check.
    """
    response = e2e_admin_client.patch(
        "/api/v1/admin/users/user_does_not_exist_ever",
        json={"plan": "pro"},
    )
    assert response.status_code == 404


def test_rollback_to_same_version_returns_409(e2e_admin_client: TestClient) -> None:
    """Rollback with the currently-deployed version -> 409, not 200.

    Prevents noisy audit log entries for no-op rollbacks, and acts as a
    safety net against a frontend double-submit.
    """
    # Pull current deployed version from /admin/system so the test stays
    # correct even if the seed changes.
    system = e2e_admin_client.get("/api/v1/admin/system").json()
    current_version = system["model"]["version"]

    response = e2e_admin_client.post(
        "/api/v1/admin/model/rollback",
        json={"targetVersion": current_version},
    )
    assert response.status_code == 409
    assert "already deployed" in response.json()["detail"].lower()


def test_create_bet_before_onboard_returns_404(e2e_user_client: TestClient) -> None:
    """Authenticated but not-onboarded users hit 404 on POST /users/me/bets.

    Guard against a silent upsert path -- the users provider must refuse
    to create bets without a prior profile so `follows_model` attribution
    has a stable foreign key target when the DB lands.
    """
    response = e2e_user_client.post(
        "/api/v1/users/me/bets",
        json={
            "matchId": "match_never_created",
            "market": "1X2",
            "selection": "home",
            "stakeEur": 10.0,
            "odds": 2.0,
            "bookmaker": "Pinnacle",
        },
    )
    assert response.status_code == 404
