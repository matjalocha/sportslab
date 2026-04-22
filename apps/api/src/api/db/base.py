"""Declarative base for SportsLab SQLAlchemy models.

Every ORM model inherits from :class:`Base`. Keep this module import-free
apart from SQLAlchemy so Alembic's ``env.py`` can import :data:`Base.metadata`
without triggering application startup side effects (settings loading,
logging configuration, Clerk JWKS warmup, etc.).
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models.

    Subclasses register themselves against :attr:`Base.metadata`, which
    Alembic introspects during ``--autogenerate`` to produce migration
    candidates.
    """
