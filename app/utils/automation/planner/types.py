"""Value objects for the pure automation planner
(app/utils/automation/planner/).

Every dataclass here is frozen - a SchedulePlan is built once and never
mutated. This module has zero DB/Flask dependency and imports no
SQLAlchemy models: groups/shift types/users are referenced by plain
int ids, never ORM objects, so the planner core stays testable with
hand-built data and no app context. The (non-pure) adapter layer that
eventually builds a PlanningRequest from real data - rule_resolution.py
in this same package - is the only place that touches the DB/ORM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal

ChangeType = Literal["unchanged", "added", "removed", "reassigned"]

# ---------------------------------------------------------------------------
# Snapshot inputs - hand-buildable in tests, no DB access required.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UserRef:
    id: int
    name: str
    group_id: int | None


@dataclass(frozen=True)
class LeaveSpan:
    user_id: int
    start_date: date
    end_date: date


@dataclass(frozen=True)
class OnCallSnapshot:
    user_id: int
    group_id: int | None
    start_time: datetime
    end_time: datetime


@dataclass(frozen=True)
class ShiftSnapshot:
    user_id: int
    group_id: int | None
    shift_type_id: int
    date: date


@dataclass(frozen=True)
class ResolvedRules:
    """One group-scope's fully-resolved rule values - already pulled
    through AutomationRuleType.resolve(group=) by rule_resolution.py,
    never re-resolved inside the pure planner. Field names mirror each
    rule type's own params (see app/utils/automation/rules/)."""

    oncall_anchor_weekday: int
    oncall_anchor_start_hour: int
    oncall_anchor_end_hour: int
    oncall_spacing_weeks: int
    weekend_days: frozenset[int]
    staffing_limits: dict[int, dict[str, int | None]]
    mandatory_shift_type_ids: frozenset[int]
    rest_after_oncall_hours: int
    oncall_shift_overlap_block: bool
    # Each role slot's resolved ShiftType id plus its (start_hour,
    # end_hour) - resolved once by rule_resolution.py (which may create
    # a fallback ShiftType row, same as
    # AdvancedShiftAutomation.get_shift_type_for_slot()), so the pure
    # shift planner never needs its own ShiftType lookup to build a
    # ProposedShift's actual start_time/end_time.
    oncall_shift_type_id: int
    oncall_slot_hours: tuple[int, int]
    rotation_shift_type_id: int
    rotation_slot_hours: tuple[int, int]
    default_shift_type_id: int
    default_slot_hours: tuple[int, int]


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProposedOnCall:
    friday: date
    start_time: datetime
    end_time: datetime
    user_id: int
    group_id: int | None
    change_type: ChangeType
    explanation: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProposedShift:
    date: date
    user_id: int
    shift_type_id: int
    start_time: datetime
    end_time: datetime
    group_id: int | None
    role_slot: Literal["oncall", "rotation", "default"]
    change_type: ChangeType
    explanation: tuple[str, ...] = ()


@dataclass(frozen=True)
class UnfilledRequirement:
    kind: Literal["oncall_week", "mandatory_shift", "staffing_min"]
    date: date
    group_id: int | None
    reason_code: str
    detail: str = ""


@dataclass(frozen=True)
class RuleViolation:
    severity: Literal["hard_blocked", "warning"]
    rule_type: str
    group_id: int | None
    date: date
    user_id: int | None
    message: str


@dataclass(frozen=True)
class FairnessMetrics:
    oncall_count_by_user: dict[int, int] = field(default_factory=dict)
    oncall_count_stddev: float = 0.0
    undesirable_shift_count_by_user: dict[int, int] = field(default_factory=dict)
    undesirable_shift_stddev: float = 0.0
    rotation_adherence_ratio: float = 1.0


@dataclass(frozen=True)
class ScheduleDiffEntry:
    kind: Literal["oncall", "shift"]
    date: date
    group_id: int | None
    published_user_id: int | None
    proposed_user_id: int | None
    change_type: ChangeType


