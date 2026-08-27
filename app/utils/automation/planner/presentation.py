"""Translates a pure SchedulePlan into the legacy-shaped presentation
objects/messages every real-generation call site needs to hand back to
its own caller without changing any downstream template/route -
originally built inline in AutomationAdminService for the phase 6/7
generate_full()/refresh_shifts() cutovers, moved here (a neutral module
both app/services/ and app/utils/automation/ can import from) once
AdvancedShiftAutomation.rebalance_after_leave()'s own new-engine cutover
needed the exact same logic - app/utils/ must never import from
app/services/ (the reverse of this app's normal routes -> services ->
repositories/utils layering), so keeping this only on
AutomationAdminService was no longer an option.

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
    """Builds the same "[TAG] text" message strings the legacy engine
    produces (admin_automation_routes.py's own
    _classify_automation_message() already parses this exact
    convention) from a plan's unfilled/violations. Returns
    (oncall_messages, oncall_unfilled_dates, shift_messages,
    shift_unfilled_dates).

    Every message is aggregated - one line per (kind, shift type) or
    per violation rule_type, with a count and a date range - never one
    line per individual day. Real production bug: a multi-month
    generation run with a recurring gap (a mandatory slot missed every
    week, or - before shift_planner.py's own rest_after_oncall/"oncall"
    role_slot fix - a rest_after_oncall exclusion firing on literally
    every transition Friday) flooded the admin with one flash toast per
    occurrence, sometimes hundreds. AdvancedShiftAutomation.
    generate_full_schedule()/OnCallAutomation.generate_oncall_schedule()
    (the legacy engine) already solved this exact problem the same way
    (see their own docstrings) - this is that same fix, ported to the
    new planner's presentation layer, which had never had it. Full
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

    mandatory_gap_dates: dict = defaultdict(list)
    staffing_min_gap_dates: dict = defaultdict(list)

    for unfilled in plan.unfilled:
        if unfilled.reason_code == "locked_but_no_published_assignment":
            continue

        if unfilled.kind == "oncall_week":
            oncall_unfilled_dates.append(unfilled.date)
            continue

        shift_unfilled_dates.append(unfilled.date)
        shift_type = None
        if unfilled.detail:
            shift_type = db.session.get(ShiftType, int(unfilled.detail))
        label = shift_type.label if shift_type else unfilled.detail

        if unfilled.kind == "mandatory_shift":
            mandatory_gap_dates[label].append(unfilled.date)
        else:  # staffing_min
            staffing_min_gap_dates[label].append(unfilled.date)

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

    for label, dates in mandatory_gap_dates.items():
        count, start, end = _date_range_suffix(dates)
        shift_messages.append(
            _(
                '[ALERT] Créneau obligatoire "%(name)s" non pourvu à '
                "%(count)s reprises entre le %(start)s et le %(end)s.",
                name=label,
                count=count,
                start=start,
                end=end,
            )
        )
    for label, dates in staffing_min_gap_dates.items():
        count, start, end = _date_range_suffix(dates)
        shift_messages.append(
            _(
                '[WARN] Effectif minimum non atteint pour "%(name)s" à '
                "%(count)s reprises entre le %(start)s et le %(end)s.",
                name=label,
                count=count,
                start=start,
                end=end,
            )
        )

    # The only rule_type any planner module currently raises a
    # RuleViolation for is rest_after_oncall (shift_planner.py) -
    # always shift-scoped. A future rule type producing on-call-side
    # violations would need its own branch here.
    violation_dates_by_severity: dict = defaultdict(list)
    for violation in plan.violations:
        violation_dates_by_severity[violation.severity].append(violation.date)

    for severity, dates in violation_dates_by_severity.items():
        count, start, end = _date_range_suffix(dates)
        tag = "[ALERT]" if severity == "hard_blocked" else "[WARN]"
        shift_messages.append(
            _(
                "%(tag)s Repos insuffisant après astreinte : %(count)s "
                "shift(s) non affecté(s) entre le %(start)s et le "
                "%(end)s.",
                tag=tag,
                count=count,
                start=start,
                end=end,
            )
        )

    return oncall_messages, oncall_unfilled_dates, shift_messages, shift_unfilled_dates
