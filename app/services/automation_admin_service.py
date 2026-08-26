"""
Automation admin service for Kairos.

Business logic supporting the admin automation screens: clearing an
existing period before regeneration and persisting the rotation order.
The actual schedule generation itself lives in app.utils.automation
(OnCallAutomation/AdvancedShiftAutomation), which is already a
business-logic layer - this service wraps the admin-specific glue
around it rather than duplicating it.
"""

from dataclasses import dataclass, field, replace
from datetime import date, timedelta

from flask import has_request_context
from flask_login import current_user

from app import db
from app.models import Group, User
from app.repositories.oncall_repository import OnCallRepository
from app.repositories.shift_repository import ShiftRepository
from app.services.automation_apply_service import AutomationApplyService
from app.services.settings_service import SettingsService
from app.utils.automation import AdvancedShiftAutomation, OnCallAutomation
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
    def save_rotation_order(rotation_order_ids: list[int]) -> str | None:
        """Returns error_message, or None on success."""
        try:
            from app.models import AutomationConfig

            AutomationConfig.set_rotation_order(rotation_order_ids)
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
    def _delete_oncalls_scoped(
        start_date: date, end_date: date, groups: list[Group | None]
    ) -> int:
        """Sums delete_overlapping_range() across `groups` - `[None]`
        (the default everywhere "shared" mode applies) reduces to a
        single unscoped delete (group_id=None); a real list of Group
        rows deletes once per group instead, so a group absent from
        that list is never touched."""
        return sum(
            OnCallRepository.delete_overlapping_range(
                start_date,
                end_date,
                group_id=(group.id if group is not None else None),
            )
            for group in groups
        )

    @staticmethod
    def _delete_shifts_scoped(
        start_date: date, end_date: date, groups: list[Group | None]
    ) -> int:
        """Shift equivalent of _delete_oncalls_scoped() above."""
        return sum(
            ShiftRepository.delete_in_date_range(
                start_date,
                end_date,
                group_id=(group.id if group is not None else None),
            )
            for group in groups
        )

    @staticmethod
    def clear_period(
        start_date: date,
        end_date: date,
        oncall_groups: list[Group | None] | None = None,
        shift_groups: list[Group | None] | None = None,
    ) -> tuple[int, int]:
        """Delete existing on-calls and shifts overlapping the period.
        Returns (oncalls_deleted, shifts_deleted). `oncall_groups`/
        `shift_groups`: the exact list of groups (or `[None]`/omitted
        for unscoped - correct under "shared" mode, where nothing is
        group-partitioned to begin with) the caller is about to
        regenerate right after this call - reuse generate_full()'s own
        `oncall_groups`/`schedule_groups` list here rather than
        recomputing it, so the delete can never diverge from what the
        regeneration loop actually repopulates. Real bug fixed here: an
        earlier version deleted everyone in this window unconditionally
        even under "per_group" mode, silently losing any on-call/shift
        belonging to a group that had since been toggled out of
        eligibility (is_part_of_oncall/is_part_of_schedule) - deleted,
        never regenerated because the loop only iterates
        currently-eligible groups."""
        oncall_groups = oncall_groups if oncall_groups is not None else [None]
        shift_groups = shift_groups if shift_groups is not None else [None]

        oncalls_deleted = AutomationAdminService._delete_oncalls_scoped(
            start_date, end_date, oncall_groups
        )
        if oncalls_deleted:
            db.session.commit()

        shifts_deleted = AutomationAdminService._delete_shifts_scoped(
            start_date, end_date, shift_groups
        )
        if shifts_deleted:
            db.session.commit()

        return oncalls_deleted, shifts_deleted

    @staticmethod
    def refresh_shifts(
        start_date: date, end_date: date, oncall_mode: str = "none"
    ) -> RefreshResult:
        """Business logic for the "refresh_shifts" action of
        admin_automation_routes.py::automation_full() - shifts-only
        recomputation, optionally also touching on-calls first depending
        on oncall_mode ("none"/"fill_gaps"/"regenerate", see that
        route's own docstring).

        Phase 7 of the automation engine rework: gated by
        SettingsService.get_new_automation_engine_enabled(), same toggle
        as generate_full()'s dry_run=False branch below."""
        if SettingsService.get_new_automation_engine_enabled():
            return AutomationAdminService._refresh_shifts_new_engine(
                start_date, end_date, oncall_mode
            )
        return AutomationAdminService._refresh_shifts_legacy(
            start_date, end_date, oncall_mode
        )

    @staticmethod
    def _refresh_shifts_legacy(
        start_date: date, end_date: date, oncall_mode: str = "none"
    ) -> RefreshResult:
        """The pre-phase-7 refresh_shifts algorithm, kept directly
        callable the same way _generate_full_legacy() is (see its own
        docstring) - reached by refresh_shifts() above whenever the
        cutover toggle is off.

        oncall_scheduling_mode/shift_scheduling_mode="per_group" each
        independently run one pass per eligible Group instead of
        pooling every group into one shared pass - same loop shape as
        generate_full() below, applied to all three of this method's
        own generation spots (fill_gaps, regenerate, and the shifts
        recompute)."""
        from app.models import AutomationConfig

        result = RefreshResult()

        oncall_per_group = SettingsService.get_oncall_scheduling_mode() == "per_group"
        oncall_groups = (
            Group.query.filter_by(is_part_of_oncall=True).all()
            if oncall_per_group
            else [None]
        )
        # Computed here (not just before the shift delete further down)
        # so that delete can be scoped to exactly these groups too - see
        # clear_period()'s docstring for why an unscoped delete under
        # "per_group" mode is a real data-loss bug otherwise.
        shift_per_group = SettingsService.get_shift_scheduling_mode() == "per_group"
        schedule_groups = (
            Group.query.filter_by(is_part_of_schedule=True).all()
            if shift_per_group
            else [None]
        )

        if oncall_mode == "fill_gaps":
            for group in oncall_groups:
                _filled, oncall_messages, oncall_unfilled_dates = (
                    OnCallAutomation.fill_oncall_gaps(
                        start_date,
                        end_date,
                        rotation_order_ids=AutomationConfig.get_rotation_order(),
                        dry_run=False,
                        group=group,
                    )
                )
                result.oncall_messages.extend(oncall_messages)
                result.oncall_unfilled_dates.extend(oncall_unfilled_dates)
            result.oncall_messages_category = "info"
        elif oncall_mode == "regenerate":
            # delete_overlapping_range() below uses a true datetime
            # overlap check, so it also wipes the on-call week anchored
            # the Friday just before start_date (its own on-call only
            # ends 07:00 into start_date, still "overlapping"). Align
            # first so the regeneration re-creates that same week
            # instead of silently losing it - see OnCallAutomation.
            # align_regeneration_start()'s docstring.
            oncall_regen_start = OnCallAutomation.align_regeneration_start(start_date)

            # Captured before the wipe below, so the search can prefer
            # keeping each week's existing occupant instead of blindly
            # replaying the rotation order - same mechanism as the
            # automatic rebalance-after-leave path (see
            # OnCallAutomation.capture_existing_assignments()).
            preferred_assignments = OnCallAutomation.capture_existing_assignments(
                oncall_regen_start, end_date
            )
            # Scoped to oncall_groups (same list the loop below
            # regenerates from) rather than deleted unconditionally - see
            # clear_period()'s docstring for why an unscoped delete under
            # "per_group" mode would otherwise silently lose data for a
            # group toggled out of eligibility since it was created.
            oncalls_deleted = AutomationAdminService._delete_oncalls_scoped(
                start_date, end_date, oncall_groups
            )
            if oncalls_deleted:
                db.session.commit()
            result.oncalls_deleted = oncalls_deleted

            for group in oncall_groups:
                _regenerated, oncall_messages, oncall_unfilled_dates = (
                    OnCallAutomation.generate_oncall_schedule(
                        oncall_regen_start,
                        end_date,
                        rotation_order_ids=AutomationConfig.get_rotation_order(),
                        dry_run=False,
                        preferred_assignments=preferred_assignments,
                        group=group,
                    )
                )
                result.oncall_messages.extend(oncall_messages)
                result.oncall_unfilled_dates.extend(oncall_unfilled_dates)
            result.oncall_messages_category = "danger"

        # Only deletes shifts (never on-calls beyond what oncall_mode
        # above already handled): this recomputes shifts, taking
        # whatever on-calls now exist into account. Scoped to
        # schedule_groups (computed above, same list the loop below
        # regenerates from) rather than deleted unconditionally - same
        # reasoning as the oncall delete above.
        shifts_deleted = AutomationAdminService._delete_shifts_scoped(
            start_date, end_date, schedule_groups
        )
        if shifts_deleted:
            db.session.commit()
        result.shifts_deleted = shifts_deleted

        for group in schedule_groups:
            shifts, shift_messages, shift_unfilled_dates = (
                AdvancedShiftAutomation.generate_full_schedule(
                    start_date, end_date, dry_run=False, group=group
                )
            )
            result.shifts.extend(shifts)
            result.shift_messages.extend(shift_messages)
            result.shift_unfilled_dates.extend(shift_unfilled_dates)

        return result

    @staticmethod
    def generate_full(
        start_date: date,
        end_date: date,
        rotation_order_ids: list[int],
        dry_run: bool,
    ) -> GenerateResult:
        """Business logic for the "generate"/"dry_run" actions of
        admin_automation_routes.py::automation_full() - full on-calls +
        shifts (re)generation for the period. Shared by both actions
        since they run the exact same computation, dry_run only
        controlling whether generate_oncall_schedule()/
        generate_full_schedule() actually persist their result.

        Phase 6 of the automation engine rework (see
        app/utils/automation/planner/): the dry_run branch always routes
        through the new pure planner instead of the legacy path,
        fixing the "shift preview reads real on-calls from the DB
        while its own on-call preview was only ever in-memory" defect.
        rotation_order_ids has no equivalent on the new engine's path -
        rotation order is only ever read from
        AutomationConfig.get_rotation_order() (see
        AutomationRuleAdminService/save_order), so a `generate`/
        `dry_run` form submission's own rotation_order_ids value is
        simply unused for the preview; `save_order` itself is
        unaffected and still writes AutomationConfig for the next call
        to read.

        Phase 7: the dry_run=False branch is gated by
        SettingsService.get_new_automation_engine_enabled() - off by
        default, so real generation keeps using the legacy engine until
        an admin explicitly opts in. The preview above always uses the
        new planner regardless of this toggle, same as before phase 7 -
        an admin previewing before opting in sees exactly what they'd
        get if they did."""
        if dry_run:
            plan = AutomationAdminService._build_new_engine_plan(start_date, end_date)
            return AutomationAdminService._generate_result_from_plan(plan, dry_run=True)

        if SettingsService.get_new_automation_engine_enabled():
            return AutomationAdminService._generate_full_new_engine(
                start_date, end_date
            )

        return AutomationAdminService._generate_full_legacy(
            start_date, end_date, rotation_order_ids, dry_run
        )

    @staticmethod
    def _build_new_engine_plan(start_date: date, end_date: date) -> SchedulePlan:
        """Shared by generate_full()'s preview branch and
        _generate_full_new_engine() below, so the preview an admin sees
        and what "Générer" actually applies are always built from the
        exact same request-shaping - the whole point of phase 6/7 is
        eliminating preview/apply divergence (audit defect #1), so this
        must never fork into two slightly-different code paths.

        oncall_regen_start widens the on-call side's Friday search to
        the covering Friday when start_date falls mid-week (see
        OnCallAutomation.align_regeneration_start); shift_start_date
        keeps the literal caller-requested start_date for shift planning
        - see PlanningRequest.shift_start_date's own docstring for why
        the two must NOT share the same effective start."""
        oncall_regen_start = OnCallAutomation.align_regeneration_start(start_date)
        request = build_planning_request(
            oncall_regen_start, end_date, shift_start_date=start_date
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
    def _generate_full_new_engine(start_date: date, end_date: date) -> GenerateResult:
        """Phase 7: real (dry_run=False) generation routed through the
        new planner + AutomationApplyService.apply_plan() - reached by
        generate_full() above only when
        SettingsService.get_new_automation_engine_enabled() is True.
        Raises on an unsuccessful apply (rather than returning a result
        with the failure silently absorbed) so
        admin_automation_routes.py's existing `except Exception as e:
        flash(...)` handling surfaces it exactly like any other
        generation failure - no route changes needed."""
        plan = AutomationAdminService._build_new_engine_plan(start_date, end_date)
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
    def _generate_full_legacy(
        start_date: date,
        end_date: date,
        rotation_order_ids: list[int],
        dry_run: bool,
    ) -> GenerateResult:
        """The pre-phase-6 generation algorithm, kept directly callable
        (bypassing generate_full()'s own dry_run=True dispatch to the
        new planner above) so
        scripts/compare_automation_engines.py can still compare the new
        planner against the actual legacy generation algorithm with
        dry_run=True, even though production previews no longer use it.
        generate_full() itself only ever calls this with dry_run=False
        now - phase 7 retargets that remaining call too, at which point
        this method's dry_run=True capability stops being exercised by
        anything except the comparison script (still meaningful there
        until phase 8 deletes the underlying
        OnCallAutomation.generate_oncall_schedule()/
        AdvancedShiftAutomation.generate_full_schedule() entirely)."""
        result = GenerateResult(dry_run=dry_run)

        # Computed *before* clear_period() below, which deletes on-calls
        # via a true datetime overlap check and would also wipe the
        # on-call week anchored the Friday just before start_date -
        # querying for it after that delete would always find nothing
        # (already gone), silently defeating this realignment. Align
        # first so the regeneration re-creates that same week instead of
        # losing it - see OnCallAutomation.align_regeneration_start()'s
        # docstring. Real regression caught by
        # tests/integration/test_admin_automation.py::
        # TestAutomationFullAppendedGeneration - a first ordering
        # attempt called this after clear_period() and looked correct
        # until that test's second, appended "Générer" call proved the
        # boundary week from the first call was still being lost.
        oncall_regen_start = OnCallAutomation.align_regeneration_start(start_date)

        # Also captured before the wipe, same "minimal perturbation"
        # mechanism as _rebalance_oncall_section/refresh_shifts's
        # regenerate mode (see OnCallAutomation.
        # capture_existing_assignments()'s docstring) - without it,
        # "Générer" used on a period appended right after an existing
        # one would silently reshuffle the boundary week's already-
        # working occupant instead of keeping it, purely because it
        # happened to fall inside the realigned regeneration range.
        preferred_assignments = OnCallAutomation.capture_existing_assignments(
            oncall_regen_start, end_date
        )

        # oncall_scheduling_mode/shift_scheduling_mode="per_group"
        # (SettingsService) each independently run one generation pass
        # per eligible Group instead of pooling every group into a
        # single shared pass - see the `group` parameter added to
        # generate_oncall_schedule()/generate_full_schedule() for what
        # "independent" means (e.g. concurrent on-calls, one per
        # group, for the same week). The two are deliberately separate
        # settings: a team's on-call rotation and its shift rotation
        # don't have to be scoped the same way. Rule *values* (weekend/
        # slots/spacing/anchor) stay org-wide either way in this
        # increment - only the eligible-user pool is partitioned.
        # Computed before clear_period() below (not just before the
        # generation loops) so the delete can be scoped to exactly these
        # groups too - see clear_period()'s docstring.
        oncall_per_group = SettingsService.get_oncall_scheduling_mode() == "per_group"
        oncall_groups = (
            Group.query.filter_by(is_part_of_oncall=True).all()
            if oncall_per_group
            else [None]
        )
        shift_per_group = SettingsService.get_shift_scheduling_mode() == "per_group"
        schedule_groups = (
            Group.query.filter_by(is_part_of_schedule=True).all()
            if shift_per_group
            else [None]
        )

        if not dry_run:
            result.oncalls_deleted, result.shifts_deleted = (
                AutomationAdminService.clear_period(
                    start_date,
                    end_date,
                    oncall_groups=oncall_groups,
                    shift_groups=schedule_groups,
                )
            )

        for group in oncall_groups:
            oncalls, oncall_messages, oncall_unfilled_dates = (
                OnCallAutomation.generate_oncall_schedule(
                    oncall_regen_start,
                    end_date,
                    rotation_order_ids,
                    dry_run=dry_run,
                    preferred_assignments=preferred_assignments,
                    group=group,
                )
            )
            result.oncalls.extend(oncalls)
            result.oncall_messages.extend(oncall_messages)
            result.oncall_unfilled_dates.extend(oncall_unfilled_dates)

        # Note: this branch is only ever reached with dry_run=False now
        # (phase 6 above routes dry_run=True through the new planner
        # instead) - schedule_groups computed above, alongside
        # oncall_groups.
        for group in schedule_groups:
            shifts, shift_messages, shift_unfilled_dates = (
                AdvancedShiftAutomation.generate_full_schedule(
                    start_date, end_date, dry_run=dry_run, group=group
                )
            )
            result.shifts.extend(shifts)
            result.shift_messages.extend(shift_messages)
            result.shift_unfilled_dates.extend(shift_unfilled_dates)

        return result

    @staticmethod
    def _generate_result_from_plan(
        plan: SchedulePlan,
        dry_run: bool,
        oncalls_deleted: int = 0,
        shifts_deleted: int = 0,
    ) -> GenerateResult:
        """Presentation shim: translates a pure SchedulePlan into the
        exact GenerateResult shape generate_full()'s legacy path already
        returns, so admin_automation_routes.py's automation_full() and
        full_dry_run.html need ZERO changes. Used both for the dry_run
        preview (phase 6, oncalls_deleted/shifts_deleted always 0 - a
        preview never deletes anything) and, once applied, for the real
        result (phase 7, oncalls_deleted/shifts_deleted come from the
        matching ApplyResult) - see _generate_full_new_engine() below.

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
        change_type != "unchanged" are included, matching the legacy
        dry_run's own implicit behavior (it only ever built objects for
        slots it was actually assigning, never for untouched rows).
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
    def _refresh_shifts_new_engine(
        start_date: date, end_date: date, oncall_mode: str
    ) -> RefreshResult:
        """Phase 7: refresh_shifts()'s new-engine path, reached only
        when SettingsService.get_new_automation_engine_enabled() is
        True. Always plans over the exact same
        [oncall_regen_start, end_date] / shift_start_date=start_date
        request-shaping as generate_full()'s own new-engine path (see
        _build_new_engine_plan()'s docstring) - oncall_mode then adds an
        EXTRA, purely additive lock on top of the request's own
        DB-`locked`-column-derived locked_oncalls (phase 5), expressing
        each mode as a request-shaping choice rather than new
        planner-core logic:

        - "none": every (date, scope) in the window gets locked, whether
          or not anything is currently published there - on-calls are
          left completely untouched, matching the legacy "none" mode's
          "shifts recomputed from whatever on-calls already exist, even
          manually modified ones" contract exactly. A locked date with
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
        oncall_regen_start = OnCallAutomation.align_regeneration_start(start_date)
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
