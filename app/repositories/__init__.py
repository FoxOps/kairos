"""
Repositories module for Leviia Schedule.

This module contains the data access layer that abstracts the database
operations. Each repository handles CRUD operations for a specific model.

Repositories:
- user_repository: User and Group data access
- shift_repository: Shift and ShiftType data access
- oncall_repository: OnCall data access
- leave_repository: Leave data access
- swap_request_repository: SwapRequest data access
- app_notification_repository: AppNotification (in-app notifications) data access
- audit_log_repository: AuditLog (audit trail) data access
- notification_target_repository: NotificationTarget (Apprise external
  notification destinations) data access
- service_account_repository: ServiceAccount (public REST API bearer
  credentials) data access
"""

from app.repositories.app_notification_repository import AppNotificationRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.leave_repository import LeaveRepository
from app.repositories.notification_target_repository import (
    NotificationTargetRepository,
)
from app.repositories.oncall_repository import OnCallRepository
from app.repositories.service_account_repository import ServiceAccountRepository
from app.repositories.shift_repository import ShiftRepository, ShiftTypeRepository
from app.repositories.swap_request_repository import SwapRequestRepository
from app.repositories.user_repository import GroupRepository, UserRepository

__all__ = [
    "UserRepository",
    "GroupRepository",
    "ShiftRepository",
    "ShiftTypeRepository",
    "OnCallRepository",
    "LeaveRepository",
    "SwapRequestRepository",
    "AppNotificationRepository",
    "AuditLogRepository",
    "NotificationTargetRepository",
    "ServiceAccountRepository",
]
