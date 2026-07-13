"""
Schedule (calendar) service for Leviia Schedule.

Aggregates shifts, on-calls and leaves into the event list consumed by
the FullCalendar-based views (index page, /api/shifts).
"""

from datetime import datetime, timedelta

from app.repositories.leave_repository import LeaveRepository
from app.repositories.oncall_repository import OnCallRepository
from app.repositories.shift_repository import ShiftRepository

CALENDAR_WINDOW_DAYS = 180


class ScheduleService:
    """Agrège shifts/astreintes/congés en événements de calendrier."""

    @staticmethod
    def calendar_window() -> tuple[datetime, datetime]:
        """Fenêtre de ±6 mois autour d'aujourd'hui pour le calendrier."""
        now = datetime.now()
        return (
            now - timedelta(days=CALENDAR_WINDOW_DAYS),
            now + timedelta(days=CALENDAR_WINDOW_DAYS),
        )

    @staticmethod
    def get_calendar_events() -> list[dict]:
        """Récupère shifts/astreintes/congés dans la fenêtre du calendrier
        et les convertit en événements FullCalendar."""
        window_start, window_end = ScheduleService.calendar_window()

        shifts = ShiftRepository.list_in_window(window_start, window_end)
        on_calls = OnCallRepository.list_in_window(window_start, window_end)
        leaves = LeaveRepository.list_in_window(window_start.date(), window_end.date())

        return ScheduleService.build_calendar_events(shifts, on_calls, leaves)

    @staticmethod
    def build_calendar_events(shifts, on_calls, leaves) -> list[dict]:
        events = []

        for shift in shifts:
            label = shift.shift_type.label if shift.shift_type else shift.shift_type
            events.append(
                {
                    "id": f"shift-{shift.id}",
                    "title": f"{shift.user.name} - {label}",
                    "start": shift.start_time.isoformat(),
                    "end": shift.end_time.isoformat(),
                    "className": "fc-event-shift",
                    "extendedProps": {"type": "shift", "resourceId": shift.id},
                }
            )

        for oncall in on_calls:
            events.append(
                {
                    "id": f"oncall-{oncall.id}",
                    "title": f"Astreinte - {oncall.user.name}",
                    "start": oncall.start_time.isoformat(),
                    "end": oncall.end_time.isoformat(),
                    "className": "fc-event-oncall",
                    "extendedProps": {"type": "oncall", "resourceId": oncall.id},
                }
            )

        for leave in leaves:
            events.append(
                {
                    "id": f"leave-{leave.id}",
                    "title": f"Conge - {leave.user.name}",
                    "start": leave.start_date.isoformat(),
                    "end": (leave.end_date + timedelta(days=1)).isoformat(),
                    "className": "fc-event-leave",
                    "allDay": True,
                    "extendedProps": {"type": "leave", "resourceId": leave.id},
                }
            )

        return events
