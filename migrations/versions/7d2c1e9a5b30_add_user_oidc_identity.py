"""add user OIDC identity binding

Binds a local account to its external SSO identity (issuer + subject)
instead of trusting the email claim alone (audit F02, see
report/1.2.0/AUDIT_REPORT_1.2.0.md). Both columns nullable, no backfill:
an existing account gets bound on its next SSO login
(app/auth/user_manager.py::UserManager.sync_user_from_oidc).

Revision ID: 7d2c1e9a5b30
Revises: 4e3f044b5851
Create Date: 2026-11-16 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7d2c1e9a5b30"
down_revision = "4e3f044b5851"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(sa.Column("oidc_issuer", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("oidc_subject", sa.String(255), nullable=True))
        batch_op.create_unique_constraint(
            "uq_user_oidc_identity", ["oidc_issuer", "oidc_subject"]
        )


def downgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_constraint("uq_user_oidc_identity", type_="unique")
        batch_op.drop_column("oidc_subject")
        batch_op.drop_column("oidc_issuer")
