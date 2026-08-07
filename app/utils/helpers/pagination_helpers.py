"""
Pagination/filter-bar helpers for the HTML schedule/on-call/leave pages.

Centralizes what used to be (or would otherwise become) copy-pasted
identically in shift_routes.py/oncall_routes.py/leave_routes.py: the
per-page dropdown's fixed choice list and resolving the effective
per_page, plus (parse_date_range_filter()) the date_from/date_to
query-string parsing shared by all three pages' filter bar. Before
resolve_per_page(), the default was a hardcoded 20 and the ceiling
didn't exist at all, completely independent of
SettingsService.get_items_per_page()/get_max_per_page() - the
admin-configurable settings at /admin/settings that the public API
(app/api/resources/shifts.py and friends) already respects. An admin
changing "items per page" there had no effect on these three pages; it
does now.
"""

from datetime import date, datetime
from typing import Any

PER_PAGE_OPTIONS = [5, 10, 25, 50, 100]

# Sentinel meaning "show everything, no pagination" - a user-facing
# override (per_page=0 or -1 in the query string), not something
# SettingsService.get_max_per_page() should cap.
_UNLIMITED = 999999


def resolve_per_page(request_args: Any) -> int:
    """Effective per_page for a request: request_args["per_page"] if
    it's one of PER_PAGE_OPTIONS, the _UNLIMITED sentinel for 0/-1,
    otherwise SettingsService.get_items_per_page() - always capped by
    SettingsService.get_max_per_page() (except the explicit
    "unlimited" case, a deliberate full override)."""
    from app.services import SettingsService

    default = SettingsService.get_items_per_page()
    per_page = request_args.get("per_page", default, type=int)

    if per_page in (0, -1):
        return _UNLIMITED

    if per_page == _UNLIMITED:
        return _UNLIMITED

    if per_page not in PER_PAGE_OPTIONS:
        per_page = default

    return min(per_page, SettingsService.get_max_per_page())


def parse_date_range_filter(
    request_args: Any,
) -> tuple[date | None, date | None, str, str]:
    """Parses the date_from/date_to filter-bar query params shared by
    /schedule, /oncall, /leave - same "%Y-%m-%d" parsing as
    admin_audit_routes.py::audit_log(), centralized here since all
    three routes need it identically. Returns
    (date_from, date_to, date_from_str, date_to_str) - the str forms
    are what the template re-injects into the <input type="date">
    value, and come back empty on an invalid/unparseable input rather
    than echoing back a value that failed to parse."""
    date_from_str = request_args.get("date_from", "").strip()
    date_to_str = request_args.get("date_to", "").strip()
    date_from: date | None = None
    date_to: date | None = None

    # Parsed independently - one malformed field must not also discard
    # the other field's already-valid value.
    try:
        if date_from_str:
            date_from = datetime.strptime(date_from_str, "%Y-%m-%d").date()
    except ValueError:
        date_from_str = ""

    try:
        if date_to_str:
            date_to = datetime.strptime(date_to_str, "%Y-%m-%d").date()
    except ValueError:
        date_to_str = ""

    return date_from, date_to, date_from_str, date_to_str
