"""add user language column

Personal UI language preference (nullable, ISO 639-1 code e.g. "fr"/"en").
Unset (None) means "use the organization's default_language setting"
(app/services/settings_service.py), resolved at read time - see
User.effective_language(). Mirrors 8b6f0e5b1c7a (User.timezone) exactly.

Revision ID: e7f4a9c2b6d1
Revises: c2a5e9f4b1d3
Create Date: 2026-07-15 23:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e7f4a9c2b6d1"
down_revision = "c2a5e9f4b1d3"
branch_labels = None
depends_on = None


def upgrade():
    # See 8b6f0e5b1c7a's comment: run.py::setup_database()'s legacy-DB
    # backfill path (db.create_all() with current model metadata, which
    # already includes User.language) can leave this column already
    # present by the time this migration runs.
    inspector = sa.inspect(op.get_bind())
    existing_columns = [col["name"] for col in inspector.get_columns("user")]
    if "language" in existing_columns:
        return

    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(sa.Column("language", sa.String(length=5), nullable=True))


def downgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("language")
