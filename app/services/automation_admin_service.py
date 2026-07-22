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
from app.repositories.oncall_repository import OnCallRepository
from app.repositories.shift_repository import ShiftRepository
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
            # Captured before the wipe below, so the search can prefer
            # keeping each week's existing occupant instead of blindly
            # replaying the rotation order - same mechanism as the
            # automatic rebalance-after-leave path (see
            # OnCallAutomation.capture_existing_assignments()).
            preferred_assignments = OnCallAutomation.capture_existing_assignments(
                start_date, end_date
            )
            oncalls_deleted = OnCallRepository.delete_overlapping_range(
                start_date, end_date
            )
            if oncalls_deleted:
                db.session.commit()
            result.oncalls_deleted = oncalls_deleted

            _regenerated, oncall_messages, oncall_unfilled_dates = (
                OnCallAutomation.generate_oncall_schedule(
                    start_date,
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

        if not dry_run:
            result.oncalls_deleted, result.shifts_deleted = (
                AutomationAdminService.clear_period(start_date, end_date)
            )

        oncalls, oncall_messages, oncall_unfilled_dates = (
            OnCallAutomation.generate_oncall_schedule(
                start_date, end_date, rotation_order_ids, dry_run=dry_run
            )
        )
        result.oncalls = oncalls
        result.oncall_messages = oncall_messages
        result.oncall_unfilled_dates = oncall_unfilled_dates

        # Note (dry_run only): the shift preview is based on the
        # on-calls already in the database for the period (the on-call
        # dry_run above doesn't save anything) - it can therefore differ
        # from the final result if no on-call exists yet for this period.
        shifts, shift_messages, shift_unfilled_dates = (
            AdvancedShiftAutomation.generate_full_schedule(
                start_date, end_date, dry_run=dry_run
            )
        )
        result.shifts = shifts
        result.shift_messages = shift_messages
        result.shift_unfilled_dates = shift_unfilled_dates

        return result
