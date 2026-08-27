"""Non-pure adapter layer: one of two files in the planner package
allowed to touch the DB / Flask request context (the other is
adapters.py, which calls into this module rather than resolving rules
itself). Wraps the existing AutomationRuleType.resolve() calls (rule
engine, unchanged) and AutomationConfig.get_rotation_epoch(), so the
pure planner core (plan_schedule.py and everything it calls) never
resolves anything itself - it only ever consumes the already-resolved
ResolvedRules/date values this module produces, placed on
PlanningRequest before plan_schedule() is called."""

from collections.abc import Iterable
from datetime import date

from app import db
from app.models import AutomationConfig, Group
from app.utils.automation.advanced_shift_automation import AdvancedShiftAutomation
from app.utils.automation.planner.types import ResolvedRules
from app.utils.automation.rules import (
    OnCallAnchorRule,
    OnCallShiftOverlapRule,
    OnCallSpacingRule,
    RestAfterOnCallRule,
    StaffingLimitsRule,
    WeekendDefinitionRule,
)


def _resolve_one(group: Group | None) -> ResolvedRules:
    anchor = OnCallAnchorRule.resolve(group=group)
    spacing = OnCallSpacingRule.resolve(group=group)
    weekend = WeekendDefinitionRule.resolve(group=group)
    staffing = StaffingLimitsRule.resolve(group=group)
    rest = RestAfterOnCallRule.resolve(group=group)
    overlap = OnCallShiftOverlapRule.resolve(group=group)
    # Reuses get_shift_type_for_slot() - the exact same resolution
    # (configured id, falling back to fetch-or-create by hours if the
    # id no longer exists) already used by the legacy generation path -
    # so the planner's role-slot ShiftTypes are never a second,
    # divergent source of truth.
    oncall_shift_type = AdvancedShiftAutomation.get_shift_type_for_slot(
        AdvancedShiftAutomation.SHIFT_13_21, group=group
    )
    rotation_shift_type = AdvancedShiftAutomation.get_shift_type_for_slot(
        AdvancedShiftAutomation.SHIFT_07_15, group=group
    )
    default_shift_type = AdvancedShiftAutomation.get_shift_type_for_slot(
        AdvancedShiftAutomation.SHIFT_09_17, group=group
    )

    return ResolvedRules(
        oncall_anchor_weekday=anchor["weekday"],
        oncall_anchor_start_hour=anchor["start_hour"],
        oncall_anchor_end_hour=anchor["end_hour"],
        oncall_spacing_weeks=spacing["min_spacing_weeks"],
        weekend_days=frozenset(weekend["weekend_days"]),
        staffing_limits={
            int(shift_type_id): max_value
            for shift_type_id, max_value in staffing.items()
        },
        rest_after_oncall_hours=rest["min_rest_hours"],
        oncall_shift_overlap_block=overlap["block"],
        oncall_shift_type_id=oncall_shift_type.id,
        oncall_slot_hours=(oncall_shift_type.start_hour, oncall_shift_type.end_hour),
        rotation_shift_type_id=rotation_shift_type.id,
        rotation_slot_hours=(
            rotation_shift_type.start_hour,
            rotation_shift_type.end_hour,
        ),
        default_shift_type_id=default_shift_type.id,
        default_slot_hours=(
            default_shift_type.start_hour,
            default_shift_type.end_hour,
        ),
    )


def resolve_rules_for_groups(
    group_ids: Iterable[int | None],
) -> dict[int | None, ResolvedRules]:
    """Resolves every rule type for each of `group_ids` (use None for
    the "shared"/org-wide scope) in one pass, ready to place on
    PlanningRequest.resolved_rules. Touches the DB (one Group lookup per
    non-None id, plus whatever AutomationRuleType.resolve() itself
    queries) - this is the boundary where that happens, exactly once,
    before plan_schedule() is ever called."""
    result: dict[int | None, ResolvedRules] = {}
    for group_id in group_ids:
        group = db.session.get(Group, group_id) if group_id is not None else None
        result[group_id] = _resolve_one(group)
    return result


def resolve_rotation_epoch() -> date:
    """The admin-configurable rotation-phase reference date (see
    app/utils/automation/planner/rotation.py) - org-wide, not
    per-group, same scope as AutomationConfig's rotation order."""
    return AutomationConfig.get_rotation_epoch()
