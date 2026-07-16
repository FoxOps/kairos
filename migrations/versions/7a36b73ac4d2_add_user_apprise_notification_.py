"""add user apprise notification target selection

Per-user selection of which external notification target(s) (Slack/
Discord/Telegram/webhooks) should receive a relay of the weekly shift/
on-call reminders - independent of shift_notifications_enabled/
oncall_notifications_enabled (email), a user may want one channel
without the other. Stored as a JSON-encoded list of NotificationTarget
ids (same encode/decode idea as NotificationTarget.categories), not a
plain boolean: the user picks specific target(s) from the ones the
admin exposed for that category, rather than a blanket on/off. Empty/
NULL means no relay. Only takes effect when
SettingsService.get_apprise_notifications_enabled() is on org-wide.

Revision ID: 7a36b73ac4d2
Revises: fda362a9150c
Create Date: 2026-07-16 21:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7a36b73ac4d2"
down_revision = "fda362a9150c"
branch_labels = None
depends_on = None


def upgrade():
    # See c2a5e9f4b1d3's comment: run.py::setup_database()'s legacy-DB
    # backfill path (db.create_all() with current model metadata) can
    # leave these columns already present by the time this migration runs.
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


def downgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("apprise_oncall_target_ids")
        batch_op.drop_column("apprise_shift_target_ids")
