"""add user notification preferences

Per-user opt-out for the weekly shift/on-call reminder emails, separate
toggles matching the two existing notification types (SHIFT_WEEKLY/
ONCALL_WEEKLY in app/services/notification_service.py). Default true on
both, at the DB level too (server_default) - preserves current behavior
for every existing user (nobody had an opt-out before, everyone got the
emails) until they explicitly disable one via /profile/settings. These
only take effect when notifications are enabled org-wide (see
SettingsService.get_notifications_enabled()) - the per-user toggle is a
finer-grained opt-out layered on top of that org-wide switch, not a
replacement for it.

Revision ID: c2a5e9f4b1d3
Revises: 8b6f0e5b1c7a
Create Date: 2026-07-15 22:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c2a5e9f4b1d3"
down_revision = "8b6f0e5b1c7a"
branch_labels = None
depends_on = None


def upgrade():
    # See 4319868f0801/8b6f0e5b1c7a's comments: run.py::setup_database()'s
    # legacy-DB backfill path (db.create_all() with current model
    # metadata) can leave these columns already present by the time this
    # migration runs.
    inspector = sa.inspect(op.get_bind())
    existing_columns = [col["name"] for col in inspector.get_columns("user")]

    with op.batch_alter_table("user", schema=None) as batch_op:
        if "shift_notifications_enabled" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "shift_notifications_enabled",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.true(),
                )
            )
        if "oncall_notifications_enabled" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "oncall_notifications_enabled",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.true(),
                )
            )


def downgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("oncall_notifications_enabled")
        batch_op.drop_column("shift_notifications_enabled")
