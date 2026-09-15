"""Add password reset tokens.

Only the SHA-256 of each token is stored: the raw value is a bearer credential
that grants account takeover, so a database read must not be a password reset
for every pending user.

Revision ID: f1a2b3c4d5e6
Revises: e77159c3482a
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f1a2b3c4d5e6"
down_revision = "e77159c3482a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_password_reset_tokens_token_hash",
        "password_reset_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"]
    )
    op.create_index(
        "ix_password_reset_tokens_created_at", "password_reset_tokens", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_created_at", "password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_user_id", "password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_token_hash", "password_reset_tokens")
    op.drop_table("password_reset_tokens")
