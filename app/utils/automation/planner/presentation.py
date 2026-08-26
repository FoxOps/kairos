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


def plan_messages(plan: SchedulePlan) -> tuple[list, list, list, list]:
    """Builds the same "[TAG] text" message strings the legacy engine
    produces (admin_automation_routes.py's own
    _classify_automation_message() already parses this exact
    convention) from a plan's unfilled/violations. Returns
    (oncall_messages, oncall_unfilled_dates, shift_messages,
    shift_unfilled_dates).

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

    for unfilled in plan.unfilled:
        if unfilled.reason_code == "locked_but_no_published_assignment":
            continue

        if unfilled.kind == "oncall_week":
            oncall_unfilled_dates.append(unfilled.date)
            oncall_messages.append(
                _(
                    "[WARN] Aucune astreinte générée pour le %(date)s "
                    "(aucun utilisateur ne respecte le délai légal entre "
                    "deux astreintes) - assignation manuelle nécessaire.",
                    date=unfilled.date.strftime("%d/%m/%Y"),
                )
            )
            continue

        shift_unfilled_dates.append(unfilled.date)
        shift_type = None
        if unfilled.detail:
            shift_type = db.session.get(ShiftType, int(unfilled.detail))
        label = shift_type.label if shift_type else unfilled.detail

        if unfilled.kind == "mandatory_shift":
            shift_messages.append(
                _(
                    "[ALERT] Créneau obligatoire non pourvu pour le "
                    "%(date)s : %(name)s.",
                    date=unfilled.date.strftime("%d/%m/%Y"),
                    name=label,
                )
            )
        else:  # staffing_min
            shift_messages.append(
                _(
                    "[WARN] Effectif minimum non atteint pour le "
                    "%(date)s : %(name)s.",
                    date=unfilled.date.strftime("%d/%m/%Y"),
                    name=label,
                )
            )

    # The only rule_type any planner module currently raises a
    # RuleViolation for is rest_after_oncall (shift_planner.py) -
    # always shift-scoped. A future rule type producing on-call-side
    # violations would need its own branch here.
    for violation in plan.violations:
        user = db.session.get(User, violation.user_id) if violation.user_id else None
        tag = "[ALERT]" if violation.severity == "hard_blocked" else "[WARN]"
        shift_messages.append(
            _(
                "%(tag)s %(name)s n'a pas pu être affecté au %(date)s : "
                "repos insuffisant après son astreinte.",
                tag=tag,
                name=user.name if user else _("Utilisateur inconnu"),
                date=violation.date.strftime("%d/%m/%Y"),
            )
        )

    return oncall_messages, oncall_unfilled_dates, shift_messages, shift_unfilled_dates
