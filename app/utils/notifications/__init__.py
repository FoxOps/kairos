"""
Notification utilities for Kairos.

This module provides email-sending functionality for the weekly
shift/on-call reminder notifications (scripts/send_shift_notifications.py,
scripts/send_oncall_notifications.py).
"""

from app.utils.notifications.email_sender import send_email

__all__ = ["send_email"]
