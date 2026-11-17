"""Translates a pure SchedulePlan into the presentation objects/messages
every generation call site (AutomationAdminService.generate_full()/
refresh_shifts()/rebalance_after_leave()) hands back to its own caller
for the downstream templates/routes. Lives in app/utils/ (a neutral
module) so it stays importable without depending on app/services/.

Shared rather than duplicated so preview and real-apply results across
every call site render/notify identically for the exact same plan/apply
output - the whole point of phases 6/7 is eliminating preview/apply
divergence (audit defect #1), so a second, slightly-different copy of
this logic would be exactly the kind of drift that created it.
"""

from collections import defaultdict
from types import SimpleNamespace

from flask_babel import gettext as _

from app import db
from app.models import ShiftType, User
from app.utils.automation.planner.types import SchedulePlan


def plan_oncall_namespaces(plan: SchedulePlan) -> list:
    """`SimpleNamespace` stand-ins for full_dry_run.html's
    oncall.user.name/.start_time/.end_time reads - not real (transient)
    OnCall instances, whose `.user` lazy relationship silently resolves
    to None with no session, and which would otherwise pollute the real
    user's in-memory `.on_calls` backref collection if the relationship
    were assigned directly instead (see this function's own git history
    / the phase 6 commit for the two problems ruled out this way)."""
    return [
        SimpleNamespace(
            user=db.session.get(User, o.user_id),
            start_time=o.start_time,
            end_time=o.end_time,
        )
        for o in plan.oncalls
        if o.change_type != "unchanged"
    ]


def plan_shift_namespaces(plan: SchedulePlan) -> list:
    """Shift equivalent of plan_oncall_namespaces() above."""
    return [
        SimpleNamespace(
            user=db.session.get(User, s.user_id),
            shift_type=db.session.get(ShiftType, s.shift_type_id),
            date=s.date,
        )
        for s in plan.shifts
        if s.change_type != "unchanged"
    ]


def _date_range_suffix(dates: list) -> tuple[int, str, str]:
    return len(dates), min(dates).strftime("%d/%m/%Y"), max(dates).strftime("%d/%m/%Y")


