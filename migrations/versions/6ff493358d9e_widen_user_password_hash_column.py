"""widen user.password_hash column to 255 chars

werkzeug.security.generate_password_hash()'s default method (scrypt)
produces a ~162-character string - the column was String(128), which
SQLite never enforces (accepts any length silently) but MySQL/
PostgreSQL both reject outright ("Data too long for column"), even for
the very first default-admin creation on a fresh install. Found and
confirmed while adding MySQL/MariaDB support (see
app/models/service_account.py::ServiceAccount for the unrelated new
table added in the same effort) - not a pre-existing MySQL deployment
issue that could have already applied this column with the old length,
so a plain ALTER (not a drop+recreate) is safe here.

Revision ID: 6ff493358d9e
Revises: b94031831198
Create Date: 2026-07-17 02:20:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6ff493358d9e"
down_revision = "b94031831198"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.String(length=128),
            type_=sa.String(length=255),
            existing_nullable=True,
        )


def downgrade():
    # Lossy if any stored hash exceeds 128 chars (true for every scrypt
    # hash generated since this migration was introduced) - narrowing
    # back is provided for symmetry, not a safe operation to actually run
    # against a database with real user accounts.
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.String(length=255),
            type_=sa.String(length=128),
            existing_nullable=True,
        )
