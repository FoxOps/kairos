"""
Models module for Kairos.

This module contains all the SQLAlchemy models for the application,
organized by domain:
- User: User, Group
- Shift: Shift, ShiftType
- OnCall: OnCall
- Leave: Leave
- SwapRequest: SwapRequest (shift exchange between users, admin validation)
- AppNotification: AppNotification (in-app notification, not the email-dedup NotificationLog)
- AuditLog: AuditLog (who did what, when - business CRUD + auth events, see AuditService)
- NotificationTarget: NotificationTarget (outbound Slack/Discord/Telegram/webhook
  destinations, see AppriseNotificationService - not NotificationLog/AppNotification)
- ServiceAccount: ServiceAccount (bearer credentials for the public REST API,
  see app/auth/service_account_auth.py and app/api/ - not a human User)
- Base: BaseModel (common fields and methods)
- Setting: Setting (generic DB-backed admin settings, distinct from AutomationConfig)
- AutomationRule: AutomationRule (configurable automation rules engine - org
  default + per-Group override, see app/utils/automation/rules/ - distinct
  from AutomationConfig, which only stores the on-call rotation order)
"""

from app.models.app_notification import AppNotification
from app.models.audit_log import AuditLog
from app.models.automation_config import AutomationConfig
from app.models.automation_rule import AutomationRule
from app.models.base import BaseModel
from app.models.leave import Leave
from app.models.notification_log import NotificationLog
from app.models.notification_target import NotificationTarget
from app.models.oncall import OnCall
from app.models.service_account import ServiceAccount
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
    "AutomationRule",
    "Setting",
    "NotificationLog",
    "SwapRequest",
    "AppNotification",
    "AuditLog",
    "NotificationTarget",
    "ServiceAccount",
]
