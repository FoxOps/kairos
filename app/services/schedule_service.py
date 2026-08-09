"""
Schedule (calendar) service for Kairos.

Aggregates shifts, on-calls and leaves into the event list consumed by
the FullCalendar-based views (index page, /api/shifts).
"""

from datetime import datetime, timedelta

from flask_babel import gettext as _

from app.repositories.leave_repository import LeaveRepository
from app.repositories.oncall_repository import OnCallRepository
from app.repositories.shift_repository import ShiftRepository
from app.utils.helpers.timezone_helpers import to_viewer_timezone

CALENDAR_WINDOW_DAYS = 180


class ScheduleService:
    """Aggregates shifts/on-calls/leaves into calendar events."""

    @staticmethod
    def calendar_window() -> tuple[datetime, datetime]:
        """±6-month window around today for the calendar."""
        now = datetime.now()
        return (
            now - timedelta(days=CALENDAR_WINDOW_DAYS),
            now + timedelta(days=CALENDAR_WINDOW_DAYS),
        )

    @staticmethod
    def get_calendar_events(viewer) -> list[dict]:
        """Default ±180-day window around today - kept for callers that
        don't need a specific range (e.g. get_calendar_events_for_range()
        called with no query params)."""
        window_start, window_end = ScheduleService.calendar_window()
        return ScheduleService.get_calendar_events_for_range(
            viewer, window_start, window_end
        )

    @staticmethod
    def get_calendar_events_for_range(
        viewer,
        window_start: datetime,
        window_end: datetime,
        group_ids: list[int] | None = None,
    ) -> list[dict]:
        """Fetch shifts/on-calls/leaves within an arbitrary window and
        convert them into FullCalendar events, translated into the
        viewer's effective timezone. Backs /api/shifts as FullCalendar's
        dynamic events source (see dashboard_routes.py::api_get_shifts)
        - called with whatever range the calendar is currently viewing,
        not capped to the ±180-day default the way a one-shot page-load
        embed would be. `group_ids`: the calendar's multi-group filter -
        None means no filtering (every group), matching the repository
        layer's own None-means-unfiltered convention."""
        shifts = ShiftRepository.list_in_window(window_start, window_end, group_ids)
        on_calls = OnCallRepository.list_in_window(window_start, window_end, group_ids)
        leaves = LeaveRepository.list_in_window(
            window_start.date(), window_end.date(), group_ids
        )

        return ScheduleService.build_calendar_events(shifts, on_calls, leaves, viewer)

    @staticmethod
    def build_calendar_events(shifts, on_calls, leaves, viewer) -> list[dict]:
        """viewer: the User the resulting event times are translated
        for (see app/utils/helpers/timezone_helpers.py) - shift/on-call
        start/end are stored as naive wall-clock times in the
        organization's default_timezone; leave dates have no time
        component and need no conversion."""
        events: list[dict] = []

        for shift in shifts:
            label = shift.shift_type.label if shift.shift_type else shift.shift_type
            events.append(
                {
                    "id": f"shift-{shift.id}",
                    "title": f"{shift.user.name} - {label}",
                    "start": to_viewer_timezone(shift.start_time, viewer).isoformat(),
                    "end": to_viewer_timezone(shift.end_time, viewer).isoformat(),
                    "className": "fc-event-shift",
                    "extendedProps": {
                        "type": "shift",
                        "resourceId": shift.id,
                        "userId": shift.user_id,
                        "groupId": shift.user.group_id,
                        "userName": shift.user.name,
                        "shiftTypeId": shift.shift_type_id,
                        "shiftTypeLabel": label,
                    },
                }
            )

        for oncall in on_calls:
            events.append(
                {
                    "id": f"oncall-{oncall.id}",
                    "title": _("Astreinte - %(name)s", name=oncall.user.name),
                    "start": to_viewer_timezone(oncall.start_time, viewer).isoformat(),
                    "end": to_viewer_timezone(oncall.end_time, viewer).isoformat(),
                    "className": "fc-event-oncall",
                    "extendedProps": {
                        "type": "oncall",
                        "resourceId": oncall.id,
                        "userId": oncall.user_id,
                        "groupId": oncall.user.group_id,
                        "userName": oncall.user.name,
                    },
                }
            )

        for leave in leaves:
            events.append(
                {
                    "id": f"leave-{leave.id}",
                    "title": _("Congé - %(name)s", name=leave.user.name),
                    "start": leave.start_date.isoformat(),
                    "end": (leave.end_date + timedelta(days=1)).isoformat(),
                    "className": "fc-event-leave",
                    "allDay": True,
                    "extendedProps": {
                        "type": "leave",
                        "resourceId": leave.id,
                        "userId": leave.user_id,
                        "groupId": leave.user.group_id,
                        "userName": leave.user.name,
                    },
                }
            )

        return events
