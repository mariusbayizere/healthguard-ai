"""Generic data-access layer.

Repositories own every query. Services own business rules and transaction
boundaries; routes own HTTP. No SQL or ORM query leaves this package.

Transaction note: the write helpers take `commit=True` by default so simple CRUD
reads naturally, but a service composing several writes into one atomic unit
passes `commit=False` and commits once itself. Triage depends on this — a
symptom report, its triage result and its queue entry must land together or not
at all.
"""

from __future__ import annotations

from typing import Any, Generic, Sequence, Type, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.base import TimestampedModel

ModelType = TypeVar("ModelType", bound=TimestampedModel)


class BaseRepository(Generic[ModelType]):
    """Type-safe CRUD operations shared by every model repository."""

    def __init__(self, model: Type[ModelType]) -> None:
        self.model = model

    # ── Reads ────────────────────────────────────────────────────────────
    def get_by_id(self, db: Session, record_id: int) -> ModelType | None:
        """Return a record by primary key, or None."""
        return db.get(self.model, record_id)

    def exists(self, db: Session, record_id: int) -> bool:
        """Whether a record with this primary key exists, without loading it."""
        return db.scalar(select(self.model.id).where(self.model.id == record_id)) is not None

    def get_all(
        self, db: Session, *, skip: int = 0, limit: int = 50
    ) -> Sequence[ModelType]:
        """Return a page of records, newest first."""
        return db.scalars(
            select(self.model)
            .order_by(self.model.created_at.desc(), self.model.id.desc())
            .offset(skip)
            .limit(limit)
        ).all()

    def count(self, db: Session) -> int:
        """Count all records."""
        return int(db.scalar(select(func.count()).select_from(self.model)) or 0)

    def _count_for(self, db: Session, statement: Select) -> int:
        """Count the rows a filtered SELECT would return.

        Counts over the statement as a subquery rather than rewriting its
        columns: `with_only_columns(func.count())` also discards the FROM clause
        derived from those columns, which silently yields 1 on Postgres.
        """
        return int(
            db.scalar(select(func.count()).select_from(statement.order_by(None).subquery()))
            or 0
        )

    # ── Writes ───────────────────────────────────────────────────────────
    def create(self, db: Session, *, commit: bool = True, **fields: Any) -> ModelType:
        """Insert a record. Flushes so server-side defaults are readable."""
        instance = self.model(**fields)
        db.add(instance)
        db.flush()
        if commit:
            db.commit()
        db.refresh(instance)
        return instance

    def update(
        self, db: Session, instance: ModelType, *, commit: bool = True, **fields: Any
    ) -> ModelType:
        """Apply the supplied fields to an existing record."""
        for field, value in fields.items():
            setattr(instance, field, value)
        db.flush()
        if commit:
            db.commit()
        return instance

    def delete(self, db: Session, instance: ModelType, *, commit: bool = True) -> None:
        """Hard-delete a record, letting database cascade rules apply."""
        db.delete(instance)
        if commit:
            db.commit()
