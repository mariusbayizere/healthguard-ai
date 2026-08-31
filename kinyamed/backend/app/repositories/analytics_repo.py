"""Analytics snapshot data access."""

from __future__ import annotations

from datetime import date
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.analytics import Analytics
from app.repositories.base import BaseRepository


class AnalyticsRepository(BaseRepository[Analytics]):
    def __init__(self) -> None:
        super().__init__(Analytics)

    def list_snapshots(
        self, db: Session, *, skip: int = 0, limit: int = 50
    ) -> tuple[Sequence[Analytics], int]:
        """Return a page of snapshots, most recent first, and the total."""
        statement = select(Analytics)
        total = self._count_for(db, statement)
        rows = db.scalars(
            statement.order_by(Analytics.snapshot_date.desc()).offset(skip).limit(limit)
        ).all()
        return rows, total

    def upsert(self, db: Session, values: dict[str, Any], *, commit: bool = True) -> Analytics:
        """Insert today's snapshot, or replace the one already taken today.

        Upserted on `snapshot_date` so a scheduler re-running the job corrects
        the day's row rather than appending a duplicate.
        """
        statement = (
            pg_insert(Analytics)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[Analytics.snapshot_date],
                set_={k: v for k, v in values.items() if k != "snapshot_date"},
            )
            .returning(Analytics)
        )
        snapshot = db.scalars(statement).one()
        if commit:
            db.commit()
        return snapshot

    def delete_by_date(self, db: Session, snapshot_date: date, *, commit: bool = True) -> int:
        """Delete one day's snapshot. Returns the number of rows removed."""
        result = db.execute(
            Analytics.__table__.delete().where(Analytics.snapshot_date == snapshot_date)
        )
        if commit:
            db.commit()
        return result.rowcount or 0

    def delete_all(self, db: Session, *, commit: bool = True) -> int:
        """Delete every snapshot. Returns the number of rows removed."""
        result = db.execute(Analytics.__table__.delete())
        if commit:
            db.commit()
        return result.rowcount or 0


analytics_repository = AnalyticsRepository()
