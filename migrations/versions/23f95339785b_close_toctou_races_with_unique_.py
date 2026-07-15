"""close TOCTOU races with unique constraints on shift and on_call

can_add_shift()/can_add_oncall() are check-then-insert: two concurrent
requests can both pass the application-level check before either one
commits, producing a duplicate shift (same user, same day) or a
duplicate on-call (same user, same week - start_time is always
constrained to Friday 21:00 by can_add_oncall). These unique
constraints close that race at the database level.

Leave doesn't get an equivalent constraint here: leave periods have no
fixed length/start pattern, so full range-overlap exclusion would need
a Postgres-only EXCLUDE USING gist constraint, not portable to SQLite
(this project's default and tested engine). Leave overlap stays an
application-level check only.

Any duplicate rows already in the database (a real consequence of the
race this migration closes) are deleted first, keeping the earliest
row (lowest id) of each duplicate group - otherwise creating the unique
constraint below would fail outright on an affected deployment.

Revision ID: 23f95339785b
Revises: da2c4dfc1024
Create Date: 2026-07-15 12:06:38.325318

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "23f95339785b"
down_revision = "da2c4dfc1024"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Keep the earliest row (lowest id) per (user_id, date)/
    # (user_id, start_time) duplicate group, delete the rest.
    conn.execute(sa.text("""
            DELETE FROM shift
            WHERE id NOT IN (
                SELECT MIN(id) FROM shift GROUP BY user_id, date
            )
            """))
    conn.execute(sa.text("""
            DELETE FROM on_call
            WHERE id NOT IN (
                SELECT MIN(id) FROM on_call GROUP BY user_id, start_time
            )
            """))

    with op.batch_alter_table("on_call", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_oncall_user_start_time", ["user_id", "start_time"]
        )

    with op.batch_alter_table("shift", schema=None) as batch_op:
        batch_op.create_unique_constraint("uq_shift_user_date", ["user_id", "date"])


def downgrade():
    with op.batch_alter_table("shift", schema=None) as batch_op:
        batch_op.drop_constraint("uq_shift_user_date", type_="unique")

    with op.batch_alter_table("on_call", schema=None) as batch_op:
        batch_op.drop_constraint("uq_oncall_user_start_time", type_="unique")
