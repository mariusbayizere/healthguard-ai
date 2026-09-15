"""red-flag layer columns on triage_results, with escalate-only enforced by the database

Revision ID: a7c3e9f1d2b4
Revises: e77159c3482a
Create Date: 2026-09-15

SQL approved as written on 2026-09-15 (CLAUDE.md L14, STATE.md). Executed verbatim
rather than rebuilt from Alembic operations, so the statements that run are the
statements that were approved.

- rules_layer_triggered: whether the red-flag layer escalated this triage.
- rules_layer_reason: the matched lexicon concept_id(s) only, never patient text (L11).
- model_urgency_raw: the model's own prediction before the rules layer. Left NULL on
  rows written before this migration: some came from the since-removed keyword
  fallback (before fb64dc2), so labelling them model output would be false.

The CHECK constraints make escalate-only a database property: no writer can store
an urgency lower than the model's (enum order CRITICAL < URGENT < ROUTINE).

MERGE HAZARD (STATE.md H21): wip/account-analytics-frontend adds f1a2b3c4d5e6 on the
same parent, e77159c3482a. Merging needs an Alembic merge revision.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "a7c3e9f1d2b4"
down_revision: str | Sequence[str] | None = "e77159c3482a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE triage_results
          ADD COLUMN rules_layer_triggered BOOLEAN NOT NULL DEFAULT false,
          ADD COLUMN rules_layer_reason    VARCHAR(200),
          ADD COLUMN model_urgency_raw     urgencylevel
        """
    )
    op.execute(
        """
        ALTER TABLE triage_results
          ADD CONSTRAINT ck_triage_results_rules_reason_iff_triggered
            CHECK (rules_layer_triggered = (rules_layer_reason IS NOT NULL)),
          ADD CONSTRAINT ck_triage_results_rules_escalate_only
            CHECK (model_urgency_raw IS NULL OR urgency_level <= model_urgency_raw),
          ADD CONSTRAINT ck_triage_results_untriggered_keeps_model_urgency
            CHECK (rules_layer_triggered OR model_urgency_raw IS NULL OR urgency_level = model_urgency_raw)
        """
    )


def downgrade() -> None:
    # Drops only the three columns this migration added, and their data.
    op.execute(
        """
        ALTER TABLE triage_results
          DROP CONSTRAINT ck_triage_results_untriggered_keeps_model_urgency,
          DROP CONSTRAINT ck_triage_results_rules_escalate_only,
          DROP CONSTRAINT ck_triage_results_rules_reason_iff_triggered
        """
    )
    op.execute(
        """
        ALTER TABLE triage_results
          DROP COLUMN model_urgency_raw, DROP COLUMN rules_layer_reason, DROP COLUMN rules_layer_triggered
        """
    )
