"""
Automation rule admin service for Kairos.

One save_*() method per configurable automation rule type (see
app/utils/automation/rules/), each validating via that rule type's own
validate_params() before persisting through AutomationRule.set().
Mirrors SettingsService's per-section setter pattern: returns
error_message | None instead of raising, and every write is followed
by an audit trail entry.

All saves here are org-wide (group=None) - per-Group overrides aren't
exposed in the admin UI yet, since scheduling_mode (shared/per_group)
isn't wired into generation yet either (see SettingsService).
"""

from app.models import AutomationRule
from app.services.audit_service import AuditService
from app.utils.automation.rules import RULE_TYPES

# Rule-type validate_params() errors (app/utils/automation/rules/*.py)
# are plain-English parameter-shape checks (e.g. "must be a
# non-negative integer"), not user-facing prose - closer to an API
# validation error than app copy. Deliberately not run through
# gettext, unlike every other user-facing string in this app.


def _save(rule_type: str, params: dict) -> str | None:
    errors = RULE_TYPES[rule_type].validate_params(params)
    if errors:
        return "; ".join(errors)
    AutomationRule.set(rule_type, params)
    AuditService.log(
        "automation_rule.update",
        resource_type="AutomationRule",
        details=f"{rule_type}={params}",
    )
    return None


class AutomationRuleAdminService:
    """Admin-editable, DB-backed configurable automation rules."""

    @staticmethod
    def save_shift_slots(
        oncall_shift_type_id: int,
        rotation_shift_type_id: int,
        default_shift_type_id: int,
    ) -> str | None:
        return _save(
            "shift_slots",
            {
                "oncall_shift_type_id": oncall_shift_type_id,
                "rotation_shift_type_id": rotation_shift_type_id,
                "default_shift_type_id": default_shift_type_id,
            },
        )

    @staticmethod
    def save_weekend_definition(weekend_days: list[int]) -> str | None:
        return _save("weekend_definition", {"weekend_days": weekend_days})

    @staticmethod
    def save_oncall_spacing(min_spacing_weeks: int) -> str | None:
        return _save("oncall_spacing", {"min_spacing_weeks": min_spacing_weeks})

    @staticmethod
    def save_oncall_anchor(weekday: int, start_hour: int, end_hour: int) -> str | None:
        return _save(
            "oncall_anchor",
            {"weekday": weekday, "start_hour": start_hour, "end_hour": end_hour},
        )

    @staticmethod
    def save_staffing_limits(
        limits: dict[int, tuple[int | None, int | None]],
    ) -> str | None:
        """`limits`: {shift_type_id: (min, max)} - either bound may be
        None (no limit on that side)."""
        params = {
            str(shift_type_id): {"min": min_value, "max": max_value}
            for shift_type_id, (min_value, max_value) in limits.items()
        }
        return _save("staffing_limits", params)

    @staticmethod
    def save_mandatory_shift(shift_type_ids: list[int]) -> str | None:
        return _save("mandatory_shift", {"shift_type_ids": shift_type_ids})

    @staticmethod
    def save_rest_after_oncall(min_rest_hours: int) -> str | None:
        return _save("rest_after_oncall", {"min_rest_hours": min_rest_hours})

    @staticmethod
    def save_oncall_shift_overlap(block: bool) -> str | None:
        return _save("oncall_shift_overlap", {"block": block})
