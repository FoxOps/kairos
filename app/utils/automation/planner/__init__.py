"""Pure automation planner - phase 2 of the shift/on-call automation
rework (see the audit that motivated it: preview/apply divergence,
non-atomic regeneration, rules bypassed by generation, rotation reset
per call, no group identity on generated rows, coverage-only
optimization). Lives beside the existing engine
(app/utils/automation/oncall_automation.py,
app/utils/automation/advanced_shift_automation.py,
app/services/automation_admin_service.py) with zero route wiring in
this phase - those keep running in production unchanged. See the
package's individual modules for the pure planning core, and
rule_resolution.py for the one non-pure adapter that bridges real
(DB-backed) config into a PlanningRequest."""

from app.utils.automation.planner.plan_schedule import plan_schedule
from app.utils.automation.planner.rule_resolution import (
    resolve_rotation_epoch,
    resolve_rules_for_groups,
)
from app.utils.automation.planner.types import (
    FairnessMetrics,
    LeaveSpan,
    OnCallSnapshot,
    PlanningRequest,
    ProposedOnCall,
    ProposedShift,
    ResolvedRules,
    RuleViolation,
    ScheduleDiffEntry,
    SchedulePlan,
    ShiftSnapshot,
    UnfilledRequirement,
    UserRef,
)

__all__ = [
    "plan_schedule",
    "resolve_rules_for_groups",
    "resolve_rotation_epoch",
    "PlanningRequest",
    "SchedulePlan",
    "UserRef",
    "LeaveSpan",
    "OnCallSnapshot",
    "ShiftSnapshot",
    "ResolvedRules",
    "ProposedOnCall",
    "ProposedShift",
    "UnfilledRequirement",
    "RuleViolation",
    "FairnessMetrics",
    "ScheduleDiffEntry",
]
