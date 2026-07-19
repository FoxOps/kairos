"""add user.ics_token_created_at, enforcing ics token expiry

ICS_TOKEN_EXPIRY_DAYS existed as a Setting but nothing checked it -
User.ics_token never carried a creation timestamp, so there was
nothing to measure elapsed time against. Adds that timestamp and
backfills every already-issued token (ics_token IS NOT NULL) with
now() rather than leaving it NULL: a NULL is treated as "expired" by
User.is_ics_token_expired() (see app/models/user.py), and blanket-
expiring every calendar subscription already configured by a user the
moment this migration runs would be a surprising breaking change, not
a security fix - existing tokens instead get a fresh full expiry
window starting from this deploy.

Revision ID: 5735938f1832
Revises: 6ff493358d9e
Create Date: 2026-07-19 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5735938f1832"
down_revision = "6ff493358d9e"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(sa.Column("ics_token_created_at", sa.DateTime(), nullable=True))

    user = sa.table(
        "user",
        sa.column("ics_token", sa.String),
        sa.column("ics_token_created_at", sa.DateTime),
    )
    op.execute(
        user.update()
        .where(user.c.ics_token.isnot(None))
        .values(ics_token_created_at=sa.func.now())
    )


def downgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("ics_token_created_at")
