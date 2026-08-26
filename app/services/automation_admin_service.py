"""
Automation admin service for Kairos.

Business logic supporting the admin automation screens: clearing an
existing period before regeneration and persisting the rotation order.
The actual schedule generation itself lives in app.utils.automation
(OnCallAutomation/AdvancedShiftAutomation), which is already a
business-logic layer - this service wraps the admin-specific glue
around it rather than duplicating it.
"""

from dataclasses import dataclass, field
from datetime import date
from types import SimpleNamespace

from flask_babel import gettext as _

from app import db
from app.models import Group, ShiftType, User
from app.repositories.oncall_repository import OnCallRepository
from app.repositories.shift_repository import ShiftRepository
from app.services.settings_service import SettingsService
from app.utils.automation import AdvancedShiftAutomation, OnCallAutomation
from app.utils.automation.planner import build_planning_request, plan_schedule
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
        app/utils/automation/planner/): the dry_run branch now routes
        through the new pure planner instead of the legacy path below,
        fixing the "shift preview reads real on-calls from the DB
        while its own on-call preview was only ever in-memory" defect
        documented on the comment further down (still accurate for the
        untouched dry_run=False branch, which phase 7 will cut over
        separately). rotation_order_ids has no equivalent on the new
        engine's path - rotation order is only ever read from
        AutomationConfig.get_rotation_order() (see
        AutomationRuleAdminService/save_order), so a `generate`/
        `dry_run` form submission's own rotation_order_ids value is
        simply unused for the preview; `save_order` itself is
        unaffected and still writes AutomationConfig for the next call
        to read."""
        if dry_run:
            oncall_regen_start = OnCallAutomation.align_regeneration_start(start_date)
            request = build_planning_request(oncall_regen_start, end_date)
            plan = plan_schedule(request)
            return AutomationAdminService._generate_result_from_plan(plan)

        return AutomationAdminService._generate_full_legacy(
            start_date, end_date, rotation_order_ids, dry_run
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
    def _generate_result_from_plan(plan: SchedulePlan) -> GenerateResult:
        """Presentation shim (phase 6): translates a pure SchedulePlan
        into the exact GenerateResult shape generate_full()'s legacy
        dry_run path already returns, so admin_automation_routes.py's
        automation_full() and full_dry_run.html need ZERO changes.

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

        Messages are built as the same "[TAG] text" strings the legacy
        path produces, not pre-classified (category, text) tuples -
        admin_automation_routes.py's automation_full() already runs
        every message through _classify_automation_message() before
        handing them to the template, so producing the same tagged-
        string convention here means that route needs no changes
        either.
        """
        result = GenerateResult(dry_run=True)

        for proposed_oncall in plan.oncalls:
            if proposed_oncall.change_type == "unchanged":
                continue
            user = db.session.get(User, proposed_oncall.user_id)
            result.oncalls.append(
                SimpleNamespace(
                    user=user,
                    start_time=proposed_oncall.start_time,
                    end_time=proposed_oncall.end_time,
                )
            )

        for proposed_shift in plan.shifts:
            if proposed_shift.change_type == "unchanged":
                continue
            user = db.session.get(User, proposed_shift.user_id)
            shift_type = db.session.get(ShiftType, proposed_shift.shift_type_id)
            result.shifts.append(
                SimpleNamespace(
                    user=user,
                    shift_type=shift_type,
                    date=proposed_shift.date,
                )
            )

        for unfilled in plan.unfilled:
            if unfilled.kind == "oncall_week":
                result.oncall_unfilled_dates.append(unfilled.date)
                result.oncall_messages.append(
                    _(
                        "[WARN] Aucune astreinte générée pour le %(date)s "
                        "(aucun utilisateur ne respecte le délai légal entre "
                        "deux astreintes) - assignation manuelle nécessaire.",
                        date=unfilled.date.strftime("%d/%m/%Y"),
                    )
                )
                continue

            result.shift_unfilled_dates.append(unfilled.date)
            shift_type = None
            if unfilled.detail:
                shift_type = db.session.get(ShiftType, int(unfilled.detail))
            label = shift_type.label if shift_type else unfilled.detail

            if unfilled.kind == "mandatory_shift":
                result.shift_messages.append(
                    _(
                        "[ALERT] Créneau obligatoire non pourvu pour le "
                        "%(date)s : %(name)s.",
                        date=unfilled.date.strftime("%d/%m/%Y"),
                        name=label,
                    )
                )
            else:  # staffing_min
                result.shift_messages.append(
                    _(
                        "[WARN] Effectif minimum non atteint pour le "
                        "%(date)s : %(name)s.",
                        date=unfilled.date.strftime("%d/%m/%Y"),
                        name=label,
                    )
                )

        # The only rule_type any planner module currently raises a
        # RuleViolation for is rest_after_oncall (shift_planner.py) -
        # always shift-scoped. A future rule type producing on-call-
        # side violations would need its own branch here.
        for violation in plan.violations:
            user = (
                db.session.get(User, violation.user_id) if violation.user_id else None
            )
            tag = "[ALERT]" if violation.severity == "hard_blocked" else "[WARN]"
            result.shift_messages.append(
                _(
                    "%(tag)s %(name)s n'a pas pu être affecté au %(date)s : "
                    "repos insuffisant après son astreinte.",
                    tag=tag,
                    name=user.name if user else _("Utilisateur inconnu"),
                    date=violation.date.strftime("%d/%m/%Y"),
                )
            )

        return result
