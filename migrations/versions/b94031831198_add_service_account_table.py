"""add service_account table

Bearer credentials for the public REST API (app/api/, /api/v1/*) - see
app/models/service_account.py::ServiceAccount and
app/auth/service_account_auth.py. Pure create_table, no ALTER on any
existing table, so this migration carries none of the "already applied
with an old column shape on a real deployment" risk documented on
migrations/versions/1055190bdf57_replace_user_apprise_toggle_with_.py -
still, once this revision ships to a real deployment, never amend it in
place: add a new migration instead.

Revision ID: b94031831198
Revises: 1055190bdf57
Create Date: 2026-07-17 09:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b94031831198"
down_revision = "1055190bdf57"
branch_labels = None
depends_on = None


def upgrade():
    # run.py::setup_database()'s legacy-DB backfill path calls
    # db.create_all() (current model metadata, which already includes
    # ServiceAccount) before stamping the baseline and running this
    # migration - on that path the table already exists by the time we
    # get here.
    inspector = sa.inspect(op.get_bind())
    if "service_account" in inspector.get_table_names():
        return

    op.create_table(
        "service_account",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("token_prefix", sa.String(length=16), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    with op.batch_alter_table("service_account", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_service_account_created_at"), ["created_at"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_service_account_updated_at"), ["updated_at"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_service_account_token_prefix"),
            ["token_prefix"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_service_account_token_hash"), ["token_hash"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_service_account_is_active"), ["is_active"], unique=False
        )


def downgrade():
    with op.batch_alter_table("service_account", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_service_account_is_active"))
        batch_op.drop_index(batch_op.f("ix_service_account_token_hash"))
        batch_op.drop_index(batch_op.f("ix_service_account_token_prefix"))
        batch_op.drop_index(batch_op.f("ix_service_account_updated_at"))
        batch_op.drop_index(batch_op.f("ix_service_account_created_at"))

    op.drop_table("service_account")
