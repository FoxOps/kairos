"""Top-level pure orchestrator - the phase 2 deliverable itself.

plan_schedule() performs zero database writes. Given the same
PlanningRequest, it always produces the same assignments/unfilled/
violations/diff/fairness/safety verdict - the property a future
apply-then-retry (phase 5) will depend on. The one field that is *not*
part of that determinism guarantee is SchedulePlan.generated_at (a
wall-clock timestamp, not deterministic by definition, and not part of
input_fingerprint either) - tests comparing two plans for equality
must exclude it.

On-calls are planned first, entirely in memory, and fed DIRECTLY into
shift planning via merge_oncall_fragments() - shift planning never
reads on-calls from the database. This is the structural fix for audit
defect #1 (preview computing on-call assignments in memory but then
reading real on-calls from the DB for the shift half of the same
preview, so the two could disagree)."""

import hashlib
import json
from dataclasses import fields, is_dataclass
from datetime import date, datetime, timezone

from app.utils.automation.planner.diff import compute_diff
from app.utils.automation.planner.fairness import compute_fairness_metrics
from app.utils.automation.planner.oncall_planner import (
    merge_oncall_fragments,
    plan_oncalls_for_scope,
)
from app.utils.automation.planner.shift_planner import plan_shifts_for_scope
from app.utils.automation.planner.types import (
    PlanningRequest,
    RuleViolation,
    ScheduleDiffEntry,
    SchedulePlan,
)


def _to_jsonable(obj):
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, frozenset):
        return sorted(_to_jsonable(x) for x in obj)
    if isinstance(obj, dict):
        return {
            str(k): _to_jsonable(v)
            for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))
        }
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(x) for x in obj]
    if is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _to_jsonable(getattr(obj, f.name)) for f in fields(obj)}
    return obj


