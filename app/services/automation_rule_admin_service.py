"""
Automation rule admin service for Kairos.

One save_*() method per configurable automation rule type (see
app/utils/automation/rules/), each validating via that rule type's own
validate_params() before persisting through AutomationRule.set().
Mirrors SettingsService's per-section setter pattern: returns
error_message | None instead of raising, and every write is followed
by an audit trail entry.

Every save_*() accepts an optional `group` (a Group instance) -
omitted or None saves the organization-wide default, exactly as
before; passed, it saves that Group's own override instead, read back
via AutomationRule.resolve_params(rule_type, group=group)/
app/utils/automation/rules/*.py's own resolve(group=group). Only
meaningful once shift_scheduling_mode/oncall_scheduling_mode (see
SettingsService) is "per_group" for the relevant generation/validation
path - a Group override saved while a mode is still "shared" persists
but is never looked up until that mode is flipped.
"""

from app.models import AutomationRule
from app.services.audit_service import AuditService
from app.utils.automation.rules import RULE_TYPES

# Rule-type validate_params() errors (app/utils/automation/rules/*.py)
# are plain-English parameter-shape checks (e.g. "must be a
# non-negative integer"), not user-facing prose - closer to an API
# validation error than app copy. Deliberately not run through
# gettext, unlike every other user-facing string in this app.


def _save(rule_type: str, params: dict, group=None) -> str | None:
    errors = RULE_TYPES[rule_type].validate_params(params)
    if errors:
        return "; ".join(errors)
    AutomationRule.set(rule_type, params, group=group)
    details = f"{rule_type}={params}"
    if group is not None:
        details += f" group={group.name}"
    AuditService.log(
        "automation_rule.update",
        resource_type="AutomationRule",
        details=details,
    )
    return None


class AutomationRuleAdminService:
    """Admin-editable, DB-backed configurable automation rules."""

    @staticmethod
    def save_shift_slots(
        oncall_shift_type_id: int,
        rotation_shift_type_id: int,
        default_shift_type_id: int,
        group=None,
    ) -> str | None:
        return _save(
            "shift_slots",
            {
                "oncall_shift_type_id": oncall_shift_type_id,
                "rotation_shift_type_id": rotation_shift_type_id,
                "default_shift_type_id": default_shift_type_id,
            },
            group=group,
        )

    @staticmethod
    def save_weekend_definition(weekend_days: list[int], group=None) -> str | None:
        return _save("weekend_definition", {"weekend_days": weekend_days}, group=group)

    @staticmethod
    def save_oncall_spacing(min_spacing_weeks: int, group=None) -> str | None:
        return _save(
            "oncall_spacing", {"min_spacing_weeks": min_spacing_weeks}, group=group
        )

    @staticmethod
    def save_oncall_anchor(
        weekday: int, start_hour: int, end_hour: int, group=None
    ) -> str | None:
        return _save(
            "oncall_anchor",
            {"weekday": weekday, "start_hour": start_hour, "end_hour": end_hour},
            group=group,
        )

    @staticmethod
    def save_staffing_limits(
        limits: dict[int, int | None],
        group=None,
    ) -> str | None:
        """`limits`: {shift_type_id: max} - a missing/None value means
        no limit for that ShiftType."""
        params = {
            str(shift_type_id): max_value for shift_type_id, max_value in limits.items()
        }
        return _save("staffing_limits", params, group=group)

    @staticmethod
    def save_rest_after_oncall(min_rest_hours: int, group=None) -> str | None:
        return _save(
            "rest_after_oncall", {"min_rest_hours": min_rest_hours}, group=group
        )

    @staticmethod
    def save_oncall_shift_overlap(block: bool, group=None) -> str | None:
        return _save("oncall_shift_overlap", {"block": block}, group=group)
