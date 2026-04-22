"""End-to-end cross-router integration tests.

Per-router tests (``tests/test_*.py``) cover each endpoint in isolation
with narrow fixtures. The suites in this package instead exercise
realistic user journeys that span multiple routers -- onboard -> update ->
create bet -> list bets, admin RBAC enforcement across ``/admin/*``,
webhook idempotency across providers, public-endpoint bypass of Clerk
auth, and representative error paths.

Scope caveats:

* Auth transport is stubbed via ``dependency_overrides`` and a
  monkey-patched ``ClerkAuthMiddleware.dispatch`` -- we do not talk to
  real Clerk JWKS. The auth *boundary* (missing / malformed Bearer)
  still goes through the real middleware via the ``anon_client``
  fixture.
* Providers are the in-memory stubs (``StubUsersProvider``,
  ``StubAdminProvider``, ``InMemoryIdempotencyStore``,
  ``StubPredictionsProvider``, ``StubTrackRecordProvider``). DB-backed
  providers (SPO-A-09) will be covered by a parallel suite that uses a
  real SQLite volume.
"""
