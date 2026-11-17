"""add scopes to service_account

ServiceAccount read scopes for the public API (/api/v1/*) - JSON-encoded
list of AVAILABLE_SCOPES strings (app/models/service_account.py). Nullable,
no backfill needed: empty/NULL means full access (read:*), same convention
as NotificationTarget.categories, so every ServiceAccount that existed
before this migration keeps its current (full) access unchanged.

Revision ID: 4e3f044b5851
Revises: f3a6b8d02c47
Create Date: 2026-09-17 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "4e3f044b5851"
down_revision = "f3a6b8d02c47"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("service_account", schema=None) as batch_op:
        batch_op.add_column(sa.Column("scopes", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("service_account", schema=None) as batch_op:
        batch_op.drop_column("scopes")
