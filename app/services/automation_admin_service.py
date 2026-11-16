"""
Automation admin service for Kairos.

Business logic supporting the admin automation screens: clearing an
existing period before regeneration and persisting the rotation order.
The actual schedule generation itself lives in the pure planner
(app.utils.automation.planner), applied by AutomationApplyService -
this service wraps the admin-specific glue around it (request shaping
per action, rotation order persistence, result presentation, leave
rebalance) rather than duplicating it.
"""

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta

from flask import has_request_context
from flask_babel import gettext as _
from flask_login import current_user

from app import db
from app.models import Leave, OnCall, User
from app.services.automation_apply_service import AutomationApplyService
from app.utils.automation import queries
from app.utils.automation.planner import build_planning_request, plan_schedule
from app.utils.automation.planner.presentation import (
    plan_messages,
    plan_oncall_namespaces,
    plan_shift_namespaces,
)
from app.utils.automation.planner.types import SchedulePlan


@dataclass
class RefreshResult:
    """Raw outcome of AutomationAdminService.refresh_shifts() below - the
    admin_automation_routes.py route turns this into flash messages/
    notifications, request-scoped concerns that don't belong in a
    service."""

    oncalls_deleted: int = 0
    oncall_messages: list = field(default_factory=list)
    oncall_messages_category: str = "info"
    oncall_unfilled_dates: list = field(default_factory=list)
    shifts_deleted: int = 0
    shifts: list = field(default_factory=list)
    shift_messages: list = field(default_factory=list)
    shift_unfilled_dates: list = field(default_factory=list)


@dataclass
class GenerateResult:
    """Raw outcome of AutomationAdminService.generate_full() below - same
    flash/notify split as RefreshResult above."""

    dry_run: bool = False
    oncalls_deleted: int = 0
    shifts_deleted: int = 0
    oncalls: list = field(default_factory=list)
    oncall_messages: list = field(default_factory=list)
    oncall_unfilled_dates: list = field(default_factory=list)
    shifts: list = field(default_factory=list)
    shift_messages: list = field(default_factory=list)
    shift_unfilled_dates: list = field(default_factory=list)


