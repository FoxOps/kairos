"""
ICS export functionality for Leviia Schedule.

This module provides functions to export shifts, on-call duties, and leaves
to ICS format for calendar integration.
"""

from datetime import datetime

import pytz
from icalendar import Calendar, Event


def generate_ics_standard(events, calendar_name="Leviia Schedule"):
    """
    Generate a standard ICS file from a list of events.
    Supports Shift, OnCall, and Leave objects.

    Args:
        events: List of objects (Shift, OnCall or Leave) with required attributes.
        calendar_name: Name of the calendar (default: "Leviia Schedule").

    Returns:
        str: Content of the ICS file.
    """
    tz = pytz.timezone("Europe/Paris")

    cal = Calendar()
    cal.add("prodid", "-//Leviia Schedule//fr")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("name", calendar_name)
    cal.add("x-wr-timezone", "Europe/Paris")

    for event_obj in events:
        event = Event()

        # Set UID (unique identifier)
        event.add("uid", f"{event_obj.__class__.__name__}-{event_obj.id}@mtg-schedule")

        # Handle titles, descriptions and dates based on event type
        event_type = event_obj.__class__.__name__

        if event_type == "Shift":
            shift_type_label = (
                event_obj.shift_type.label
                if event_obj.shift_type
                else str(event_obj.shift_type_id)
            )
            title = f"Shift {shift_type_label} - {event_obj.user.name}"
            description = (
                f"Type: {shift_type_label}\nUtilisateur: {event_obj.user.name}"
            )
            start_time = event_obj.start_time
            end_time = event_obj.end_time
        elif event_type == "OnCall":
            title = f"Astreinte - {event_obj.user.name}"
            description = f"Utilisateur: {event_obj.user.name}"
            start_time = event_obj.start_time
            end_time = event_obj.end_time
        elif event_type == "Leave":
            title = f"Congé - {event_obj.user.name}"
            description = f"Utilisateur: {event_obj.user.name}"
            # For Leave, we need to handle dates (not datetimes)
            start_time = datetime.combine(event_obj.start_date, datetime.min.time())
            end_time = datetime.combine(event_obj.end_date, datetime.min.time())
        else:
            # Unknown type, skip
            continue

        # Set start and end times
        event.add("dtstart", start_time)
        event.add("dtend", end_time)
        event.add("summary", title)
        event.add("description", description)

        # Set timezone
        event.add("dtstamp", datetime.now(tz))

        cal.add_component(event)

    return cal.to_ical().decode("utf-8")


def export_to_ics(events, calendar_name="Leviia Schedule") -> str:
    """
    Export events to ICS format.

    Args:
        events: List of events to export
        calendar_name: Name of the calendar

    Returns:
        ICS formatted string
    """
    return generate_ics_standard(events, calendar_name)


def generate_ics_calendar(events, calendar_name="Leviia Schedule") -> bytes:
    """
    Generate a calendar in ICS format as bytes.

    Args:
        events: List of events to include
        calendar_name: Name of the calendar

    Returns:
        ICS formatted bytes
    """
    return generate_ics_standard(events, calendar_name).encode("utf-8")


# ---------------------------------------------------------------------------
# Convenience functions for specific event types (for backward compatibility)
# ---------------------------------------------------------------------------


def generate_ics_shifts(shifts):
    """Generate an ICS file for shifts."""
    return generate_ics_standard(shifts, "Leviia Schedule - Shifts")


def generate_ics_oncall(on_calls):
    """Generate an ICS file for on-call duties."""
    return generate_ics_standard(on_calls, "Leviia Schedule - Astreintes")


def generate_ics_leaves(leaves):
    """Generate an ICS file for leaves."""
    return generate_ics_standard(leaves, "Leviia Schedule - Conge")
