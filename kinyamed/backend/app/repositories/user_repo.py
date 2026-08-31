"""User and refresh-token data access."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.user import RefreshToken, User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self) -> None:
        super().__init__(User)

    def get_by_email(self, db: Session, email: str) -> User | None:
        """Return the account registered under this email, or None."""
        return db.scalars(select(User).where(User.email == email)).unique().one_or_none()

    def email_taken(self, db: Session, email: str) -> bool:
        """Whether an account already exists for this email."""
        return db.scalar(select(User.id).where(User.email == email)) is not None

    def list_users(
        self, db: Session, *, skip: int = 0, limit: int = 50
    ) -> tuple[Sequence[User], int]:
        """Return a page of accounts and the total."""
        statement = select(User)
        total = self._count_for(db, statement)
        rows = db.scalars(
            statement.order_by(User.created_at.desc()).offset(skip).limit(limit)
        ).unique().all()
        return rows, total


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self) -> None:
        super().__init__(RefreshToken)

    def get_by_jti(self, db: Session, jti: str) -> RefreshToken | None:
        """Return the recorded token with this id, or None."""
        return db.scalars(select(RefreshToken).where(RefreshToken.jti == jti)).one_or_none()

    def active_for_user(self, db: Session, user_id: int) -> Sequence[RefreshToken]:
        """Sessions that are neither revoked nor expired."""
        return db.scalars(
            select(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
            .order_by(RefreshToken.created_at.desc())
        ).all()

    def revoke(self, db: Session, token: RefreshToken, *, commit: bool = True) -> RefreshToken:
        """Mark one token as revoked, leaving the audit row in place."""
        if token.revoked_at is None:
            token.revoked_at = datetime.now(timezone.utc)
        db.flush()
        if commit:
            db.commit()
        return token

    def revoke_all_for_user(self, db: Session, user_id: int, *, commit: bool = True) -> int:
        """Revoke every live session for a user. Returns how many were ended."""
        result = db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        if commit:
            db.commit()
        return result.rowcount or 0

    def delete_expired(self, db: Session, *, commit: bool = True) -> int:
        """Purge tokens that expired long enough ago to be useless as an audit trail."""
        result = db.execute(
            RefreshToken.__table__.delete().where(
                RefreshToken.expires_at < datetime.now(timezone.utc)
            )
        )
        if commit:
            db.commit()
        return result.rowcount or 0


user_repository = UserRepository()
refresh_token_repository = RefreshTokenRepository()
