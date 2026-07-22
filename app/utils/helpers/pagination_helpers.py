"""
Pagination helpers for the HTML schedule/on-call/leave pages.

Centralizes what used to be copy-pasted identically in
shift_routes.py/oncall_routes.py/leave_routes.py: the dropdown's fixed
choice list, and resolving the effective per_page. Before this, the
default was a hardcoded 20 and the ceiling didn't exist at all,
completely independent of SettingsService.get_items_per_page()/
get_max_per_page() - the admin-configurable settings at /admin/settings
that the public API (app/api/resources/shifts.py and friends) already
respects. An admin changing "items per page" there had no effect on
these three pages; it does now.
"""

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