def _fingerprint(request: PlanningRequest) -> str:
    """Deterministic regardless of dict/frozenset insertion order in the
    request (sorted before serializing) - two PlanningRequests with the
    same logical content always hash identically, not just two
    references to the exact same object."""
    payload = json.dumps(_to_jsonable(request), sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _evaluate_safety(
    violations: tuple[RuleViolation, ...],
    diff: tuple[ScheduleDiffEntry, ...],
    locked_oncalls: frozenset[tuple[date, int | None]],
    locked_shifts: frozenset[tuple[date, int]],
) -> tuple[bool, tuple[str, ...]]:
    """safe_to_apply is a defense-in-depth internal-consistency flag,
    NOT "coverage is complete" - an unfilled on-call week or an
    understaffed day is an expected, non-blocking planner output
    (see UnfilledRequirement), never reflected here. Only a
    "hard_blocked" RuleViolation counts below - a "warning" one (e.g.
    shift_planner.py's routine per-day rest_after_oncall exclusions,
    already self-mitigated via `continue` and surfaced to the admin as
    an ordinary message) is expected to fire regularly and must never
    abort an otherwise-fine multi-month apply (real production bug:
    it used to, via the wrong severity - any org with rest_after_oncall
    configured could never apply a generation run at all). False here
    means: a hard_blocked violation slipped through hard-constraint
    filtering (should be structurally impossible if the planner is
    wired correctly), or a locked slot appears in the diff as
    reassigned/removed (locked slots are excluded from the candidate
    pool entirely, so this should also be impossible in correctly-wired
    code) - a loud, typed signal instead of a silently wrong plan."""
    reasons: list[str] = []

    for violation in violations:
        if violation.severity == "hard_blocked":
            reasons.append(
                f"hard_blocked violation: {violation.rule_type} on "
                f"{violation.date} (user {violation.user_id})"
            )

    for entry in diff:
        if entry.change_type not in ("reassigned", "removed"):
            continue
        if entry.kind == "oncall" and (entry.date, entry.group_id) in locked_oncalls:
            reasons.append(
                f"locked oncall slot changed: {entry.date} group {entry.group_id}"
            )
        elif entry.kind == "shift":
            relevant_user = (
                entry.published_user_id
                if entry.published_user_id is not None
                else entry.proposed_user_id
            )
            if (
                relevant_user is not None
                and (
                    entry.date,
                    relevant_user,
                )
                in locked_shifts
            ):
                reasons.append(
                    f"locked shift changed: {entry.date} user {relevant_user}"
                )

    return (len(reasons) == 0, tuple(reasons))


def plan_schedule(request: PlanningRequest) -> SchedulePlan:
    oncall_fragments = {
        group_id: plan_oncalls_for_scope(
            start_date=request.start_date,
            end_date=request.end_date,
            group_id=group_id,
            rotation_order=request.rotation_order.get(group_id, ()),
            rotation_anchor_epoch=request.rotation_anchor_epoch,
            existing_oncalls=request.existing_oncalls,
            existing_leaves=request.existing_leaves,
            locked=request.locked_oncalls,
            published=request.published_oncalls,
            preferred=request.preferred_oncall_assignments,
            rules=request.resolved_rules[group_id],
        )
        for group_id in request.oncall_groups
    }

    # Merged in-memory, fed directly into shift planning below - never
    # through the database (see module docstring).
    proposed_oncalls_by_scope = merge_oncall_fragments(oncall_fragments)

    # Which keys in proposed_oncalls_by_scope hold a given shift scope's
    # on-call info - see plan_shifts_for_scope()'s own docstring for the
    # two real bugs this distinction fixes (shift "per_group" + oncall
    # "shared", and the reverse: shift "shared" + oncall "per_group").
    # Three cases:
    #   - oncall mode "shared": on-calls are proposed under scope None
    #     regardless of how many shift scopes exist -> (None,).
    #   - this shift scope is itself per-group (`group_id` is a real
    #     id): only that same group's on-call is relevant -> (group_id,).
    #   - this shift scope is "shared" (`group_id` is None) while
    #     oncall is "per_group": every oncall-eligible group can have
    #     its own concurrent on-call relevant to this one pooled shift
    #     scope -> every oncall group id.
    oncall_mode_is_shared = request.oncall_groups == (None,)
    shift_start_date = request.shift_start_date or request.start_date

    def _oncall_group_ids_for_shift_scope(
        shift_group_id: int | None,
    ) -> tuple[int | None, ...]:
        if oncall_mode_is_shared:
            return (None,)
        if shift_group_id is not None:
            return (shift_group_id,)
        return request.oncall_groups

    shift_fragments = {
        group_id: plan_shifts_for_scope(
            start_date=shift_start_date,
            end_date=request.end_date,
            group_id=group_id,
            oncall_group_ids=_oncall_group_ids_for_shift_scope(group_id),
            eligible_users=request.eligible_shift_users.get(group_id, ()),
            proposed_oncalls=proposed_oncalls_by_scope,
            existing_oncalls=request.existing_oncalls,
            existing_leaves=request.existing_leaves,
            locked=request.locked_shifts,
            published=request.published_shifts,
            rotation_order=request.rotation_order.get(group_id, ()),
            rotation_anchor_epoch=request.rotation_anchor_epoch,
            rules=request.resolved_rules[group_id],
        )
        for group_id in request.schedule_groups
    }

    oncalls = tuple(o for f in oncall_fragments.values() for o in f.proposed)
    shifts = tuple(s for f in shift_fragments.values() for s in f.proposed)
    unfilled = tuple(u for f in oncall_fragments.values() for u in f.unfilled) + tuple(
        u for f in shift_fragments.values() for u in f.unfilled
    )
    violations = tuple(v for f in shift_fragments.values() for v in f.violations)

    diff = compute_diff(
        oncalls, shifts, request.published_oncalls, request.published_shifts
    )
    fairness = compute_fairness_metrics(oncalls, shifts)
    safe_to_apply, safe_to_apply_reasons = _evaluate_safety(
        violations, diff, request.locked_oncalls, request.locked_shifts
    )

    return SchedulePlan(
        start_date=request.start_date,
        end_date=request.end_date,
        generated_at=datetime.now(timezone.utc),
        oncalls=oncalls,
        shifts=shifts,
        unfilled=unfilled,
        violations=violations,
        fairness=fairness,
        diff=diff,
        safe_to_apply=safe_to_apply,
        safe_to_apply_reasons=safe_to_apply_reasons,
        input_fingerprint=_fingerprint(request),
    )
