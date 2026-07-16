"""add audit_log table

Append-only audit trail (who did what, when, to which resource) - see
app/models/audit_log.py::AuditLog and app/services/audit_service.py.

Revision ID: f1a4c8e2b9d6
Revises: a3f8c1d2e4b7
Create Date: 2026-07-16 10:20:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f1a4c8e2b9d6"
down_revision = "a3f8c1d2e4b7"
branch_labels = None
depends_on = None


def upgrade():
    # run.py::setup_database()'s legacy-DB backfill path calls
    # db.create_all() (current model metadata, which already includes
    # AuditLog) before stamping the baseline and running this migration -
    # on that path the table already exists by the time we get here.
    inspector = sa.inspect(op.get_bind())
    if "audit_log" in inspector.get_table_names():
        return

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=32), nullable=True),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.ForeignKeyConstraint(["actor_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("audit_log", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_audit_log_created_at"), ["created_at"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_audit_log_updated_at"), ["updated_at"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_audit_log_actor_id"), ["actor_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_audit_log_action"), ["action"], unique=False
        )
        batch_op.create_index(
            "idx_audit_log_resource", ["resource_type", "resource_id"], unique=False
        )


def downgrade():
    with op.batch_alter_table("audit_log", schema=None) as batch_op:
        batch_op.drop_index("idx_audit_log_resource")
        batch_op.drop_index(batch_op.f("ix_audit_log_action"))
        batch_op.drop_index(batch_op.f("ix_audit_log_actor_id"))
        batch_op.drop_index(batch_op.f("ix_audit_log_updated_at"))
        batch_op.drop_index(batch_op.f("ix_audit_log_created_at"))

    op.drop_table("audit_log")
