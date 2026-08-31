"""Database engine, session factory and the declarative base.

Schema changes are managed by Alembic (`migrations/`), never by
`Base.metadata.create_all`: an auto-created schema silently diverges from what
is deployed and gives no way to migrate existing patient data.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    # Verify a pooled connection before handing it out; without this, every
    # connection dropped by Postgres or a proxy surfaces as a failed request.
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE_SECONDS,
    echo=settings.DB_ECHO,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    # Keep attributes loaded after commit so a route can serialise the object
    # it just wrote without emitting another SELECT (or raising once detached).
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a request-scoped session.

    The session is rolled back if the request raises, so a failed request can
    never leave partial writes pending on a pooled connection.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
