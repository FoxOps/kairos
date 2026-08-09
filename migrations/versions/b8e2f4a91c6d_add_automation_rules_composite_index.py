"""add composite index on automation_rules(rule_type, group_id)

Every real lookup (AutomationRule.resolve_params()/has_group_override(),
called on every automation-rule resolution - now the hottest query path
in shift/on-call generation, see PERFORMANCE_OPTIMIZATION.md) filters on
rule_type and group_id together, not either column alone. The two
existing single-column indexes (from a3f7c1d9e4b2) can each narrow the
scan but can't satisfy the combined filter in one index lookup the way a
composite index can. Purely additive - existing single-column indexes
are left in place (SQLite/most engines still use them for a
rule_type-only or group_id-only filter, e.g. has_group_override()'s
group_id IS NULL-agnostic queries elsewhere), no data or behavior change.

Revision ID: b8e2f4a91c6d
Revises: a3f7c1d9e4b2
Create Date: 2026-08-07 00:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "b8e2f4a91c6d"
down_revision = "a3f7c1d9e4b2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("automation_rules", schema=None) as batch_op:
        batch_op.create_index(
            "ix_automation_rules_rule_type_group_id",
            ["rule_type", "group_id"],
            unique=False,
        )


def downgrade():
    with op.batch_alter_table("automation_rules", schema=None) as batch_op:
        batch_op.drop_index("ix_automation_rules_rule_type_group_id")
