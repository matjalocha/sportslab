"""ASGI middleware for the SportsLab API."""

from api.middleware.clerk_auth import ClerkAuthMiddleware

__all__ = ["ClerkAuthMiddleware"]
