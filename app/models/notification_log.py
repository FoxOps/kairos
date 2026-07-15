"""
NotificationLog model for Leviia Schedule.

This module contains the NotificationLog model, used to record which
weekly email notifications (shift/on-call reminders) have already been
sent, so a re-run of the notification scripts for the same period does
not send duplicate emails.
"""

from datetime import date

from app import db
from app.models.base import BaseModel


class NotificationLog(BaseModel):
    """
    NotificationLog model for tracking sent email notifications.

    Attributes:
        user_id: Foreign key to User
        notification_type: "shift_weekly" or "oncall_weekly"
        period_start: First day covered by the notification (the Monday
            for shift_weekly, the Friday for oncall_weekly) - used as the
            idempotency key together with user_id/notification_type.
    """

    __tablename__ = "notification_log"

    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    notification_type = db.Column(db.String(20), nullable=False)
    period_start = db.Column(db.Date, nullable=False)

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "notification_type",
            "period_start",
            name="uq_notification_log_user_type_period",
        ),
    )

    @classmethod
    def already_sent(
        cls, user_id: int, notification_type: str, period_start: date
    ) -> bool:
        """True if this notification has already been recorded as sent."""
        return (
            cls.query.filter_by(
                user_id=user_id,
                notification_type=notification_type,
                period_start=period_start,
            ).first()
            is not None
        )

    def __repr__(self) -> str:
        return (
            f"<NotificationLog {self.notification_type} user={self.user_id} "
            f"period_start={self.period_start}>"
        )
