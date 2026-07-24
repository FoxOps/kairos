"""add automation_rules table

Configurable automation rules engine: an extensible, plugin-style
store for the business rules that drive shift/on-call generation -
see app/models/automation_rule.py::AutomationRule and
app/utils/automation/rules/ for the rule-type classes that interpret
`params`. The table starts empty on upgrade: an absent row means "use
this rule type's own default_params()", which is set to match the
previously hardcoded behavior exactly - so this migration is
behavior-neutral until an admin actually configures something.

Revision ID: a3f7c1d9e4b2
Revises: c88d6b7b34a4
Create Date: 2026-07-24 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a3f7c1d9e4b2"
down_revision = "c88d6b7b34a4"
branch_labels = None
depends_on = None


def upgrade():
    # run.py::setup_database()'s legacy-DB backfill path calls
    # db.create_all() (current model metadata, which already includes
    # AutomationRule) before stamping the baseline and running this
    # migration - on that path the table already exists by the time we
    # get here.
    inspector = sa.inspect(op.get_bind())
    if "automation_rules" in inspector.get_table_names():
        return

    op.create_table(
        "automation_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=True),
        sa.Column("rule_type", sa.String(length=50), nullable=False),
        sa.Column("params", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("automation_rules", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_automation_rules_created_at"), ["created_at"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_automation_rules_updated_at"), ["updated_at"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_automation_rules_group_id"), ["group_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_automation_rules_rule_type"), ["rule_type"], unique=False
        )


def downgrade():
    with op.batch_alter_table("automation_rules", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_automation_rules_rule_type"))
        batch_op.drop_index(batch_op.f("ix_automation_rules_group_id"))
        batch_op.drop_index(batch_op.f("ix_automation_rules_updated_at"))
        batch_op.drop_index(batch_op.f("ix_automation_rules_created_at"))

    op.drop_table("automation_rules")
