"""Shared Pydantic response / request models."""

from api.models.common import ErrorResponse, HealthResponse
from api.models.users import (
    NotificationPrefs,
    OnboardRequest,
    UserBet,
    UserBetCreate,
    UserProfile,
    UserProfileUpdate,
)
from api.models.webhooks import WebhookErrorResponse, WebhookResponse

__all__ = [
    "ErrorResponse",
    "HealthResponse",
    "NotificationPrefs",
    "OnboardRequest",
    "UserBet",
    "UserBetCreate",
    "UserProfile",
    "UserProfileUpdate",
    "WebhookErrorResponse",
    "WebhookResponse",
]
