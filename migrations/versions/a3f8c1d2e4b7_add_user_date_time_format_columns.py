"""add user date_format and time_format columns

Personal date/time display format preference (nullable strftime
patterns, e.g. "%d/%m/%Y" / "%H:%M"). Unset (None) means "use the
organization's default_date_format/default_time_format setting"
(app/services/settings_service.py), resolved at read time - see
User.effective_date_format()/effective_time_format(). Mirrors
e7f4a9c2b6d1 (User.language) exactly, just two columns instead of one.

Revision ID: a3f8c1d2e4b7
Revises: e7f4a9c2b6d1
Create Date: 2026-07-16 08:10:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a3f8c1d2e4b7"
down_revision = "e7f4a9c2b6d1"
branch_labels = None
depends_on = None


def upgrade():
    # See e7f4a9c2b6d1's comment: run.py::setup_database()'s legacy-DB
    # backfill path (db.create_all() with current model metadata, which
    # already includes these columns) can leave them already present by
    # the time this migration runs.
    inspector = sa.inspect(op.get_bind())
    existing_columns = [col["name"] for col in inspector.get_columns("user")]

    with op.batch_alter_table("user", schema=None) as batch_op:
        if "date_format" not in existing_columns:
            batch_op.add_column(
                sa.Column("date_format", sa.String(length=20), nullable=True)
            )
        if "time_format" not in existing_columns:
            batch_op.add_column(
                sa.Column("time_format", sa.String(length=20), nullable=True)
            )


def downgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("time_format")
        batch_op.drop_column("date_format")
