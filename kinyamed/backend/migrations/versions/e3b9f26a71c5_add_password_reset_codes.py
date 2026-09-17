"""add password_reset_codes

Six-digit reset codes with a ten-minute window (FR-05-12). The table holds a
digest, never the code: the threat is a read of this table -- a backup, a query
log, a support export -- becoming account takeover for every reset in flight.

Additive: one new table, no existing object touched.

Revision ID: e3b9f26a71c5
Revises: d2a7c81b4e60
Create Date: 2026-09-17

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e3b9f26a71c5"
down_revision: str | Sequence[str] | None = "d2a7c81b4e60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "password_reset_codes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), nullable=False),
        # A bcrypt digest of the code. Never the code.
        sa.Column("code_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        # Set when the code is spent, which is what makes it single-use. Kept
        # rather than deleted so a support question about a reset can be
        # answered without the code ever having been recoverable.
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "attempts", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # The two lookups: the live code for an account, and the per-account
    # request cap counting recent rows.
    op.create_index(
        "ix_password_reset_codes_user",
        "password_reset_codes",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_password_reset_codes_user", table_name="password_reset_codes")
    op.drop_table("password_reset_codes")
