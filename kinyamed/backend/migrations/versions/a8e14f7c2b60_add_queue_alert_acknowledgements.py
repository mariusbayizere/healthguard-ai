"""add queue_alert_acknowledgements

Per-doctor record that a CRITICAL alert reached a human (reports/
ALERT_DELIVERY_DESIGN.md §3). It is what makes "never delivered", "delivered
and not acknowledged" and "acknowledged" three distinguishable states instead
of one guess.

PER DOCTOR, hence UNIQUE (queue_id, user_id) rather than a flag on `queue`.
"Seen by the doctor going off shift" is not "seen by the doctor coming on", and
a single global flag would let a CRITICAL vanish from the incoming doctor's
board because somebody else dismissed it.

DELIBERATELY NOT A COLUMN ON `queue`. Acknowledgement means "this alert reached
a human"; it does not mean the patient was assessed. Keeping it out of
`queue.status` is what stops "dismissed a popup" becoming indistinguishable
from "saw the patient" in every later audit and every retraining set.

Additive: one new table, nothing existing touched.

Revision ID: a8e14f7c2b60
Revises: f4c81d5a9e27
Create Date: 2026-09-17

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a8e14f7c2b60"
down_revision: str | Sequence[str] | None = "f4c81d5a9e27"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "queue_alert_acknowledgements",
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
        sa.Column("queue_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["queue_id"], ["queue.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # One acknowledgement per doctor per alert. Acknowledging twice is not
        # a second fact, and the constraint makes the backfill query's NOT
        # EXISTS an index probe rather than a scan.
        sa.UniqueConstraint("queue_id", "user_id", name="uq_alert_ack_queue_user"),
    )
    # The backfill asks "what has THIS doctor not acknowledged", so the user
    # leads the index.
    op.create_index(
        "ix_alert_ack_user", "queue_alert_acknowledgements", ["user_id", "queue_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_alert_ack_user", table_name="queue_alert_acknowledgements")
    op.drop_table("queue_alert_acknowledgements")