def plan_messages(plan: SchedulePlan) -> tuple[list, list, list, list]:
    """Builds "[TAG] text" message strings (admin_automation_routes.py's own
    _classify_automation_message() already parses this exact
    convention) from a plan's unfilled/violations. Returns
    (oncall_messages, oncall_unfilled_dates, shift_messages,
    shift_unfilled_dates).

    Every message is aggregated - one line per (kind, shift type) or
    per violation rule_type, with a count and a date range - never one
    line per individual day. Real production bug: a multi-month
    generation run with a recurring gap (before shift_planner.py's own
    rest_after_oncall/"oncall" role_slot fix, a rest_after_oncall
    exclusion firing on literally every transition Friday) flooded the
    admin with one flash toast per occurrence, sometimes hundreds. Full
    per-day detail is not lost - it's what the calendar itself already
    shows, and _notify_shift_unfilled_if_any()/_notify_oncall_gap_if_any()
    (admin_automation_routes.py) still record every individual date on
    the notification page.

    Entries whose reason_code is "locked_but_no_published_assignment"
    are always skipped: that reason code only ever means a caller
    deliberately locked a slot that happens to have nothing published
    (refresh_shifts()'s oncall_mode="none"/"fill_gaps" widened locking,
    or rebalance_after_leave()'s own "don't touch on-calls at all
    unless the leave overlaps one" locking) - the caller already knows
    and chose that, so it must never surface as an admin-facing
    "unfilled"/"gap" notification."""
    oncall_messages: list = []
    oncall_unfilled_dates: list = []
    shift_messages: list = []
    shift_unfilled_dates: list = []

    staffing_max_gap_dates: dict = defaultdict(list)
    role_uncovered_dates: list = []

    for unfilled in plan.unfilled:
        if unfilled.reason_code == "locked_but_no_published_assignment":
            continue

        if unfilled.kind == "oncall_week":
            oncall_unfilled_dates.append(unfilled.date)
            continue

        if unfilled.kind == "no_available_user":
            shift_unfilled_dates.append(unfilled.date)
            continue

        if unfilled.kind == "role_uncovered":
            # Users were available, but nobody could take the rotation
            # slot without breaking a hard rule (shift_planner.py's
            # _repair_rotation_coverage) - a [WARN], like staffing_max.
            role_uncovered_dates.append(unfilled.date)
            continue

        # staffing_max: flash [WARN] only, never shift_unfilled_dates
        # (the "aucun utilisateur disponible" notification) - users WERE
        # available, the admin's own cap was reached (see
        # AppNotificationService.notify_admins_shift_unfilled()).
        shift_type = None
        if unfilled.detail:
            shift_type = db.session.get(ShiftType, int(unfilled.detail))
        label = shift_type.label if shift_type else unfilled.detail

        staffing_max_gap_dates[label].append(unfilled.date)

    if shift_unfilled_dates:
        count, start, end = _date_range_suffix(shift_unfilled_dates)
        shift_messages.append(
            _(
                "[WARN] Aucun utilisateur disponible (absences) : %(count)s "
                "jour(s) sans shift entre le %(start)s et le %(end)s - "
                "assignation manuelle nécessaire.",
                count=count,
                start=start,
                end=end,
            )
        )

    if oncall_unfilled_dates:
        count, start, end = _date_range_suffix(oncall_unfilled_dates)
        oncall_messages.append(
            _(
                "[WARN] %(count)s astreintes non générées entre le "
                "%(start)s et le %(end)s (délai légal non respecté) - "
                "assignation manuelle nécessaire.",
                count=count,
                start=start,
                end=end,
            )
        )

    for label, dates in staffing_max_gap_dates.items():
        count, start, end = _date_range_suffix(dates)
        shift_messages.append(
            _(
                '[WARN] Effectif maximum déjà atteint pour "%(name)s" à '
                "%(count)s reprises entre le %(start)s et le %(end)s - "
                "assignation manuelle nécessaire.",
                name=label,
                count=count,
                start=start,
                end=end,
            )
        )

    if role_uncovered_dates:
        count, start, end = _date_range_suffix(role_uncovered_dates)
        shift_messages.append(
            _(
                "[WARN] Créneau de rotation non couvert (aucun remplaçant "
                "ne respecte les règles) : %(count)s jour(s) entre le "
                "%(start)s et le %(end)s - assignation manuelle nécessaire.",
                count=count,
                start=start,
                end=end,
            )
        )

    # Both rule types shift_planner.py raises a RuleViolation for
    # (rest_after_oncall, oncall_shift_overlap) are shift-scoped. A
    # future rule type producing on-call-side violations would need its
    # own branch here.
    violation_dates: dict = defaultdict(list)
    for violation in plan.violations:
        violation_dates[(violation.rule_type, violation.severity)].append(
            violation.date
        )

    for (rule_type, severity), dates in violation_dates.items():
        count, start, end = _date_range_suffix(dates)
        tag = "[ALERT]" if severity == "hard_blocked" else "[WARN]"
        if rule_type == "oncall_shift_overlap":
            message = _(
                "%(tag)s Chevauchement astreinte/shift interdit : %(count)s "
                "shift(s) non affecté(s) entre le %(start)s et le "
                "%(end)s.",
                tag=tag,
                count=count,
                start=start,
                end=end,
            )
        else:
            message = _(
                "%(tag)s Repos insuffisant après astreinte : %(count)s "
                "shift(s) non affecté(s) entre le %(start)s et le "
                "%(end)s.",
                tag=tag,
                count=count,
                start=start,
                end=end,
            )
        shift_messages.append(message)

    return oncall_messages, oncall_unfilled_dates, shift_messages, shift_unfilled_dates
