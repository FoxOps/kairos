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

from app import db
from app.models import Group
from app.repositories.oncall_repository import OnCallRepository
from app.repositories.shift_repository import ShiftRepository
from app.services.settings_service import SettingsService
from app.utils.automation import AdvancedShiftAutomation, OnCallAutomation


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
    def clear_period(start_date: date, end_date: date) -> tuple[int, int]:
        """Delete existing on-calls and shifts overlapping the period.
        Returns (oncalls_deleted, shifts_deleted)."""
        oncalls_deleted = OnCallRepository.delete_overlapping_range(
            start_date, end_date
        )
        if oncalls_deleted:
            db.session.commit()

        shifts_deleted = ShiftRepository.delete_in_date_range(start_date, end_date)
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
        route's own docstring)."""
        from app.models import AutomationConfig

        result = RefreshResult()

        if oncall_mode == "fill_gaps":
            _filled, oncall_messages, oncall_unfilled_dates = (
                OnCallAutomation.fill_oncall_gaps(
                    start_date,
                    end_date,
                    rotation_order_ids=AutomationConfig.get_rotation_order(),
                    dry_run=False,
                )
            )
            result.oncall_messages = oncall_messages
            result.oncall_messages_category = "info"
            result.oncall_unfilled_dates = oncall_unfilled_dates
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
            oncalls_deleted = OnCallRepository.delete_overlapping_range(
                start_date, end_date
            )
            if oncalls_deleted:
                db.session.commit()
            result.oncalls_deleted = oncalls_deleted

            _regenerated, oncall_messages, oncall_unfilled_dates = (
                OnCallAutomation.generate_oncall_schedule(
                    oncall_regen_start,
                    end_date,
                    rotation_order_ids=AutomationConfig.get_rotation_order(),
                    dry_run=False,
                    preferred_assignments=preferred_assignments,
                )
            )
            result.oncall_messages = oncall_messages
            result.oncall_messages_category = "danger"
            result.oncall_unfilled_dates = oncall_unfilled_dates

        # Only deletes shifts (never on-calls beyond what oncall_mode
        # above already handled): this recomputes shifts, taking
        # whatever on-calls now exist into account.
        shifts_deleted = ShiftRepository.delete_in_date_range(start_date, end_date)
        if shifts_deleted:
            db.session.commit()
        result.shifts_deleted = shifts_deleted

        shifts, shift_messages, shift_unfilled_dates = (
            AdvancedShiftAutomation.generate_full_schedule(
                start_date, end_date, dry_run=False
            )
        )
        result.shifts = shifts
        result.shift_messages = shift_messages
        result.shift_unfilled_dates = shift_unfilled_dates

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
        generate_full_schedule() actually persist their result."""
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

        if not dry_run:
            result.oncalls_deleted, result.shifts_deleted = (
                AutomationAdminService.clear_period(start_date, end_date)
            )

        # scheduling_mode="per_group" (SettingsService) runs one
        # independent generation pass per eligible Group instead of
        # pooling every group into a single shared pass - see the
        # `group` parameter added to generate_oncall_schedule()/
        # generate_full_schedule() for what "independent" means (e.g.
        # concurrent on-calls, one per group, for the same week).
        # Rule *values* (weekend/slots/spacing/anchor) stay org-wide
        # either way in this increment - only the eligible-user pool
        # is partitioned.
        per_group = SettingsService.get_scheduling_mode() == "per_group"
        oncall_groups = (
            Group.query.filter_by(is_part_of_oncall=True).all() if per_group else [None]
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

        # Note (dry_run only): the shift preview is based on the
        # on-calls already in the database for the period (the on-call
        # dry_run above doesn't save anything) - it can therefore differ
        # from the final result if no on-call exists yet for this period.
        schedule_groups = (
            Group.query.filter_by(is_part_of_schedule=True).all()
            if per_group
            else [None]
        )
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
