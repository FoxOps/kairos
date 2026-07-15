"""
Services module for Leviia Schedule.

This module contains the business logic services that handle the
application's core functionality. Each service encapsulates the
business logic for a specific domain.

Services:
- user_service: User management (+ admin CRUD)
- group_service: Group management (admin CRUD)
- shift_service: Shift management
- shift_type_service: Shift type management (admin CRUD)
- oncall_service: On-call management
- leave_service: Leave management
- swap_service: Shift exchange requests between users (admin validation)
- export_service: Export functionality (ICS, etc.)
- schedule_service: Calendar event aggregation (shifts + on-calls + leaves)
- automation_admin_service: Admin automation screens support (form
  parsing, period clearing, rotation order persistence)
- notification_service: Weekly email reminders (shifts + on-call),
  called by scripts/send_*_notifications.py, not by any Flask route
- app_notification_service: In-app notifications (bell icon), created
  synchronously by other services on domain events - not to be confused
  with notification_service above (emails, cron-only)
- backup_service: Admin UI support for database backups, wraps the
  pure functions in scripts/backup_database.py
- settings_service: Typed getters/setters for DB-backed admin settings
  (app/models/setting.py) - default timezone, public base URL, pagination,
  notifications toggle, backup retention, ICS token expiry. DB row wins
  when present, falls back live to app.config/env otherwise.
"""

from app.services.app_notification_service import AppNotificationService
from app.services.automation_admin_service import AutomationAdminService
from app.services.backup_service import BackupService
from app.services.export_service import ExportService
from app.services.group_service import GroupService
from app.services.leave_service import LeaveService
from app.services.notification_service import NotificationService
from app.services.oncall_service import OnCallService
from app.services.schedule_service import ScheduleService
from app.services.settings_service import SettingsService
from app.services.shift_service import ShiftService
from app.services.shift_type_service import ShiftTypeService
from app.services.swap_service import SwapService
from app.services.user_service import UserService

__all__ = [
    "UserService",
    "GroupService",
    "ShiftService",
    "ShiftTypeService",
    "OnCallService",
    "LeaveService",
    "SwapService",
    "ExportService",
    "ScheduleService",
    "AutomationAdminService",
    "NotificationService",
    "AppNotificationService",
    "BackupService",
    "SettingsService",
]
