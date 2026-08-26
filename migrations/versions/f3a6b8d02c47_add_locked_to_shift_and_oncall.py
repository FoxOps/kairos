"""add locked to shift and on_call

Manual-pin flag for the automation planner (phase 5 of the automation
engine rework, see app/utils/automation/planner/adapters.py's
locked_oncalls/locked_shifts derivation) - a locked row is excluded
from the planner's candidate pool entirely, so a correctly-wired plan
can never propose reassigning/removing it. No admin UI sets this yet
in this rework (a column + read-side-only addition, deliberate scope
exclusion, not an oversight) - `server_default=false()` preserves
today's implicit behavior (nothing is locked) for every existing row,
no backfill loop needed (unlike group_id, which had no computable
default and needed a real per-row UPDATE - see migration 9c3e7a1f4b6d).

Revision ID: f3a6b8d02c47
Revises: e1f8a4c92d3b
Create Date: 2026-08-26 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f3a6b8d02c47"
down_revision = "e1f8a4c92d3b"
branch_labels = None
depends_on = None


def upgrade():
    # See 9c3e7a1f4b6d's own comment: run.py::setup_database()'s
    # legacy-DB backfill path (db.create_all() with current model
    # metadata) can leave this column already present by the time this
    # migration runs.
    inspector = sa.inspect(op.get_bind())

    shift_columns = [col["name"] for col in inspector.get_columns("shift")]
    with op.batch_alter_table("shift", schema=None) as batch_op:
        if "locked" not in shift_columns:
            batch_op.add_column(
                sa.Column(
                    "locked", sa.Boolean(), nullable=False, server_default=sa.false()
                )
            )

    on_call_columns = [col["name"] for col in inspector.get_columns("on_call")]
    with op.batch_alter_table("on_call", schema=None) as batch_op:
        if "locked" not in on_call_columns:
            batch_op.add_column(
                sa.Column(
                    "locked", sa.Boolean(), nullable=False, server_default=sa.false()
                )
            )


def downgrade():
    with op.batch_alter_table("on_call", schema=None) as batch_op:
        batch_op.drop_column("locked")

    with op.batch_alter_table("shift", schema=None) as batch_op:
        batch_op.drop_column("locked")