class AutomationAdminService:
    """Supporting business logic for the admin automation screens."""

    @staticmethod
    def parse_rotation_order_from_form(form) -> list[int]:
        """Extract the rotation order from the `rotation_order_{user_id}`
        (position) / `include_{user_id}` fields."""
        user_data = []
        for key, value in form.items():
            if key.startswith("rotation_order_"):
                user_id = int(key.replace("rotation_order_", ""))
                position = int(value)
                include = form.get(f"include_{user_id}", "0") == "1"
                user_data.append(
                    {"user_id": user_id, "position": position, "include": include}
                )

        user_data_sorted = sorted(user_data, key=lambda u: u["position"])
        return [u["user_id"] for u in user_data_sorted if u["include"]]

    @staticmethod
    def parse_rotation_exclusions_from_form(form) -> list[int]:
        """Users listed on the rotation form (`rotation_order_{id}`) whose
        "Inclure" box is unticked - excluded from on-call rotation, not
        just moved to the end (audit F13)."""
        return [
            int(key.replace("rotation_order_", ""))
            for key in form.keys()
            if key.startswith("rotation_order_")
            and form.get(f"include_{key.replace('rotation_order_', '')}", "0") != "1"
        ]

    @staticmethod
    def save_rotation_order(
        rotation_order_ids: list[int],
        reference_date: date | None = None,
        excluded_ids: list[int] | None = None,
    ) -> str | None:
        """Returns error_message, or None on success. Called both by the
        explicit "Sauvegarder l'ordre" action AND by generate_full()
        below on every "generate"/"dry_run" call - real bug found in
        production: the new engine's rotation order is only ever read
        from AutomationConfig (never from whatever the admin currently
        has configured/checked on the same generation form), so
        clicking "Générer" without a separate, easy-to-miss prior
        "Sauvegarder l'ordre" click silently fell back to alphabetical
        order - the admin's own configured order was never actually
        used. Persisting here on every generate/dry_run call keeps
        AutomationConfig always in sync with what's visibly on screen.

        Always resets AutomationConfig's rotation epoch to
        `reference_date` (default: today), on every call - a second real
        bug found in production: with the epoch left untouched forever,
        the rotation phase stayed pinned to
        AutomationConfig.FALLBACK_ROTATION_EPOCH (a fixed date from year
        2000), so the first user in a freshly configured rotation was
        essentially never the first one actually put on-call (whichever
        position `(next_anchor_date - epoch).days // 7 % len(order)`
        landed on, unrelated to the order an admin configured). Resetting
        epoch to `reference_date` makes the *next* anchor date on/after
        it (always within 0-6 days, whatever weekday it falls on) land on
        offset 0, i.e. rotation_order[0] - matching the "the order I
        configured should start applying from here" expectation.

        `reference_date` defaults to `date.today()` for the explicit
        "Sauvegarder l'ordre" action (`app/routes/admin_automation_routes.py`,
        no generation window involved - "now" is the only sensible
        reference). generate_full() below instead passes its own
        `start_date` explicitly - a second real bug found in production:
        using `date.today()` unconditionally here made rotation_order[0]
        land on the window being generated only when that window
        happened to start near the real wall-clock date; a dry-run
        preview or a backfill for a period far from today (or a test
        suite with fixed dates - see
        TestGenerateFullPersistsRotationOrder in
        tests/integration/test_automation_dry_run_cutover.py, which is
        exactly how this was caught) silently landed on an unrelated
        offset instead, unrelated to what was actually being generated.
        The configured order must be authoritative for *the window being
        generated*, not for whatever real time the button happened to be
        clicked at.

        This used to only reset the epoch when the order's *content*
        changed, to avoid re-shuffling an already-running rotation's
        phase on a same-order regenerate (rotation.py's module
        docstring, defect #4). Removed after a real production report:
        the admin's own order was correctly saved and correctly read,
        but the *first pick* still didn't match rotation_order[0]
        because the calendar had been cleared (for testing) without the
        order itself changing, so the epoch - set days earlier - had
        already drifted the offset away from 0 by elapsed time alone.
        The user's explicit call: the configured order must always be
        authoritative for non-locked weeks, full stop, even at the cost
        of the old "same Friday always maps to the same offset
        regardless of which call computed it" guarantee for two
        *overlapping* generate calls made on different days with an
        unchanged order - see [[project-automation-engine-rework]]."""
        try:
            from app.models import AutomationConfig

            # commit=False on both writes, one db.session.commit() at
            # the end: epoch and order must move together (rotation
            # phase math depends on both agreeing) - found during 1.1.1
            # release QA that AutomationConfig.set_config()'s own
            # per-call auto-commit meant a failure on the second write
            # left the epoch durably persisted without its matching
            # order.
            AutomationConfig.set_rotation_epoch(
                reference_date or date.today(), commit=False
            )
            AutomationConfig.set_rotation_order(rotation_order_ids, commit=False)
            # `excluded_ids=None` (callers that don't post the form) keeps
            # the persisted exclusion list as-is.
            if excluded_ids is not None:
                AutomationConfig.set_rotation_excluded(
                    sorted(set(excluded_ids) - set(rotation_order_ids)), commit=False
                )
            db.session.commit()
            return None
        except Exception as e:
            db.session.rollback()
            return str(e)

    @staticmethod
    def get_rotation_order() -> list[int] | None:
        try:
            from app.models import AutomationConfig

            return AutomationConfig.get_rotation_order()
        except Exception:
            return None

    @staticmethod
    def refresh_shifts(
        start_date: date, end_date: date, oncall_mode: str = "none"
    ) -> RefreshResult:
        """Business logic for the "refresh_shifts" action of
        admin_automation_routes.py::automation_full() - shifts-only
        recomputation, optionally also touching on-calls first depending
        on oncall_mode ("none"/"fill_gaps"/"regenerate", see that
        route's own docstring and _refresh_shifts_plan() below)."""
        return AutomationAdminService._refresh_shifts_plan(
            start_date, end_date, oncall_mode
        )

    @staticmethod
    def generate_full(
        start_date: date,
        end_date: date,
        rotation_order_ids: list[int],
        dry_run: bool,
        excluded_ids: list[int] | None = None,
    ) -> GenerateResult:
        """Business logic for the "generate"/"dry_run" actions of
        admin_automation_routes.py::automation_full() - full on-calls +
        shifts (re)generation for the period. Shared by both actions
        since they build the exact same plan (_build_plan()), dry_run
        only controlling whether it gets applied.

        The planner's rotation order is only ever read from
        AutomationConfig.get_rotation_order() (see
        AutomationRuleAdminService/save_order) - so this call always
        persists `rotation_order_ids` (via save_rotation_order(), same
        as the explicit "Sauvegarder l'ordre" action) before building
        the plan, real bug found in production: without this, whatever
        the admin currently has checked/ordered on the generation form
        itself was silently ignored by the planner unless a
        separate, easy-to-miss "Sauvegarder l'ordre" click had already
        happened first - AutomationConfig could (and did, in
        production) stay empty forever, silently falling back to
        alphabetical order regardless of what the admin configured.

        Passes `reference_date=start_date` to save_rotation_order() -
        real bug found in production (and by a test suite run on a date
        far from the fixed dates its own tests use, see
        TestGenerateFullPersistsRotationOrder): the default
        `reference_date=date.today()` only makes rotation_order[0] land
        on this call's own generation window when that window happens to
        start near the real wall-clock date. Passing start_date makes the
        window's own first anchor deterministically get offset 0,
        regardless of when the call actually runs - see
        save_rotation_order()'s own docstring for the full reasoning.

        A dry run persists nothing (audit F14): it plans with the form's
        order/exclusions and the epoch a real run would set, passed as
        request overrides - so a preview of some other period can no
        longer shift the rotation phase later refreshes/rebalances use.
        A real run persists first and aborts if that save fails, rather
        than generating with a stale order."""
        if dry_run:
            plan = AutomationAdminService._build_plan(
                start_date,
                end_date,
                rotation_order_override=rotation_order_ids,
                rotation_excluded_override=excluded_ids,
                rotation_epoch_override=start_date,
            )
            return AutomationAdminService._generate_result_from_plan(plan, dry_run=True)

        error = AutomationAdminService.save_rotation_order(
            rotation_order_ids, reference_date=start_date, excluded_ids=excluded_ids
        )
        if error is not None:
            raise RuntimeError(
                _(
                    "Impossible d'enregistrer l'ordre de rotation, génération "
                    "annulée : %(error)s",
                    error=error,
                )
            )

        return AutomationAdminService._generate_full_apply(start_date, end_date)

    @staticmethod
    def _build_plan(
        start_date: date, end_date: date, **rotation_overrides
    ) -> SchedulePlan:
        """Shared by generate_full()'s preview branch and
        _generate_full_apply() below, so the preview an admin sees
        and what "Générer" actually applies are always built from the
        exact same request-shaping - the whole point of the planner is
        eliminating preview/apply divergence (audit defect #1), so this
        must never fork into two slightly-different code paths.

        oncall_regen_start widens the on-call side's Friday search to
        the covering Friday when start_date falls mid-week (see
        queries.align_regeneration_start); shift_start_date
        keeps the literal caller-requested start_date for shift planning
        - see PlanningRequest.shift_start_date's own docstring for why
        the two must NOT share the same effective start."""
        oncall_regen_start = queries.align_regeneration_start(start_date)
        request = build_planning_request(
            oncall_regen_start,
            end_date,
            shift_start_date=start_date,
            **rotation_overrides,
        )
        return plan_schedule(request)

    @staticmethod
    def _current_actor() -> User | None:
        return (
            current_user
            if has_request_context() and current_user.is_authenticated
            else None
        )

    @staticmethod
    def _generate_full_apply(start_date: date, end_date: date) -> GenerateResult:
        """Real (dry_run=False) generation: the planner's plan applied
        via AutomationApplyService.apply_plan(). Raises on an unsuccessful apply (rather than returning a result
        with the failure silently absorbed) so
        admin_automation_routes.py's existing `except Exception as e:
        flash(...)` handling surfaces it exactly like any other
        generation failure - no route changes needed."""
        plan = AutomationAdminService._build_plan(start_date, end_date)
        apply_result = AutomationApplyService.apply_plan(
            plan, actor=AutomationAdminService._current_actor()
        )
        if not apply_result.success:
            raise RuntimeError(apply_result.error or "apply_plan failed")

        return AutomationAdminService._generate_result_from_plan(
            plan,
            dry_run=False,
            oncalls_deleted=apply_result.oncalls_deleted,
            shifts_deleted=apply_result.shifts_deleted,
        )

    @staticmethod
    def _generate_result_from_plan(
        plan: SchedulePlan,
        dry_run: bool,
        oncalls_deleted: int = 0,
        shifts_deleted: int = 0,
    ) -> GenerateResult:
        """Presentation shim: translates a pure SchedulePlan into the
        GenerateResult shape admin_automation_routes.py's
        automation_full() and full_dry_run.html consume. Used both for
        the dry_run preview (oncalls_deleted/shifts_deleted always 0 - a
        preview never deletes anything) and, once applied, for the real
        result (oncalls_deleted/shifts_deleted come from the matching
        ApplyResult) - see _generate_full_apply() above.

        `result.oncalls`/`result.shifts` hold plain `SimpleNamespace`
        objects, NOT real OnCall/Shift ORM instances - full_dry_run.html
        only ever reads oncall.user.name/.start_time/.end_time and
        shift.date/.shift_type.label/.user.name (duck-typed, Jinja does
        not care about the Python type), so a lightweight stand-in
        exposing exactly those attributes renders identically with none
        of the risk a real (if unpersisted) ORM instance would carry.

        A real `OnCall(user_id=..., ...)` / `Shift(...)` was tried
        first and rejected after direct testing showed two problems:
        (1) a transient instance has no session of its own, so its
        `.user`/`.shift_type` lazy relationship cannot run a query and
        silently resolves to None; (2) fixing that by assigning the
        already-fetched User/ShiftType onto the relationship
        (`oncall.user = user`) does NOT risk the transient object being
        persisted (SQLAlchemy declines the implicit session-add with a
        warning) - but it DOES populate the *other* side of that
        bidirectional backref, silently appending the fake preview
        object into the real, persistent user's/shift_type's own
        `.shifts`/`.on_calls` in-memory collection for the rest of the
        request. Anything else in the same request later reading
        `user.shifts` (e.g. a shared layout widget) would see the fake
        row mixed in. `SimpleNamespace` has no relationships to
        pollute, sidestepping both problems entirely. Only rows with
        change_type != "unchanged" are included (only slots actually
        being assigned, never untouched rows).
        """
        result = GenerateResult(
            dry_run=dry_run,
            oncalls_deleted=oncalls_deleted,
            shifts_deleted=shifts_deleted,
        )
        result.oncalls = plan_oncall_namespaces(plan)
        result.shifts = plan_shift_namespaces(plan)
        (
            result.oncall_messages,
            result.oncall_unfilled_dates,
            result.shift_messages,
            result.shift_unfilled_dates,
        ) = plan_messages(plan)
        return result

    @staticmethod
    def _iter_dates(start: date, end: date):
        current = start
        while current <= end:
            yield current
            current += timedelta(days=1)

    @staticmethod
    def _refresh_shifts_plan(
        start_date: date, end_date: date, oncall_mode: str
    ) -> RefreshResult:
        """refresh_shifts()'s planning. Always plans over the exact same
        [oncall_regen_start, end_date] / shift_start_date=start_date
        request-shaping as generate_full() (see
        _build_plan()'s docstring) - oncall_mode then adds an
        EXTRA, purely additive lock on top of the request's own
        DB-`locked`-column-derived locked_oncalls, expressing
        each mode as a request-shaping choice rather than new
        planner-core logic:

        - "none": every (date, scope) in the window gets locked, whether
          or not anything is currently published there - on-calls are
          left completely untouched ("shifts recomputed from whatever
          on-calls already exist, even manually modified ones"). A locked date with
          nothing published produces an UnfilledRequirement tagged
          "locked_but_no_published_assignment", which plan_messages()
          (app/utils/automation/planner/presentation.py) always filters
          out - "none" mode must never surface an
          on-call gap it was never asked to fill.
        - "fill_gaps": only dates that already have a published
          assignment are locked (frozenset(request.published_oncalls) -
          the two are the same set by construction), so an existing
          on-call can never be reassigned but a genuinely empty Friday
          still flows through normal solving and gets filled.
        - "regenerate": no extra locking - a full, unlocked re-solve of
          on-calls over the (aligned) window, identical to
          generate_full()'s own on-call planning.

        Shift planning itself is never locked in any of the three modes
        (locked_shifts stays whatever the request's own DB-column-derived
        value already is) - refresh_shifts always recomputes shifts,
        that is the one thing every mode has in common."""
        oncall_regen_start = queries.align_regeneration_start(start_date)
        request = build_planning_request(
            oncall_regen_start, end_date, shift_start_date=start_date
        )

        if oncall_mode == "none":
            extra_locked = frozenset(
                (day, group_id)
                for group_id in request.oncall_groups
                for day in AutomationAdminService._iter_dates(
                    oncall_regen_start, end_date
                )
            )
            request = replace(
                request, locked_oncalls=request.locked_oncalls | extra_locked
            )
            oncall_messages_category = "info"
        elif oncall_mode == "fill_gaps":
            extra_locked = frozenset(request.published_oncalls.keys())
            request = replace(
                request, locked_oncalls=request.locked_oncalls | extra_locked
            )
            oncall_messages_category = "info"
        else:  # "regenerate"
            oncall_messages_category = "danger"

        plan = plan_schedule(request)
        apply_result = AutomationApplyService.apply_plan(
            plan, actor=AutomationAdminService._current_actor()
        )
        if not apply_result.success:
            raise RuntimeError(apply_result.error or "apply_plan failed")

        result = RefreshResult(
            oncalls_deleted=apply_result.oncalls_deleted,
            shifts_deleted=apply_result.shifts_deleted,
            oncall_messages_category=oncall_messages_category,
        )
        result.shifts = plan_shift_namespaces(plan)
        (
            result.oncall_messages,
            result.oncall_unfilled_dates,
            result.shift_messages,
            result.shift_unfilled_dates,
        ) = plan_messages(plan)
        return result

    @staticmethod
    def _leave_rebalance_window(leave: Leave) -> tuple[date, date, list]:
        """Read-only: the on-calls overlapping `leave`, and the shift
        regeneration window they imply.

        Returns (shift_period_start, shift_period_end,
        overlapping_oncalls) - `overlapping_oncalls` empty means the
        leave doesn't overlap any on-call at all: no on-call
        regeneration is needed, and shift_period_start/end just span
        the leave's own dates."""
        overlapping_oncalls = OnCall.query.filter(
            OnCall.user_id == leave.user_id,
            OnCall.start_time
            < datetime.combine(leave.end_date + timedelta(days=1), datetime.min.time()),
            OnCall.end_time > datetime.combine(leave.start_date, datetime.min.time()),
        ).all()

        shift_period_start = leave.start_date
        shift_period_end = leave.end_date

        if overlapping_oncalls:
            # Find the period to cover: from the first Friday before
            # the leave to the last Friday after the leave ends + 30
            # days (to cover the whole on-call).
            first_friday = leave.start_date
            while first_friday.weekday() != 4:  # 4 = Friday
                first_friday -= timedelta(days=1)

            last_friday = leave.end_date
            while last_friday.weekday() != 4:
                last_friday += timedelta(days=1)

            shift_period_start = first_friday - timedelta(days=30)
            shift_period_end = last_friday + timedelta(days=30)

        return shift_period_start, shift_period_end, overlapping_oncalls

    @staticmethod
    def rebalance_after_leave(
        leave: Leave,
    ) -> tuple[list, list, list, list, list, list]:
        """Rebalance shifts and on-calls after a leave is added/modified/
        deleted (LeaveService calls this right after the leave's own
        commit). Leaves take priority: overlapping shifts and on-calls
        are re-planned around them.

        Returns (regenerated_shifts, messages, unfilled_oncall_dates,
        failed_shift_dates, failed_oncall_period, unfilled_shift_dates):
        regenerated_shifts/messages as for generate_full();
        unfilled_*_dates feed the admin "gap" notifications;
        failed_shift_dates/failed_oncall_period list what a per-entry
        apply failure left untouched (failed_oncall_period is at most
        one [start, end] pair per call).

        `restrict_to_group_id=leave.user.group_id` scopes planning to
        the leave owner's own Group - a no-op when
        scheduling mode is "shared" (build_planning_request only
        narrows under "per_group"), so a leave never triggers replanning
        for every other unrelated group's schedule.

        On-calls are only ever replanned when the leave actually
        overlaps one - achieved by fully locking every (date, scope) in
        the window when there's nothing to regenerate (same "none" trick
        as _refresh_shifts_plan()'s oncall_mode="none"), so on-call
        planning becomes a structural no-op instead of a second code
        path to keep in sync.

        apply_plan(atomic=False) gives each diff entry its own
        SAVEPOINT - one bad entry (e.g. a unique-constraint race on one
        day) doesn't lose everything else. failed_entries (per-entry
        (ScheduleDiffEntry, error) pairs) are translated back into
        failed_shift_dates/failed_oncall_period for LeaveService's
        notifications."""
        shift_period_start, shift_period_end, overlapping_oncalls = (
            AutomationAdminService._leave_rebalance_window(leave)
        )

        if overlapping_oncalls:
            oncall_window_start = queries.align_regeneration_start(shift_period_start)
        else:
            oncall_window_start = shift_period_start

        request = build_planning_request(
            oncall_window_start,
            shift_period_end,
            shift_start_date=shift_period_start,
            restrict_to_group_id=leave.user.group_id,
        )

        if not overlapping_oncalls:
            all_dates = []
            current = oncall_window_start
            while current <= shift_period_end:
                all_dates.append(current)
                current += timedelta(days=1)
            extra_locked = frozenset(
                (day, scope) for scope in request.oncall_groups for day in all_dates
            )
            request = replace(
                request, locked_oncalls=request.locked_oncalls | extra_locked
            )

        plan = plan_schedule(request)
        apply_result = AutomationApplyService.apply_plan(plan, actor=None, atomic=False)

        regenerated_shifts = plan_shift_namespaces(plan)
        (
            oncall_messages,
            unfilled_oncall_dates,
            shift_messages,
            unfilled_shift_dates,
        ) = plan_messages(plan)
        messages = oncall_messages + shift_messages

        failed_shift_dates: list = []
        failed_oncall_period: list = []
        for entry, error in apply_result.failed_entries:
            if entry.kind == "shift":
                failed_shift_dates.append(entry.date)
                messages.append(
                    _(
                        "[ERROR] Échec de la régénération du %(date)s : "
                        "%(error)s - ce jour n'a pas été modifié, "
                        "action manuelle nécessaire",
                        date=entry.date.strftime("%d/%m/%Y"),
                        error=error,
                    )
                )
            elif not failed_oncall_period:
                # At most one on-call period per call - report the
                # whole window once, not once per failed Friday.
                failed_oncall_period = [shift_period_start, shift_period_end]
                messages.append(
                    _(
                        "[ERROR] Échec de la régénération des astreintes pour la "
                        "période %(start)s - %(end)s : %(error)s - les "
                        "astreintes de cette période n'ont pas été "
                        "modifiées, action manuelle nécessaire",
                        start=shift_period_start.strftime("%d/%m/%Y"),
                        end=shift_period_end.strftime("%d/%m/%Y"),
                        error=error,
                    )
                )

        return (
            regenerated_shifts,
            messages,
            unfilled_oncall_dates,
            failed_shift_dates,
            failed_oncall_period,
            unfilled_shift_dates,
        )
