"""
Common helper functions for Leviia Schedule.

This module provides general utility functions used throughout the application.
"""

from datetime import datetime, date, time, timedelta
from typing import Optional, Union
from flask_login import current_user


def format_date(d: date, format_str: str = "%Y-%m-%d") -> str:
    """
    Format a date object as a string.
    
    Args:
        d: Date object to format
        format_str: Format string (default: YYYY-MM-DD)
        
    Returns:
        Formatted date string
    """
    if d is None:
        return ""
    return d.strftime(format_str)


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format a datetime object as a string.
    
    Args:
        dt: Datetime object to format
        format_str: Format string (default: YYYY-MM-DD HH:MM:SS)
        
    Returns:
        Formatted datetime string
    """
    if dt is None:
        return ""
    return dt.strftime(format_str)


def format_time(t: time, format_str: str = "%H:%M") -> str:
    """
    Format a time object as a string.
    
    Args:
        t: Time object to format
        format_str: Format string (default: HH:MM)
        
    Returns:
        Formatted time string
    """
    if t is None:
        return ""
    return t.strftime(format_str)


def parse_date(date_str: str, format_str: str = "%Y-%m-%d") -> Optional[date]:
    """
    Parse a string into a date object.
    
    Args:
        date_str: String to parse
        format_str: Format string (default: YYYY-MM-DD)
        
    Returns:
        Date object or None if parsing fails
    """
    try:
        return datetime.strptime(date_str, format_str).date()
    except (ValueError, TypeError):
        return None


def parse_datetime(dt_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
    """
    Parse a string into a datetime object.
    
    Args:
        dt_str: String to parse
        format_str: Format string (default: YYYY-MM-DD HH:MM:SS)
        
    Returns:
        Datetime object or None if parsing fails
    """
    try:
        return datetime.strptime(dt_str, format_str)
    except (ValueError, TypeError):
        return None


def get_current_year() -> int:
    """Get the current year."""
    return datetime.now().year


def get_current_month() -> int:
    """Get the current month (1-12)."""
    return datetime.now().month


def get_days_in_month(year: int, month: int) -> int:
    """
    Get the number of days in a month.
    
    Args:
        year: Year
        month: Month (1-12)
        
    Returns:
        Number of days in the month
    """
    if month == 12:
        return (date(year + 1, 1, 1) - date(year, 12, 1)).days
    else:
        return (date(year, month + 1, 1) - date(year, month, 1)).days


# ---------------------------------------------------------------------------
# Permission helper functions (for compatibility with existing code)
# ---------------------------------------------------------------------------

def can_add_shift(user=None, date=None, shift_type_id=None):
    """
    Check if a user can add a shift on a specific date.
    
    Args:
        user: User to check (default: current_user)
        date: Date to check (default: today)
        shift_type_id: Shift type ID to check
        
    Returns:
        True if user can add a shift, False otherwise
    """
    from app.models import Shift
    
    if user is None:
        user = current_user
    
    if date is None:
        date = datetime.now().date()
    
    if not user or not user.is_authenticated:
        return False
    
    # Check if user already has a shift on this date
    existing_shift = Shift.query.filter(
        Shift.user_id == user.id,
        Shift.date == date
    ).first()
    
    return existing_shift is None


def can_add_leave(user=None, start_date=None, end_date=None):
    """
    Check if a user can add a leave for a specific period.
    
    Args:
        user: User to check (default: current_user)
        start_date: Start date of leave
        end_date: End date of leave
        
    Returns:
        True if user can add leave, False otherwise
    """
    from app.models import Leave
    
    if user is None:
        user = current_user
    
    if start_date is None or end_date is None:
        return False
    
    if not user or not user.is_authenticated:
        return False
    
    # Check if user already has a leave overlapping with this period
    overlapping_leave = Leave.query.filter(
        Leave.user_id == user.id,
        Leave.start_date <= end_date,
        Leave.end_date >= start_date
    ).first()
    
    return overlapping_leave is None


def can_add_oncall(user=None, start_time=None, end_time=None):
    """
    Check if a user can add an on-call duty for a specific period.
    
    Args:
        user: User to check (default: current_user)
        start_time: Start datetime of on-call
        end_time: End datetime of on-call
        
    Returns:
        True if user can add on-call, False otherwise
    """
    from app.models import OnCall
    
    if user is None:
        user = current_user
    
    if start_time is None or end_time is None:
        return False
    
    if not user or not user.is_authenticated:
        return False
    
    # Check if user already has an on-call overlapping with this period
    overlapping_oncall = OnCall.query.filter(
        OnCall.user_id == user.id,
        OnCall.start_time <= end_time,
        OnCall.end_time >= start_time
    ).first()
    
    return overlapping_oncall is None
