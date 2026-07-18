"""
ICS export functionality for Kairos.

This module provides functions to export shifts, on-call duties, and leaves
to ICS format for calendar integration.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event


def generate_ics_standard(events, calendar_name="Kairos", tz_name="Europe/Paris"):
    """
    Generate a standard ICS file from a list of events.
    Supports Shift, OnCall, and Leave objects.

    Args:
        events: List of objects (Shift, OnCall or Leave) with required attributes.
        calendar_name: Name of the calendar (default: "Kairos").
        tz_name: IANA timezone name the stored naive datetimes should be
            interpreted in - always the organization's canonical timezone
            (SettingsService.get_default_timezone()), never a viewer's
            personal preference: attaching the wrong tzinfo would relabel
            the instant instead of translating it. See CLAUDE.md's
            "Multi-timezone support" section.

    Returns:
        str: Content of the ICS file.
    """
    tz = ZoneInfo(tz_name)

    cal = Calendar()
    cal.add("prodid", "-//Kairos//fr")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("name", calendar_name)
    cal.add("x-wr-timezone", tz_name)

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
            start_time = event_obj.start_time.replace(tzinfo=tz)
            end_time = event_obj.end_time.replace(tzinfo=tz)
        elif event_type == "OnCall":
            title = f"Astreinte - {event_obj.user.name}"
            description = f"Utilisateur: {event_obj.user.name}"
            start_time = event_obj.start_time.replace(tzinfo=tz)
            end_time = event_obj.end_time.replace(tzinfo=tz)
        elif event_type == "Leave":
            title = f"Congé - {event_obj.user.name}"
            description = f"Utilisateur: {event_obj.user.name}"
            # For Leave, we need to handle dates (not datetimes)
            start_time = datetime.combine(
                event_obj.start_date, datetime.min.time()
            ).replace(tzinfo=tz)
            end_time = datetime.combine(
                event_obj.end_date, datetime.min.time()
            ).replace(tzinfo=tz)
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

    # Generates a VTIMEZONE component matching the TZID attached to
    # dtstart/dtend above, from the ZoneInfo tzinfo objects - without
    # this, RFC-5545-compliant clients receive a TZID with no matching
    # VTIMEZONE definition and may reject or misinterpret the times.
    cal.add_missing_timezones()

    return cal.to_ical().decode("utf-8")


def export_to_ics(events, calendar_name="Kairos", tz_name="Europe/Paris") -> str:
    """
    Export events to ICS format.

    Args:
        events: List of events to export
        calendar_name: Name of the calendar
        tz_name: IANA timezone name - see generate_ics_standard's docstring

    Returns:
        ICS formatted string
    """
    return generate_ics_standard(events, calendar_name, tz_name)
