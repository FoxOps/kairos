"""Infrastructure regression test (not a named acceptance scenario):
AvailabilityIndex.from_snapshots() must produce identical
has_oncall_conflict()/has_leave_conflict()/meets_spacing_constraint()
results as the pre-existing DB-backed __init__, given equivalent data -
a parity guard for the one additive change made to
oncall_automation.py's own module to support the pure planner. This is
the one planner test file that needs a real DB/app context, since it
exercises the DB-backed constructor directly for comparison."""

from datetime import date, datetime

from app.models import Leave, OnCall


def test_from_snapshots_matches_db_backed_constructor(test_app, test_user, test_group):
    from app import db
    from app.models import User
    from app.utils.automation.oncall_automation import AvailabilityIndex
    from app.utils.automation.planner.types import LeaveSpan, OnCallSnapshot

    other_user = User(
        name="Other",
        email="other@example.com",
        password_hash="x",
        group_id=test_group.id,
    )
    db.session.add(other_user)
    db.session.commit()

    oncall = OnCall(
        user_id=test_user.id,
        start_time=datetime(2026, 1, 2, 21, 0),
        end_time=datetime(2026, 1, 9, 7, 0),
    )
    leave = Leave(
        user_id=other_user.id,
        start_date=date(2026, 1, 5),
        end_date=date(2026, 1, 7),
    )
    db.session.add_all([oncall, leave])
    db.session.commit()

    user_ids = [test_user.id, other_user.id]
    db_index = AvailabilityIndex(user_ids, min_spacing_weeks=2)

    oncall_snapshots = tuple(
        OnCallSnapshot(
            user_id=o.user_id,
            group_id=None,
            start_time=o.start_time,
            end_time=o.end_time,
        )
        for o in OnCall.query.filter(OnCall.user_id.in_(user_ids)).all()
    )
    leave_snapshots = tuple(
        LeaveSpan(
            user_id=leave_row.user_id,
            start_date=leave_row.start_date,
            end_date=leave_row.end_date,
        )
        for leave_row in Leave.query.filter(Leave.user_id.in_(user_ids)).all()
    )
    snapshot_index = AvailabilityIndex.from_snapshots(
        oncall_snapshots, leave_snapshots, min_spacing_weeks=2
    )

    probe_start = datetime(2026, 1, 2, 21, 0)
    probe_end = datetime(2026, 1, 9, 7, 0)
    for user_id in user_ids:
        assert db_index.has_oncall_conflict(
            user_id, probe_start, probe_end
        ) == snapshot_index.has_oncall_conflict(user_id, probe_start, probe_end)
        assert db_index.has_leave_conflict(
            user_id, date(2026, 1, 5), date(2026, 1, 7)
        ) == snapshot_index.has_leave_conflict(
            user_id, date(2026, 1, 5), date(2026, 1, 7)
        )
        # A week 1 day after the existing on-call ends - inside the
        # 2-week spacing window, must fail on both.
        near_start = datetime(2026, 1, 9, 21, 0)
        near_end = datetime(2026, 1, 16, 7, 0)
        assert db_index.meets_spacing_constraint(
            user_id, near_start, near_end
        ) == snapshot_index.meets_spacing_constraint(user_id, near_start, near_end)
