"""
AutomationApplyService for Kairos.

Applies a pure SchedulePlan (app/utils/automation/planner/) to the
database - the single write path of every generation entry point
(AutomationAdminService.generate_full()/refresh_shifts()/
rebalance_after_leave()).

Stale-plan protection (audit F07): applies are serialized (process lock
plus a row lock on databases that support SELECT ... FOR UPDATE), and a
plan carrying a state_fingerprint is re-checked against a fresh rebuild
of its request right before any write - a leave, assignment or
population change since planning refuses the plan instead of applying
decisions computed against a schedule that no longer exists.
"""

import threading
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import cast

from sqlalchemy import update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError

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
    oncalls_updated: int = 0
    shifts_updated: int = 0
    error: str | None = None
    # True when the plan was refused because the schedule changed since
    # it was computed (audit F07) - the caller should replan.
    stale: bool = False
    # Only ever populated when apply_plan(atomic=False) - one
    # (ScheduleDiffEntry, error message) pair per diff entry whose own
    # SAVEPOINT rolled back. `success` stays True even when this is
    # non-empty (AutomationAdminService.rebalance_after_leave()'s
    # contract: only a setup-step failure is a real failure -
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


# One apply at a time per process (Gunicorn runs threads in one worker).
_APPLY_LOCK = threading.Lock()
_APPLY_LOCK_KEY = "schedule_apply_lock"


def _acquire_schedule_write_lock() -> None:
    """Cross-process serialization: a no-op UPDATE on a sentinel config
    row, as the first statement of a fresh transaction. That is a row
    lock on PostgreSQL/MySQL and the database-wide RESERVED write lock on
    SQLite, held until this transaction's commit/rollback - so the stale
    check below and the writes that follow it can't interleave with
    another worker's apply (a read-only SELECT ... FOR UPDATE would leave
    SQLite multi-worker deployments unprotected)."""
    from app.models import AutomationConfig

    def _touch() -> int:
        # An UPDATE always yields a CursorResult (rowcount); Session.execute()
        # is just typed with the generic Result.
        result = cast(
            CursorResult,
            db.session.execute(
                update(AutomationConfig)
                .where(AutomationConfig.config_key == _APPLY_LOCK_KEY)
                .values(config_value=AutomationConfig.config_value)
            ),
        )
        return result.rowcount

    if _touch():
        return
    # First apply ever: create the sentinel. Two processes racing here
    # both INSERT - the unique config_key makes one fail, which simply
    # re-selects the row the other created.
    try:
        db.session.add(AutomationConfig(config_key=_APPLY_LOCK_KEY, config_value="1"))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
    _touch()


