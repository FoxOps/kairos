"""
Repositories module for Leviia Schedule.

This module contains the data access layer that abstracts the database
operations. Each repository handles CRUD operations for a specific model.

Repositories:
- user_repository: User and Group data access
- shift_repository: Shift and ShiftType data access
- oncall_repository: OnCall data access
- leave_repository: Leave data access
"""

from app.repositories.leave_repository import LeaveRepository
from app.repositories.oncall_repository import OnCallRepository
from app.repositories.shift_repository import ShiftRepository, ShiftTypeRepository
from app.repositories.user_repository import GroupRepository, UserRepository

__all__ = [
    "UserRepository",
    "GroupRepository",
    "ShiftRepository",
    "ShiftTypeRepository",
    "OnCallRepository",
    "LeaveRepository",
]
