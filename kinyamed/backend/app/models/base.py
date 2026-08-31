"""Shared model base.

Every table carries a surrogate primary key and both timestamps, defaulted
server-side so that API, worker, migration and psql all record the same clock.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TimestampedModel(Base):
    """Abstract base model with an integer primary key and automatic timestamps."""

    __abstract__ = True

    # No index=True: the primary-key constraint already creates a unique index.
    # Adding another duplicates it, costing write throughput and disk on every
    # table for no read benefit.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