@dataclass(frozen=True)
class SchedulePlan:
    start_date: date
    end_date: date
    generated_at: datetime
    oncalls: tuple[ProposedOnCall, ...]
    shifts: tuple[ProposedShift, ...]
    unfilled: tuple[UnfilledRequirement, ...]
    violations: tuple[RuleViolation, ...]
    fairness: FairnessMetrics
    diff: tuple[ScheduleDiffEntry, ...]
    safe_to_apply: bool
    safe_to_apply_reasons: tuple[str, ...] = ()
    input_fingerprint: str = ""


# ---------------------------------------------------------------------------
# Request - the purity boundary. Rule resolution and rotation-epoch
# lookup (both DB-touching) happen once, outside plan_schedule(), and
# their results are placed here as plain data.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PlanningRequest:
    start_date: date
    end_date: date

    # (None,) means "shared" mode - one pooled scope covering everyone.
    # Independent of each other: shifts can be shared while on-call is
    # per_group, or the reverse.
    oncall_groups: tuple[int | None, ...]
    schedule_groups: tuple[int | None, ...]

    eligible_oncall_users: dict[int | None, tuple[UserRef, ...]]
    eligible_shift_users: dict[int | None, tuple[UserRef, ...]]
    rotation_order: dict[int | None, tuple[UserRef, ...]]

    # Absolute reference date for rotation-phase math (see rotation.py) -
    # request data, never looked up internally by the pure planner.
    rotation_anchor_epoch: date

    # Every on-call/leave relevant to spacing/conflict checks, not just
    # those inside [start_date, end_date] - spacing looks both forward
    # and backward in time (see AvailabilityIndex.meets_spacing_constraint).
    existing_oncalls: tuple[OnCallSnapshot, ...]
    existing_leaves: tuple[LeaveSpan, ...]

    # Keyed by (friday, group_id) / (date, user_id) - group_id in the
    # on-call key is the direct fix for concurrent per-group on-calls on
    # the same Friday silently overwriting each other (a single
    # {date: user_id} dict cannot represent that; a Shift is already
    # unique per (user_id, date) so no group dimension is needed there).
    published_oncalls: dict[tuple[date, int | None], int] = field(default_factory=dict)
    published_shifts: dict[tuple[date, int], int] = field(default_factory=dict)

    # Presence in these sets means "must not change" - excluded from the
    # candidate pool entirely (not merely preferred), so a correctly
    # wired planner can never propose reassigning/removing one.
    locked_oncalls: frozenset[tuple[date, int | None]] = field(
        default_factory=frozenset
    )
    locked_shifts: frozenset[tuple[date, int]] = field(default_factory=frozenset)

    # Minimal-perturbation seed for the on-call solver's fairness
    # tie-break - group-aware for the same reason published_oncalls is.
    preferred_oncall_assignments: dict[tuple[date, int | None], int] = field(
        default_factory=dict
    )

    resolved_rules: dict[int | None, ResolvedRules] = field(default_factory=dict)

    # On-call planning's own Friday search (oncall_planner._fridays_in_range)
    # legitimately needs `start_date` widened to the covering Friday when a
    # caller's literal requested start falls mid-on-call-week (see
    # OnCallAutomation.align_regeneration_start) - otherwise the boundary
    # week's already-published on-call would be misdiffed as "removed"
    # (present in published_oncalls via a true datetime-overlap fetch, but
    # never re-proposed since the Friday-date search starts too late to see
    # it). Shift planning must NOT inherit that same widening: a caller
    # asking to (re)generate shifts "from Monday" must never touch shift
    # rows on the preceding Fri/Sat/Sun just because the on-call side had to
    # look further back. `None` (every phase 4-6 call site) means "use
    # start_date for shifts too" - today's behavior, unchanged.
    shift_start_date: date | None = None
