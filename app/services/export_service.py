"""
Export service for Leviia Schedule.

Thin wrapper around app.utils.export.ics_exporter so export routes can
depend on the service layer like the rest of the app instead of the
utils module directly.
"""

from typing import Iterable

from app.utils.export.ics_exporter import generate_ics_calendar


class ExportService:
    """Logique métier pour l'export ICS."""

    @staticmethod
    def generate_ics(events: Iterable, calendar_name: str = "Leviia Schedule") -> bytes:
        return generate_ics_calendar(events, calendar_name=calendar_name)
