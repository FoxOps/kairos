"""add group_id to shift and on_call

Adds a nullable group_id FK to both tables, snapshotting each existing
row's CURRENT user.group_id at migration time (one-time backfill - the
first step of the shift/on-call automation rework audit's finding that
generated assignments carried no stable record of which group they were
generated for, only a live join through user.group_id, so moving a user
to a new group retroactively "moved" their historical assignments).
Pre-migration history reflects this point-in-time snapshot, not
necessarily the group the assignment was originally made under; every
row created from this point forward records its own group_id at
creation time instead (see the accompanying code change to
ShiftRepository.create/OnCallRepository.create and their callers, plus
ShiftService.api_update/OnCallService.api_update refreshing group_id on
reassignment).

Deliberately NOT added to uq_shift_user_date/uq_oncall_user_start_time:
group_id is descriptive metadata (a user has exactly one real group at
assignment time), not an independent uniqueness dimension - making the
constraint composite would incorrectly permit two rows for the same
user/date differing only by a stale group_id snapshot. A plain index is
added instead, for future direct group_id filtering without a join
through user.

Revision ID: 9c3e7a1f4b6d
Revises: b8e2f4a91c6d
Create Date: 2026-08-25 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9c3e7a1f4b6d"
down_revision = "b8e2f4a91c6d"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("shift", schema=None) as batch_op:
        batch_op.add_column(sa.Column("group_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_shift_group_id"), ["group_id"], unique=False
        )
        batch_op.create_foreign_key(
            "fk_shift_group_id_groups", "groups", ["group_id"], ["id"]
        )

    with op.batch_alter_table("on_call", schema=None) as batch_op:
        batch_op.add_column(sa.Column("group_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_on_call_group_id"), ["group_id"], unique=False
        )
        batch_op.create_foreign_key(
            "fk_on_call_group_id_groups", "groups", ["group_id"], ["id"]
        )

    # Built via SQLAlchemy Core (not raw sa.text SQL) so identifier
    # quoting of the "user" table name - a reserved word requiring
    # backticks on MySQL/MariaDB but double quotes on Postgres/SQLite -
    # is handled per-dialect by the query compiler instead of being
    # hardcoded for one engine, matching this app's 3-engine support.
    bind = op.get_bind()
    user_table = sa.table("user", sa.column("id"), sa.column("group_id"))
    shift_table = sa.table("shift", sa.column("user_id"), sa.column("group_id"))
    on_call_table = sa.table("on_call", sa.column("user_id"), sa.column("group_id"))

    bind.execute(
        shift_table.update().values(
            group_id=sa.select(user_table.c.group_id)
            .where(user_table.c.id == shift_table.c.user_id)
            .scalar_subquery()
        )
    )
    bind.execute(
        on_call_table.update().values(
            group_id=sa.select(user_table.c.group_id)
            .where(user_table.c.id == on_call_table.c.user_id)
            .scalar_subquery()
        )
    )


def downgrade():
    with op.batch_alter_table("on_call", schema=None) as batch_op:
        batch_op.drop_constraint("fk_on_call_group_id_groups", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_on_call_group_id"))
        batch_op.drop_column("group_id")

    with op.batch_alter_table("shift", schema=None) as batch_op:
        batch_op.drop_constraint("fk_shift_group_id_groups", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_shift_group_id"))
        batch_op.drop_column("group_id")
