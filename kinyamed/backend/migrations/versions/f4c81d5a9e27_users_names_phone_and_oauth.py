"""split users.full_name, add phone, OAuth columns and a refresh-token digest

Three requirements land together because they touch one table and splitting
them would mean three migrations over the same rows (FR-05-02, FR-05-04,
FR-05-12's delivery gap).

NAMES. `full_name` becomes `first_name` + `last_name`. The backfill splits on
the first space. `last_name` is NULLABLE, and that is deliberate: a row
recorded as a single word has no last name to recover, and writing '' or
repeating the first name would be inventing data to satisfy a constraint. NULL
says "not captured under the old scheme", which is true. New registrations
require both, enforced in the schema layer where the information actually
exists.

PHONE. Staff accounts had no phone anywhere, so a password-reset code could not
reach them (FR-05-12). Nullable because a patient's number lives on their
`patients` row and a staff member may not have supplied one yet.

OAUTH. `hashed_password` becomes NULLABLE so a Google account can exist without
one, guarded by a CHECK that every row has a password or an OAuth identity.
Without that CHECK, relaxing the column would silently permit an account with
no way to authenticate at all.

Revision ID: f4c81d5a9e27
Revises: e3b9f26a71c5
Create Date: 2026-09-17

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f4c81d5a9e27"
down_revision: str | Sequence[str] | None = "e3b9f26a71c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Names ────────────────────────────────────────────────────────────
    op.add_column("users", sa.Column("first_name", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(length=50), nullable=True))
    op.execute(
        """
        UPDATE users
           SET first_name = split_part(trim(full_name), ' ', 1),
               last_name  = NULLIF(
                   trim(substring(trim(full_name)
                        from position(' ' in trim(full_name)) + 1)),
                   ''
               )
         WHERE first_name IS NULL
        """
    )
    # Every row has at least one word, so first_name is now complete and can
    # carry the constraint the application relies on.
    op.alter_column("users", "first_name", nullable=False)
    op.drop_column("users", "full_name")

    # ── Phone, avatar ────────────────────────────────────────────────────
    op.add_column("users", sa.Column("phone", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.String(length=512), nullable=True))

    # ── OAuth ────────────────────────────────────────────────────────────
    op.add_column(
        "users", sa.Column("oauth_provider", sa.String(length=32), nullable=True)
    )
    op.add_column("users", sa.Column("oauth_id", sa.String(length=255), nullable=True))
    op.create_unique_constraint(
        "uq_users_oauth_identity", "users", ["oauth_provider", "oauth_id"]
    )
    op.alter_column("users", "hashed_password", nullable=True)

    # ── Refresh tokens hashed at rest (FR-05-06) ─────────────────────────
    # SHA-256, not bcrypt: bcrypt silently truncates past 72 bytes and a JWT is
    # far longer, so it would hash a prefix. The token is high-entropy and not
    # guessable, so the slow-hash argument that applies to passwords does not
    # apply here; what is wanted is that a read of the table yields nothing
    # usable. Nullable for rows written before this migration.
    op.add_column(
        "refresh_tokens", sa.Column("token_hash", sa.String(length=128), nullable=True)
    )
    op.create_check_constraint(
        "ck_users_has_a_credential",
        "users",
        "hashed_password IS NOT NULL OR oauth_provider IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_column("refresh_tokens", "token_hash")
    op.drop_constraint("ck_users_has_a_credential", "users", type_="check")
    # Rows with no password cannot exist once the column is NOT NULL again.
    # Refusing loudly beats writing a placeholder digest that would look like a
    # credential and authenticate nobody.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM users WHERE hashed_password IS NULL) THEN
                RAISE EXCEPTION
                  'Cannot downgrade: % OAuth-only account(s) have no password.',
                  (SELECT count(*) FROM users WHERE hashed_password IS NULL);
            END IF;
        END $$;
        """
    )
    op.alter_column("users", "hashed_password", nullable=False)
    op.drop_constraint("uq_users_oauth_identity", "users", type_="unique")
    op.drop_column("users", "oauth_id")
    op.drop_column("users", "oauth_provider")
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "phone")

    op.add_column("users", sa.Column("full_name", sa.String(length=100), nullable=True))
    op.execute(
        "UPDATE users SET full_name = trim(first_name || ' ' || coalesce(last_name, ''))"
    )
    op.alter_column("users", "full_name", nullable=False)
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
