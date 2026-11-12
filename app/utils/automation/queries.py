"""DB-backed lookups shared by the automation planner's adapter layer,
the admin automation pages and manual shift/on-call validation.

Moved here unchanged from the legacy engine's classes
(OnCallAutomation.get_eligible_users/get_rotation_order/
detect_oncall_gaps/align_regeneration_start and
AdvancedShiftAutomation.get_users_in_schedule_groups) when that engine
was removed in 1.2.0 - same queries, same ordering, so the planner sees
exactly the same population as before."""

from datetime import date, datetime, timedelta

from app.models import Group, OnCall, User


def get_oncall_users(group: Group | None = None) -> list[User]:
    """Users in a group taking part in the on-call rotation, sorted by
    name. `group`: restricts to that one Group's members ("per_group"
    on-call scheduling mode) instead of pooling every eligible group."""
    query = User.query.join(Group).filter(Group.is_part_of_oncall.is_(True))
    if group is not None:
        query = query.filter(User.group_id == group.id)
    return query.order_by(User.name).all()


def get_schedule_users(group: Group | None = None) -> list[User]:
    """Users in a group taking part in the shift schedule. `group`:
    restricts to that one Group's members ("per_group" shift
    scheduling mode). Deliberately unsorted (DB order), exactly like
    the legacy helper this replaces - the planner's rule-7 fallback
    breaks ties by this order."""
    query = User.query.join(Group).filter(Group.is_part_of_schedule.is_(True))
    if group is not None:
        query = query.filter(User.group_id == group.id)
    return query.all()


def get_rotation_order(
    rotation_order_ids: list[int] | None = None, group: Group | None = None
) -> list[User]:
    """On-call-eligible users (see get_oncall_users()) in the configured
    rotation order: ids from `rotation_order_ids` first (ineligible ids
    silently dropped), then every remaining eligible user by name.
    Without `rotation_order_ids`, plain name order."""
    eligible_users = get_oncall_users(group=group)
    if not eligible_users or not rotation_order_ids:
        return eligible_users

    user_map = {user.id: user for user in eligible_users}
    ordered_users = [user_map[uid] for uid in rotation_order_ids if uid in user_map]
    ordered_users.extend(u for u in eligible_users if u.id not in rotation_order_ids)
    return ordered_users


def align_regeneration_start(start_date: date) -> date:
    """The start date of the on-call week straddling `start_date`, if
    one actually exists in the database - otherwise `start_date` itself.

    Regenerating from a mid-week `start_date` must also re-plan the
    on-call week already in progress that day, or the week is lost
    (an on-call starting Friday 21:00 ends the following Friday 07:00,
    so it always overlaps midnight of a later start date - a confirmed
    real-world instance: two consecutive weeks silently lost after a
    leave-triggered rebalance). Queries the DB rather than
    unconditionally backdating one week: backdating when nothing was
    ever assigned there would spend a candidate's 2-week spacing budget
    on a week nobody asked about (regression caught by
    tests/integration/test_admin_automation.py::
    test_regenerate_mode_replaces_assignment_with_a_real_conflict)."""
    start_midnight = datetime.combine(start_date, datetime.min.time())
    straddling = (
        OnCall.query.filter(
            OnCall.start_time < start_midnight,
            OnCall.end_time > start_midnight,
        )
        .order_by(OnCall.start_time.desc())
        .first()
    )
    return straddling.start_time.date() if straddling else start_date


def detect_oncall_gaps() -> list[date]:
    """On-call anchor dates with no on-call at all, strictly *between*
    the earliest and latest existing on-call - real gaps in an
    otherwise-generated schedule, not "not generated yet" future weeks.

    Surfaced proactively on the automation pages: an admin once ran
    "Combler les trous d'astreintes" with the page's default dates
    (starting today) and concluded the feature "did nothing" because
    the actual gap predated the selected range."""
    first_oncall = OnCall.query.order_by(OnCall.start_time.asc()).first()
    last_oncall = OnCall.query.order_by(OnCall.start_time.desc()).first()
    if not first_oncall or not last_oncall:
        return []

    covered = {oncall.start_time.date() for oncall in OnCall.query.all()}

    gaps = []
    current_friday = first_oncall.start_time.date() + timedelta(days=7)
    last_friday = last_oncall.start_time.date()
    while current_friday < last_friday:
        if current_friday not in covered:
            gaps.append(current_friday)
        current_friday += timedelta(days=7)
    return gaps
