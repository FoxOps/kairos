"""
Timezone helpers for the naive wall-clock datetimes Shift/OnCall store.

Shifts/on-calls are stored as naive wall-clock datetimes meaning "local
time in the organization's default_timezone" (see CLAUDE.md's
"Multi-timezone support" section). `to_viewer_timezone`/`to_org_timezone`
translate that canonical value to/from a specific viewer's
effective_timezone(), for the FullCalendar JSON API (display and drag &
drop input). `org_now()` gives "now" in that same canonical
representation, for "is this happening right now" comparisons.

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


def org_now() -> datetime:
    """Current time as a naive org-tz wall clock datetime - the same
    representation Shift/OnCall store, for "is this happening right now"
    comparisons like OnCall.is_active(). Deliberately not `datetime.now()`
    (the server process's own local time, which can differ from the
    organization's configured default_timezone by the server's UTC
    offset - the bug this function exists to avoid reintroducing)."""
    return datetime.now(_org_timezone()).replace(tzinfo=None)
