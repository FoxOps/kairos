"""
Services module for Leviia Schedule.

This module contains the business logic services that handle the
application's core functionality. Each service encapsulates the
business logic for a specific domain.

Services:
- user_service: User management
- shift_service: Shift management
- oncall_service: On-call management
- leave_service: Leave management
- export_service: Export functionality (ICS, etc.)
- schedule_service: Calendar event aggregation (shifts + on-calls + leaves)
"""

from app.services.user_service import UserService
from app.services.shift_service import ShiftService
from app.services.oncall_service import OnCallService
from app.services.leave_service import LeaveService
from app.services.export_service import ExportService
from app.services.schedule_service import ScheduleService

__all__ = [
    'UserService',
    'ShiftService',
    'OnCallService',
    'LeaveService',
    'ExportService',
    'ScheduleService',
]
