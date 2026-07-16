"""replace user apprise toggle with target selection

Superseded design (from the very same unreleased feature, caught before
0.9.1 shipped): a plain on/off toggle
(apprise_shift_notifications_enabled/apprise_oncall_notifications_enabled)
isn't expressive enough - a user must be able to choose *which*
external notification target(s) receive their own weekly reminder, not
just whether any of them do. Replaces those two Boolean columns with
apprise_shift_target_ids/apprise_oncall_target_ids (Text, JSON-encoded
list of NotificationTarget ids, same encode/decode idea as
NotificationTarget.categories). This is a separate migration rather
than an edit to 7a36b73ac4d2 itself because that revision may already
be recorded as applied in a real database (Alembic does not re-run a
migration whose revision id already appears in alembic_version, even if
its file content changes afterwards) - amending it in place left such
a database missing the new columns entirely.

Revision ID: 1055190bdf57
Revises: 7a36b73ac4d2
Create Date: 2026-07-16 22:05:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1055190bdf57"
down_revision = "7a36b73ac4d2"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    existing_columns = [col["name"] for col in inspector.get_columns("user")]

    with op.batch_alter_table("user", schema=None) as batch_op:
        if "apprise_shift_target_ids" not in existing_columns:
            batch_op.add_column(
                sa.Column("apprise_shift_target_ids", sa.Text(), nullable=True)
            )
        if "apprise_oncall_target_ids" not in existing_columns:
            batch_op.add_column(
                sa.Column("apprise_oncall_target_ids", sa.Text(), nullable=True)
            )
        if "apprise_shift_notifications_enabled" in existing_columns:
            batch_op.drop_column("apprise_shift_notifications_enabled")
        if "apprise_oncall_notifications_enabled" in existing_columns:
            batch_op.drop_column("apprise_oncall_notifications_enabled")


def downgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "apprise_oncall_notifications_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "apprise_shift_notifications_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
        batch_op.drop_column("apprise_oncall_target_ids")
        batch_op.drop_column("apprise_shift_target_ids")
