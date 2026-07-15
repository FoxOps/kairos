"""add user timezone column

Personal timezone preference (nullable, IANA name e.g. "Europe/Paris").
Unset (None) means "use the organization's default_timezone setting"
(app/services/settings_service.py), resolved at read time - see
User.effective_timezone().

Revision ID: 8b6f0e5b1c7a
Revises: 4319868f0801
Create Date: 2026-07-15 16:20:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8b6f0e5b1c7a"
down_revision = "4319868f0801"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(sa.Column("timezone", sa.String(length=64), nullable=True))


def downgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("timezone")
