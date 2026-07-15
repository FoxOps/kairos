"""
Timezone conversion helpers for the FullCalendar JSON API (schedule/
on-call read and write via drag & drop).

Shifts/on-calls are stored as naive wall-clock datetimes meaning "local
time in the organization's default_timezone" (see CLAUDE.md's
"Multi-timezone support" section) - these functions translate between
that canonical value and a specific viewer's effective_timezone(), for
display and for interpreting drag & drop input from the browser.

FullCalendar itself is configured with `timeZone: 'UTC'`
(fullcalendar-config.js) so it never reinterprets these numbers against
the browser's own system clock - the server does all the real
conversion via zoneinfo, avoiding the need for a moment-timezone/luxon
plugin (this app is CDN-only, see CLAUDE.md's Frontend section).
"""

from datetime import datetime
from zoneinfo import ZoneInfo


def _org_timezone() -> ZoneInfo:
    from app.services import SettingsService

    return ZoneInfo(SettingsService.get_default_timezone())


def to_viewer_timezone(dt: datetime, viewer) -> datetime:
    """Naive org-tz wall clock -> naive viewer-tz wall clock, for
    serializing calendar events to the browser."""
    viewer_tz = ZoneInfo(viewer.effective_timezone())
    localized = dt.replace(tzinfo=_org_timezone())
    return localized.astimezone(viewer_tz).replace(tzinfo=None)


def to_org_timezone(dt: datetime, viewer) -> datetime:
    """Naive viewer-tz wall clock (drag & drop input) -> naive org-tz
    wall clock, for storage."""
    viewer_tz = ZoneInfo(viewer.effective_timezone())
    localized = dt.replace(tzinfo=viewer_tz)
    return localized.astimezone(_org_timezone()).replace(tzinfo=None)
