"""
NotificationTarget repository for Leviia Schedule.

Data access layer for the NotificationTarget model - no business logic,
no Flask request/response handling, just queries. See
app/services/apprise_notification_service.py for the send logic.
"""

from app import db
from app.models import NotificationTarget


class NotificationTargetRepository:
    """Data access for the NotificationTarget model."""

    @staticmethod
    def get_by_id(target_id: int) -> NotificationTarget | None:
        return db.session.get(NotificationTarget, target_id)

    @staticmethod
    def get_all() -> list[NotificationTarget]:
        return NotificationTarget.query.order_by(NotificationTarget.name).all()

    @staticmethod
    def create(
        name: str,
        apprise_url: str,
        enabled: bool,
        categories: list[str],
    ) -> NotificationTarget:
        target = NotificationTarget(name=name, apprise_url=apprise_url, enabled=enabled)
        target.set_categories(categories)
        db.session.add(target)
        return target

    @staticmethod
    def delete(target: NotificationTarget) -> None:
        db.session.delete(target)

    @staticmethod
    def list_enabled_for_category(category: str) -> list[NotificationTarget]:
        """Enabled targets subscribed to the given category (or to "all",
        i.e. an empty categories list) - enabled=True is filtered at the
        SQL level (indexed), categories membership in Python since a
        JSON-in-Text column isn't portably queryable across SQLite/
        PostgreSQL and the target count is small (admin-managed list)."""
        targets = NotificationTarget.query.filter(
            NotificationTarget.enabled.is_(True)
        ).all()
        return [t for t in targets if t.subscribes_to(category)]
