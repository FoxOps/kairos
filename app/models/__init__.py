"""
Models module for Leviia Schedule.

This module contains all the SQLAlchemy models for the application,
organized by domain:
- User: User, Group
- Shift: Shift, ShiftType
- OnCall: OnCall
- Leave: Leave
- SwapRequest: SwapRequest (shift exchange between users, admin validation)
- AppNotification: AppNotification (in-app notification, not the email-dedup NotificationLog)
- Base: BaseModel (common fields and methods)
- Setting: Setting (generic DB-backed admin settings, distinct from AutomationConfig)
"""

from app.models.app_notification import AppNotification
from app.models.automation_config import AutomationConfig
from app.models.base import BaseModel
from app.models.leave import Leave
from app.models.notification_log import NotificationLog
from app.models.oncall import OnCall
from app.models.setting import Setting
from app.models.shift import Shift, ShiftType
from app.models.swap_request import SwapRequest
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
    "Setting",
    "NotificationLog",
    "SwapRequest",
    "AppNotification",
]
