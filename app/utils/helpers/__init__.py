"""
Helper utilities for Leviia Schedule.

This module provides general helper functions.
"""

from app.utils.helpers.common_helpers import (
    _get_overlapping_leave,
    _get_overlapping_oncall,
    _get_overlapping_shift,
    _has_overlapping_oncall,
    can_add_leave,
    can_add_oncall,
    can_add_shift,
    format_date,
    format_date_fr,
    format_datetime,
    format_time,
    get_bool,
    get_current_month,
    get_current_year,
    get_days_in_month,
    get_int,
    is_user_on_leave,
    is_user_on_shift,
    leave_keeps_minimum_headcount,
    parse_date,
    parse_datetime,
    shift_type_color,
)

__all__ = [
    "get_bool",
    "get_int",
    "format_date",
    "format_date_fr",
    "format_datetime",
    "format_time",
    "parse_date",
    "parse_datetime",
    "get_current_year",
    "get_current_month",
    "get_days_in_month",
    "can_add_shift",
    "can_add_leave",
    "can_add_oncall",
    "is_user_on_shift",
    "is_user_on_leave",
    "leave_keeps_minimum_headcount",
    "shift_type_color",
    "_has_overlapping_oncall",
    "_get_overlapping_leave",
    "_get_overlapping_shift",
    "_get_overlapping_oncall",
]
