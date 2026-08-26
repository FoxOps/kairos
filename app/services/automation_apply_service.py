"""
AutomationApplyService for Kairos.

Phase 5 of the automation engine rework: applies a pure SchedulePlan
(app/utils/automation/planner/) to the database inside one atomic
transaction. Not wired into any route yet (phase 6/7 do that) - this
service can be exercised directly (or by scripts/tests) but nothing in
production calls it.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from app import db
from app.models import OnCall, Shift, User
from app.models.generation_run import GenerationRun
from app.repositories.oncall_repository import OnCallRepository
from app.repositories.shift_repository import ShiftRepository
from app.services.audit_service import AuditService
from app.utils.automation.planner.types import SchedulePlan


@dataclass
class ApplyResult:
    success: bool
    generation_run_id: int | None = None
    oncalls_created: int = 0
    oncalls_deleted: int = 0
    oncalls_reassigned: int = 0
    shifts_created: int = 0
    shifts_deleted: int = 0
    shifts_reassigned: int = 0
    error: str | None = None
    # Only ever populated when apply_plan(atomic=False) - one
    # (ScheduleDiffEntry, error message) pair per diff entry whose own
    # SAVEPOINT rolled back. `success` stays True even when this is
    # non-empty (mirrors AdvancedShiftAutomation.rebalance_after_leave()'s
    # legacy contract: only a setup-step failure is a real failure -
    # a per-entry failure is the caller's own signal to notify about,
    # not an overall failure).
    failed_entries: list = field(default_factory=list)


def _find_oncall(user_id: int, day: date) -> OnCall | None:
    """The existing on-call for `user_id` starting somewhere on `day` -
    looked up by (user_id, calendar date of start_time) rather than an
    exact start_time match, since the caller only has a plain date
    (ScheduleDiffEntry.date), not the anchor hour."""
    day_start = datetime.combine(day, datetime.min.time())
    day_end = day_start + timedelta(days=1)
    return OnCall.query.filter(
        OnCall.user_id == user_id,
        OnCall.start_time >= day_start,
        OnCall.start_time < day_end,
    ).first()


def _find_shift(user_id: int, day: date) -> Shift | None:
    return Shift.query.filter_by(user_id=user_id, date=day).first()


class AutomationApplyService:
    """Applies a SchedulePlan. Unlike AuditService.log() (which
    swallows its own failures because a broken audit trail must never
    block the real action it describes), apply_plan's entire job is
    telling the caller whether the schedule actually changed - it
    never swallows an exception silently, it converts it into a typed
    ApplyResult.

    `atomic` (default True) selects between two isolation models:
    - `atomic=True` (generate_full/refresh_shifts, admin-button-
      triggered): one transaction for the whole plan, any exception
      rolls back everything, outcome is "applied" or "failed".
    - `atomic=False` (AdvancedShiftAutomation.rebalance_after_leave(),
      the automatic Leave-triggered rebalance - unattended, no admin
      retry button): each diff entry gets its own SAVEPOINT
      (`db.session.begin_nested()`), so one bad entry (e.g. a
      unique-constraint race) rolls back only that entry - every other
      entry's already-flushed change survives - recorded in
      `ApplyResult.failed_entries` instead of aborting the whole plan.
      A single final commit() persists everything that succeeded, plus
      one GenerationRun row with `outcome="partial"` if anything
      failed, `"applied"` otherwise. `success` stays True either way -
      matching rebalance_after_leave's own legacy contract, where only
      a setup-step failure (before any entry was even attempted) was
      ever a real failure, never a per-entry one."""

    @staticmethod
    def apply_plan(
        plan: SchedulePlan, actor: User | None = None, atomic: bool = True
    ) -> ApplyResult:
        if not plan.safe_to_apply:
            return ApplyResult(
                success=False,
                error="plan is not safe to apply: "
                + "; ".join(plan.safe_to_apply_reasons),
            )

        proposed_oncalls_by_key = {(o.friday, o.group_id): o for o in plan.oncalls}
        proposed_shifts_by_key = {(s.date, s.user_id): s for s in plan.shifts}

        result = ApplyResult(success=True)

        if atomic:
            try:
                for entry in plan.diff:
                    if entry.change_type == "unchanged":
                        continue

                    if entry.kind == "oncall":
                        AutomationApplyService._apply_oncall_entry(
                            entry, proposed_oncalls_by_key, result
                        )
                    else:
                        AutomationApplyService._apply_shift_entry(
                            entry, proposed_shifts_by_key, result
                        )

                run = GenerationRun(
                    start_date=plan.start_date,
                    end_date=plan.end_date,
                    input_fingerprint=plan.input_fingerprint,
                    outcome="applied",
                    actor_id=actor.id if actor else None,
                )
                db.session.add(run)
                db.session.commit()
            except (
                Exception
            ) as e:  # noqa: BLE001 - converted into a typed result, not swallowed
                db.session.rollback()
                run = GenerationRun(
                    start_date=plan.start_date,
                    end_date=plan.end_date,
                    input_fingerprint=plan.input_fingerprint,
                    outcome="failed",
                    error_detail=str(e),
                    actor_id=actor.id if actor else None,
                )
                db.session.add(run)
                db.session.commit()
                return ApplyResult(
                    success=False, generation_run_id=run.id, error=str(e)
                )
        else:
            entries_attempted = 0
            for entry in plan.diff:
                if entry.change_type == "unchanged":
                    continue
                entries_attempted += 1
                try:
                    with db.session.begin_nested():
                        if entry.kind == "oncall":
                            AutomationApplyService._apply_oncall_entry(
                                entry, proposed_oncalls_by_key, result
                            )
                        else:
                            AutomationApplyService._apply_shift_entry(
                                entry, proposed_shifts_by_key, result
                            )
                except Exception as e:  # noqa: BLE001 - recorded, not swallowed
                    result.failed_entries.append((entry, str(e)))

            outcome = "partial" if result.failed_entries else "applied"
            error_detail = (
                f"{len(result.failed_entries)}/{entries_attempted} entrées en échec"
                if result.failed_entries
                else None
            )
            run = GenerationRun(
                start_date=plan.start_date,
                end_date=plan.end_date,
                input_fingerprint=plan.input_fingerprint,
                outcome=outcome,
                error_detail=error_detail,
                actor_id=actor.id if actor else None,
            )
            db.session.add(run)
            db.session.commit()

        result.generation_run_id = run.id
        AuditService.log(
            "automation.apply",
            resource_type="GenerationRun",
            resource_id=run.id,
            actor=actor,
        )
        return result

    @staticmethod
    def _apply_oncall_entry(
        entry, proposed_oncalls_by_key, result: ApplyResult
    ) -> None:
        if entry.change_type in ("removed", "reassigned"):
            existing = _find_oncall(entry.published_user_id, entry.date)
            if existing is not None:
                OnCallRepository.delete(existing)
                result.oncalls_deleted += 1

        if entry.change_type in ("added", "reassigned"):
            proposed = proposed_oncalls_by_key[(entry.date, entry.group_id)]
            # group_id snapshots the ASSIGNED USER's real group at
            # apply time - not proposed.group_id, which is the
            # generation SCOPE (None in "shared" mode) - matching the
            # established meaning of this column everywhere else
            # (legacy engine, manual creation service layer): a
            # point-in-time snapshot of who was actually assigned,
            # never the pool they were drawn from.
            user = db.session.get(User, proposed.user_id)
            OnCallRepository.create(
                proposed.user_id,
                proposed.start_time,
                proposed.end_time,
                group_id=user.group_id if user else None,
            )
            if entry.change_type == "added":
                result.oncalls_created += 1
            else:
                result.oncalls_reassigned += 1

    @staticmethod
    def _apply_shift_entry(entry, proposed_shifts_by_key, result: ApplyResult) -> None:
        if entry.change_type in ("removed", "reassigned"):
            user_id = entry.published_user_id or entry.proposed_user_id
            existing = _find_shift(user_id, entry.date)
            if existing is not None:
                ShiftRepository.delete(existing)
                result.shifts_deleted += 1

        if entry.change_type in ("added", "reassigned"):
            proposed = proposed_shifts_by_key[(entry.date, entry.proposed_user_id)]
            user = db.session.get(User, proposed.user_id)
            ShiftRepository.create(
                proposed.user_id,
                proposed.shift_type_id,
                proposed.start_time,
                proposed.end_time,
                proposed.date,
                group_id=user.group_id if user else None,
            )
            if entry.change_type == "added":
                result.shifts_created += 1
            else:
                result.shifts_reassigned += 1
