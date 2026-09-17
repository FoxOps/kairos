"""add generation_runs table

Record-keeping for AutomationApplyService.apply_plan() (phase 5 of the
automation engine rework) - see app/models/generation_run.py::GenerationRun.
The table starts empty on upgrade: it's populated only once apply_plan()
is actually called, which no production code path does yet (phase 5
only adds the model/service, phase 6/7 wire it into the admin routes) -
behavior-neutral until then.

Revision ID: e1f8a4c92d3b
Revises: 9c3e7a1f4b6d
Create Date: 2026-08-26 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e1f8a4c92d3b"
down_revision = "9c3e7a1f4b6d"
branch_labels = None
depends_on = None


def upgrade():
    # run.py::setup_database()'s legacy-DB backfill path calls
    # db.create_all() (current model metadata, which already includes
    # GenerationRun) before stamping the baseline and running this
    # migration - on that path the table already exists by the time we
    # get here (same guard as a3f7c1d9e4b2_add_automation_rules_table.py).
    inspector = sa.inspect(op.get_bind())
    if "generation_runs" in inspector.get_table_names():
        return

    op.create_table(
        "generation_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=20), nullable=False),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["actor_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("generation_runs", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_generation_runs_created_at"), ["created_at"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_generation_runs_updated_at"), ["updated_at"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_generation_runs_start_date"), ["start_date"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_generation_runs_end_date"), ["end_date"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_generation_runs_outcome"), ["outcome"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_generation_runs_actor_id"), ["actor_id"], unique=False
        )


def downgrade():
    with op.batch_alter_table("generation_runs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_generation_runs_actor_id"))
        batch_op.drop_index(batch_op.f("ix_generation_runs_outcome"))
        batch_op.drop_index(batch_op.f("ix_generation_runs_end_date"))
        batch_op.drop_index(batch_op.f("ix_generation_runs_start_date"))
        batch_op.drop_index(batch_op.f("ix_generation_runs_updated_at"))
        batch_op.drop_index(batch_op.f("ix_generation_runs_created_at"))

    op.drop_table("generation_runs")
