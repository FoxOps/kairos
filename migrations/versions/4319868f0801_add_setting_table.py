"""add setting table

Revision ID: 4319868f0801
Revises: 23f95339785b
Create Date: 2026-07-15 16:14:47.064286

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "4319868f0801"
down_revision = "23f95339785b"
branch_labels = None
depends_on = None


def upgrade():
    # run.py::setup_database()'s legacy-DB backfill path calls
    # db.create_all() (current model metadata, which already includes
    # Setting) before stamping the baseline and running this migration -
    # on that path the table already exists by the time we get here.
    # Guard against "table already exists" rather than assuming a bare
    # CREATE TABLE is always safe.
    inspector = sa.inspect(op.get_bind())
    if "setting" in inspector.get_table_names():
        return

    op.create_table(
        "setting",
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    with op.batch_alter_table("setting", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_setting_created_at"), ["created_at"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_setting_updated_at"), ["updated_at"], unique=False
        )


def downgrade():
    with op.batch_alter_table("setting", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_setting_updated_at"))
        batch_op.drop_index(batch_op.f("ix_setting_created_at"))

    op.drop_table("setting")
