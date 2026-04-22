"""SQLAlchemy ORM layer for the SportsLab API.

Split into three modules so migrations can import the metadata without
dragging the full API surface into Alembic's env.py:

- ``base``    -- :class:`Base` declarative class (only the registry).
- ``models``  -- ORM models registered against ``Base``.
- ``session`` -- async engine / session factory construction (wired in
  once the SPO-A-09 Postgres migration lands).

Kept deliberately thin: the runtime API still uses the existing Pydantic
providers (``UsersProvider``, ``TrackRecordProvider`` ABCs). These models
exist to define the durable schema so Alembic has something to diff, and
so the upcoming SQLAlchemy-backed providers have a real target.
"""

from api.db.base import Base
from api.db.models import User, UserBet, WebhookEvent

__all__ = ["Base", "User", "UserBet", "WebhookEvent"]
