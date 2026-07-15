"""
AppNotification model for Leviia Schedule.

In-app notification shown to a user (bell icon in the sidebar) - distinct
from NotificationLog (app/models/notification_log.py), which is purely an
idempotency guard for the weekly *email* reminders and is never displayed
in the UI. Don't confuse the two.
"""

from datetime import datetime, timezone

from app import db
from app.models.base import BaseModel


class AppNotification(BaseModel):
    """
    In-app notification for a single user.

    Attributes:
        user_id: Foreign key to User - recipient
        notification_type: Short machine-readable category
            (e.g. "swap_request_created", "swap_approved", "swap_rejected",
            "swap_reverted") - not currently used for filtering, kept for
            future grouping/preferences.
        message: Human-readable text shown to the user
        link: Optional relative URL to the relevant page (e.g. "/swaps")
        read_at: Timestamp when the user marked it read - null while unread
    """

    __tablename__ = "app_notification"

    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    notification_type = db.Column(db.String(30), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(255), nullable=True)
    read_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (db.Index("idx_app_notification_user_read", "user_id", "read_at"),)

    def is_unread(self) -> bool:
        return self.read_at is None

    def mark_read(self) -> None:
        """Set read_at (caller is responsible for commit)."""
        self.read_at = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"<AppNotification {self.id} - user={self.user_id} - {self.notification_type}>"
