"""add notification_target table

Admin-managed outbound notification destinations (Slack, Discord,
Telegram, generic webhooks...) sent via Apprise - see
app/models/notification_target.py::NotificationTarget and
app/services/apprise_notification_service.py::AppriseNotificationService.

Revision ID: fda362a9150c
Revises: f1a4c8e2b9d6
Create Date: 2026-07-16 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "fda362a9150c"
down_revision = "f1a4c8e2b9d6"
branch_labels = None
depends_on = None


def upgrade():
    # run.py::setup_database()'s legacy-DB backfill path calls
    # db.create_all() (current model metadata, which already includes
    # NotificationTarget) before stamping the baseline and running this
    # migration - on that path the table already exists by the time we
    # get here.
    inspector = sa.inspect(op.get_bind())
    if "notification_target" in inspector.get_table_names():
        return

    op.create_table(
        "notification_target",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("apprise_url", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("categories", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("notification_target", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_notification_target_created_at"),
            ["created_at"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_notification_target_updated_at"),
            ["updated_at"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_notification_target_enabled"), ["enabled"], unique=False
        )


def downgrade():
    with op.batch_alter_table("notification_target", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_notification_target_enabled"))
        batch_op.drop_index(batch_op.f("ix_notification_target_updated_at"))
        batch_op.drop_index(batch_op.f("ix_notification_target_created_at"))

    op.drop_table("notification_target")
