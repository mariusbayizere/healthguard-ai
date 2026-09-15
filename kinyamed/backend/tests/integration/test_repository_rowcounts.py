"""Characterisation: repository deletes and bulk revokes report how many rows they changed.

The mypy backlog retyped these four methods (casts on `__table__` and on the
execute result). The SQL and the returned count must not change; nothing tested
them before.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta


def _token(db, user_id: int, *, expires_at: datetime, revoked: bool = False):
    from app.models.user import RefreshToken

    token = RefreshToken(
        jti=str(uuid.uuid4()),
        user_id=user_id,
        expires_at=expires_at,
        revoked_at=datetime.now(UTC) if revoked else None,
    )
    db.add(token)
    db.commit()
    return token


def test_analytics_delete_by_date_and_delete_all_return_row_counts(db):
    from app.models.analytics import Analytics
    from app.repositories import analytics_repository

    for offset in range(3):
        db.add(Analytics(snapshot_date=date(2026, 9, 1) + timedelta(days=offset)))
    db.commit()

    assert analytics_repository.delete_by_date(db, date(2026, 9, 2)) == 1
    assert analytics_repository.delete_by_date(db, date(2026, 9, 2)) == 0
    assert analytics_repository.delete_all(db) == 2
    assert analytics_repository.delete_all(db) == 0


def test_refresh_token_revoke_all_counts_only_live_sessions(db, user_factory):
    from app.repositories import refresh_token_repository

    user, other = user_factory(), user_factory()
    soon = datetime.now(UTC) + timedelta(days=1)
    _token(db, user.id, expires_at=soon)
    _token(db, user.id, expires_at=soon)
    _token(db, user.id, expires_at=soon, revoked=True)
    _token(db, other.id, expires_at=soon)

    assert refresh_token_repository.revoke_all_for_user(db, user.id) == 2
    assert refresh_token_repository.revoke_all_for_user(db, user.id) == 0


def test_refresh_token_delete_expired_counts_only_expired(db, user_factory):
    from app.repositories import refresh_token_repository

    user = user_factory()
    _token(db, user.id, expires_at=datetime.now(UTC) - timedelta(days=2))
    _token(db, user.id, expires_at=datetime.now(UTC) + timedelta(days=2))

    assert refresh_token_repository.delete_expired(db) == 1
    assert refresh_token_repository.delete_expired(db) == 0
