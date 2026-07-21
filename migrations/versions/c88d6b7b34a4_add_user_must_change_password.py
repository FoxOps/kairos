"""add user.must_change_password

Password policy hardening (ANSSI-PG-078 section 4): forces a user
through auth.update_profile on their next login whenever a password is
chosen *for* them rather than by them - the default admin bootstrap
password, or an admin creating/resetting a user's password. Defaults to
False for the column itself (existing accounts aren't retroactively
forced to change anything on upgrade) - only the specific code paths
above ever set it True, at the Python level.

Revision ID: c88d6b7b34a4
Revises: 5735938f1832
Create Date: 2026-07-21 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c88d6b7b34a4"
down_revision = "5735938f1832"
branch_labels = None
depends_on = None


def upgrade():
    # Same guard as 5735938f1832/8b6f0e5b1c7a/etc: run.py::setup_database()'s
    # legacy-DB backfill path (db.create_all() with current model metadata,
    # which already includes User.must_change_password) can leave this
    # column already present by the time this migration runs.
    inspector = sa.inspect(op.get_bind())
    existing_columns = [col["name"] for col in inspector.get_columns("user")]
    if "must_change_password" not in existing_columns:
        with op.batch_alter_table("user", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "must_change_password",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                )
            )


def downgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("must_change_password")
