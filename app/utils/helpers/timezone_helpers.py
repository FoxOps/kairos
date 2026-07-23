"""
Timezone helpers for the naive wall-clock datetimes Shift/OnCall store.

Shifts/on-calls are stored as naive wall-clock datetimes meaning "local
time in the organization's default_timezone" - never UTC, never the
server's own local time. `to_viewer_timezone`/`to_org_timezone` translate
that canonical value to/from a specific viewer's effective_timezone(),
for the FullCalendar JSON API (display and drag & drop input). `org_now()`
gives "now" in that same canonical representation, for "is this happening
right now" comparisons.

FullCalendar itself is configured with `timeZone: 'UTC'`
(fullcalendar-config.js) so it never reinterprets these numbers against
the browser's own system clock - the server does all the real
conversion via zoneinfo, avoiding the need for a moment-timezone/luxon
plugin (this app has no JS build step / bundled npm dependencies).
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


def parse_fullcalendar_datetime(iso_str: str, viewer) -> datetime:
    """FullCalendar's timeZone: 'UTC' (fullcalendar-config.js) means an
    ISO string coming back from a drag & drop / shift-creation request
    carries the viewer's own wall-clock digits under a "Z"/offset
    suffix that's just a serialization artifact, never a real UTC
    instant. Strips that tzinfo and converts from the viewer's
    effective_timezone() to the org's canonical one, ready for storage
    - the exact parse+convert sequence previously duplicated at every
    api_create_shift/api_update_shift/api_update_oncall call site."""
    naive = datetime.fromisoformat(iso_str.replace("Z", "+00:00")).replace(tzinfo=None)
    return to_org_timezone(naive, viewer)


def org_now() -> datetime:
    """Current time as a naive org-tz wall clock datetime - the same
    representation Shift/OnCall store, for "is this happening right now"
    comparisons like OnCall.is_active(). Deliberately not `datetime.now()`
    (the server process's own local time, which can differ from the
    organization's configured default_timezone by the server's UTC
    offset - the bug this function exists to avoid reintroducing)."""
    return datetime.now(_org_timezone()).replace(tzinfo=None)