def _stale_reason(plan: SchedulePlan) -> str | None:
    if not plan.state_fingerprint:
        return None
    from app.utils.automation.planner.adapters import build_planning_request
    from app.utils.automation.planner.plan_schedule import state_fingerprint

    fresh = build_planning_request(
        plan.start_date,
        plan.end_date,
        shift_start_date=plan.shift_start_date,
        restrict_to_group_id=plan.restrict_to_group_id,
    )
    if state_fingerprint(fresh) != plan.state_fingerprint:
        return (
            "stale plan: the schedule, leaves or eligible users changed "
            "since this plan was computed - replan before applying"
        )
    return None


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
    - `atomic=False` (AutomationAdminService.rebalance_after_leave(),
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

        with _APPLY_LOCK:
            # End the transaction the plan was built in (its only pending
            # writes are fallback ShiftType rows the plan itself refers
            # to), so the lock below is the first statement of a fresh
            # transaction, and drop every cached object: the stale check
            # must re-read the DB, not the session's identity map or a
            # REPEATABLE READ snapshot taken at planning time.
            try:
                db.session.commit()
                _acquire_schedule_write_lock()
                db.session.expire_all()
                stale = _stale_reason(plan)
            except Exception as e:  # noqa: BLE001 - converted into a typed result
                db.session.rollback()
                return ApplyResult(success=False, error=str(e))
            if stale is not None:
                db.session.rollback()
                run = GenerationRun(
                    start_date=plan.start_date,
                    end_date=plan.end_date,
                    input_fingerprint=plan.input_fingerprint,
                    outcome="failed",
                    error_detail=stale,
                    actor_id=actor.id if actor else None,
                )
                db.session.add(run)
                db.session.commit()
                return ApplyResult(
                    success=False, generation_run_id=run.id, error=stale, stale=True
                )
            return AutomationApplyService._apply_unlocked(plan, actor, atomic)

    @staticmethod
    def _apply_unlocked(plan: SchedulePlan, actor: User | None, atomic: bool):
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
        if entry.change_type == "updated":
            proposed = proposed_oncalls_by_key[(entry.date, entry.group_id)]
            existing = _find_oncall(proposed.user_id, entry.date)
            if existing is not None:
                existing.start_time = proposed.start_time
                existing.end_time = proposed.end_time
                db.session.flush()
                result.oncalls_updated += 1
            return

        if entry.change_type in ("removed", "reassigned"):
            existing = _find_oncall(entry.published_user_id, entry.date)
            if existing is not None:
                OnCallRepository.delete(existing)
                result.oncalls_deleted += 1
                # Real bug found in production: without flushing here,
                # this DELETE stays merely staged - when a later entry's
                # own lookup query (_find_oncall/_find_shift) triggers
                # SQLAlchemy's autoflush, the unit of work can batch
                # every pending INSERT before every pending DELETE
                # (no FK dependency forces otherwise for these unrelated
                # rows), so a same-day INSERT for a *different* user can
                # be attempted before this DELETE has actually run - see
                # _apply_shift_entry's identical fix below for the
                # concrete unique-constraint failure this caused.
                db.session.flush()

        if entry.change_type in ("added", "reassigned"):
            proposed = proposed_oncalls_by_key[(entry.date, entry.group_id)]
            # group_id snapshots the ASSIGNED USER's real group at
            # apply time - not proposed.group_id, which is the
            # generation SCOPE (None in "shared" mode) - matching the
            # established meaning of this column everywhere else
            # (manual creation service layer): a
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
        if entry.change_type == "updated":
            proposed = proposed_shifts_by_key[(entry.date, entry.proposed_user_id)]
            existing = _find_shift(proposed.user_id, entry.date)
            if existing is not None:
                existing.start_time = proposed.start_time
                existing.end_time = proposed.end_time
                db.session.flush()
                result.shifts_updated += 1
            return

        if entry.change_type in ("removed", "reassigned"):
            user_id = entry.published_user_id or entry.proposed_user_id
            existing = _find_shift(user_id, entry.date)
            if existing is not None:
                ShiftRepository.delete(existing)
                result.shifts_deleted += 1
                # Real bug found in production, surfaced by the rotation-
                # order fix ([[project-automation-engine-rework]]): a
                # "reassigned" shift entry has published_user_id ==
                # proposed_user_id (same user, only shift_type_id
                # changes - see diff.py's own docstring), so this
                # deletes the user's existing (user_id, date) row and
                # the block below creates a fresh one for that exact
                # same key. Without flushing here, the DELETE stays
                # merely staged - when regenerating a day where several
                # users are reassigned at once (now routine, since the
                # configured rotation order is always followed), a
                # later entry's own _find_shift() lookup triggers
                # SQLAlchemy's autoflush, which can batch every pending
                # INSERT before every pending DELETE (no FK dependency
                # forces otherwise for these unrelated rows) - one
                # user's still-undeleted old row then collides with
                # another's new INSERT under the (user_id, date) unique
                # constraint. Reproduced directly: 4 users reassigned on
                # the same day raised "UNIQUE constraint failed:
                # shift.user_id, shift.date" via autoflush before this
                # fix.
                db.session.flush()

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
