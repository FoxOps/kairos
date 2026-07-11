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
- export_service: Export functionality (ICS, etc.)
- schedule_service: Calendar event aggregation (shifts + on-calls + leaves)
- automation_admin_service: Admin automation screens support (form
  parsing, period clearing, rotation order persistence)
"""

from app.services.user_service import UserService
from app.services.group_service import GroupService
from app.services.shift_service import ShiftService
from app.services.shift_type_service import ShiftTypeService
from app.services.oncall_service import OnCallService
from app.services.leave_service import LeaveService
from app.services.export_service import ExportService
from app.services.schedule_service import ScheduleService
from app.services.automation_admin_service import AutomationAdminService

__all__ = [
    'UserService',
    'GroupService',
    'ShiftService',
    'ShiftTypeService',
    'OnCallService',
    'LeaveService',
    'ExportService',
    'ScheduleService',
    'AutomationAdminService',
]
