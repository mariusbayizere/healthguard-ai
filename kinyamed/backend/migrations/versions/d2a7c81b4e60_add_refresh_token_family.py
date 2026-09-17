"""add refresh_tokens.family_id

Reuse detection was user-wide: replaying one rotated token ended every session
the person had. A family is one login and everything rotated from it, so reuse
can end the compromised lineage and leave the others alone (FR-05-13).

Additive. The column lands NOT NULL with a `gen_random_uuid()` default, which
gives every existing row its own family: each token already in the table is
treated as its own lineage, which is the safe reading -- it means an old token
being replayed ends only itself rather than a family it was never really part
of. PostgreSQL 13+ provides gen_random_uuid() in core; this project runs 16.

Revision ID: d2a7c81b4e60
Revises: c1f4a2b7d903
Create Date: 2026-09-17

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d2a7c81b4e60"
down_revision: str | Sequence[str] | None = "c1f4a2b7d903"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "refresh_tokens",
        sa.Column(
            "family_id",
            sa.String(length=36),
            nullable=False,
            server_default=sa.text("gen_random_uuid()::text"),
        ),
    )
    # The application always supplies a family id; the default exists only to
    # populate the rows that predate this column. Keeping it would let a future
    # insert silently start its own family instead of joining one.
    op.alter_column("refresh_tokens", "family_id", server_default=None)
    # Reuse detection revokes by family, so that lookup must not scan.
    op.create_index(
        "ix_refresh_tokens_family", "refresh_tokens", ["family_id", "revoked_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_family", table_name="refresh_tokens")
    op.drop_column("refresh_tokens", "family_id")
