"""
Shift automation utilities for Leviia Schedule.

This module provides automation functionality for generating shifts
and managing shift rotations.
"""

from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any
from app import db


def generate_shifts(start_date: date, end_date: date, users: List, 
                    shift_types: List, pattern: Optional[Dict] = None) -> List:
    """
    Generate shifts for a date range based on a pattern.
    
    Args:
        start_date: Start date of the period
        end_date: End date of the period
        users: List of users to assign shifts to
        shift_types: List of available shift types
        pattern: Optional pattern for shift generation
        
    Returns:
        List of generated shift dictionaries
    """
    from app.models.shift import Shift
    
    generated_shifts = []
    current_date = start_date
    
    while current_date <= end_date:
        # For each day, generate shifts based on the pattern
        # This is a simplified version - the actual implementation
        # would use the pattern to determine which shifts to create
        
        for user in users:
            for shift_type in shift_types:
                # Create a shift for this user and shift type
                shift_data = {
                    'user_id': user.id,
                    'shift_type_id': shift_type.id,
                    'date': current_date,
                    'start_time': datetime.combine(current_date, datetime.min.time()),
                    'end_time': datetime.combine(current_date, datetime.max.time())
                }
                generated_shifts.append(shift_data)
        
        current_date += timedelta(days=1)
    
    return generated_shifts


def check_shift_conflicts(user_id: int, start_time: datetime, end_time: datetime) -> bool:
    """
    Check if a shift conflicts with existing shifts for a user.
    
    Args:
        user_id: User ID to check
        start_time: Proposed start time
        end_time: Proposed end time
        
    Returns:
        True if there is a conflict, False otherwise
    """
    from app.models.shift import Shift
    
    # Check for overlapping shifts
    conflicting_shifts = Shift.query.filter(
        Shift.user_id == user_id,
        Shift.start_time < end_time,
        Shift.end_time > start_time
    ).all()
    
    return len(conflicting_shifts) > 0


def generate_oncall_rotations(users: List, start_date: date, 
                             rotation_order: Optional[List[int]] = None) -> List:
    """
    Generate on-call rotations for a list of users.
    
    Args:
        users: List of users to include in rotation
        start_date: Start date of the rotation
        rotation_order: Optional list of user IDs in rotation order
        
    Returns:
        List of generated on-call dictionaries
    """
    from app.models.oncall import OnCall
    
    if rotation_order is None:
        rotation_order = [user.id for user in users]
    
    generated_oncalls = []
    
    # Simple rotation: each user gets one day in order
    for i, user_id in enumerate(rotation_order):
        oncall_date = start_date + timedelta(days=i)
        oncall_data = {
            'user_id': user_id,
            'start_time': datetime.combine(oncall_date, datetime.min.time()),
            'end_time': datetime.combine(oncall_date + timedelta(days=1), datetime.min.time())
        }
        generated_oncalls.append(oncall_data)
    
    return generated_oncalls


def check_oncall_conflicts(user_id: int, start_time: datetime, end_time: datetime) -> bool:
    """
    Check if an on-call period conflicts with existing on-call duties for a user.
    
    Args:
        user_id: User ID to check
        start_time: Proposed start time
        end_time: Proposed end time
        
    Returns:
        True if there is a conflict, False otherwise
    """
    from app.models.oncall import OnCall
    
    # Check for overlapping on-call duties
    conflicting_oncalls = OnCall.query.filter(
        OnCall.user_id == user_id,
        OnCall.start_time < end_time,
        OnCall.end_time > start_time
    ).all()
    
    return len(conflicting_oncalls) > 0
