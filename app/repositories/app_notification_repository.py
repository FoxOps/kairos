"""
AppNotification repository for Leviia Schedule.

Data access layer for the AppNotification model - no business logic, no
Flask request/response handling, just queries.
"""

from datetime import datetime, timezone

from app import db
from app.models import AppNotification


class AppNotificationRepository:
    """Data access for the AppNotification model."""

    @staticmethod
    def get_by_id(notification_id: int) -> AppNotification | None:
        return db.session.get(AppNotification, notification_id)

    @staticmethod
    def list_for_user(user_id: int, limit: int = 50) -> list[AppNotification]:
        return (
            AppNotification.query.filter_by(user_id=user_id)
            .order_by(AppNotification.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def count_unread(user_id: int) -> int:
        return AppNotification.query.filter_by(user_id=user_id, read_at=None).count()

    @staticmethod
    def create(
        user_id: int, notification_type: str, message: str, link: str | None = None
    ) -> AppNotification:
        notification = AppNotification(
            user_id=user_id,
            notification_type=notification_type,
            message=message,
            link=link,
        )
        db.session.add(notification)
        return notification

    @staticmethod
    def mark_all_read_for_user(user_id: int) -> None:
        AppNotification.query.filter_by(user_id=user_id, read_at=None).update(
            {"read_at": datetime.now(timezone.utc)}
        )

    @staticmethod
    def purge_read_for_user(user_id: int) -> int:
        """Delete user_id's already-read notifications. Returns the number deleted."""
        return AppNotification.query.filter(
            AppNotification.user_id == user_id,
            AppNotification.read_at.isnot(None),
        ).delete()
