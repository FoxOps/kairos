"""
NotificationTarget model for Leviia Schedule.

Admin-managed destinations (Slack, Discord, Telegram, generic webhooks...)
for outbound external notifications sent via the Apprise library - see
AppriseNotificationService (app/services/apprise_notification_service.py)
for the single send path. Not to be confused with NotificationLog
(email send-dedup only) or AppNotification (in-app bell icon).
"""

import json

from app import db
from app.models.base import BaseModel


class NotificationTarget(BaseModel):
    """
    A single outbound notification destination.

    Attributes:
        name: Human-readable label shown in the admin UI (e.g. "Slack -
            #on-call").
        apprise_url: The Apprise service URL (e.g.
            "slack://TokenA/TokenB/TokenC/#channel"). Text, not String -
            some providers' URLs exceed 255 characters. Treated as a
            secret: never included in AuditService `details`, flash
            messages, or log lines - only `id`/`name` are.
        enabled: Per-target on/off switch, independent of the org-wide
            SettingsService.apprise_notifications_enabled master toggle.
        categories: JSON-encoded list of category strings (e.g.
            '["swap","backup"]") this target subscribes to. NULL/empty
            means "all categories" - see subscribes_to().
    """

    __tablename__ = "notification_target"

    name = db.Column(db.String(100), nullable=False)
    apprise_url = db.Column(db.Text, nullable=False)
    enabled = db.Column(db.Boolean, nullable=False, default=True, index=True)
    categories = db.Column(db.Text, nullable=True)

    def get_categories(self) -> list[str]:
        if not self.categories:
            return []
        try:
            return json.loads(self.categories)
        except json.JSONDecodeError:
            return []

    def set_categories(self, categories: list[str]) -> None:
        self.categories = json.dumps(categories) if categories else None

    def subscribes_to(self, category: str) -> bool:
        """True if this target should receive notifications of the given
        category - an empty/unset category list means "all categories"."""
        cats = self.get_categories()
        return not cats or category in cats

    def __repr__(self) -> str:
        return f"<NotificationTarget {self.name} enabled={self.enabled}>"
