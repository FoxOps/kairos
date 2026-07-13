"""
Models module for Leviia Schedule.

This module contains all the SQLAlchemy models for the application,
organized by domain:
- User: User, Group
- Shift: Shift, ShiftType
- OnCall: OnCall
- Leave: Leave
- Base: BaseModel (common fields and methods)
"""

from app.models.automation_config import AutomationConfig
from app.models.base import BaseModel
from app.models.leave import Leave
from app.models.oncall import OnCall
from app.models.shift import Shift, ShiftType
from app.models.user import Group, User

__all__ = [
    "BaseModel",
    "User",
    "Group",
    "Shift",
    "ShiftType",
    "OnCall",
    "Leave",
    "AutomationConfig",
]
