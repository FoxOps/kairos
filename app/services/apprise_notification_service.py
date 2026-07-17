"""
Apprise external notification service for Leviia Schedule.

Sends outbound notifications to admin-configured external destinations
(Slack, Discord, Telegram, generic webhooks...) via the Apprise library.
Not to be confused with NotificationService (weekly reminder emails,
cron-only) or AppNotificationService (in-app bell icon) - see CLAUDE.md
"External notifications (Apprise)".
"""

import apprise
from flask_babel import gettext as _

from app.models import NotificationTarget
from app.repositories.notification_target_repository import (
    NotificationTargetRepository,
)
from app.services.settings_service import SettingsService
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AppriseNotificationService:
    """Outbound external notifications (Slack/Discord/Telegram/webhooks)."""

    @staticmethod
    def _send_to_target(target: NotificationTarget, title: str, body: str) -> None:
        apobj = apprise.Apprise()
        apobj.add(target.apprise_url)
        apobj.notify(title=title, body=body)

    @staticmethod
    def notify(category: str, title: str, body: str) -> None:
        """Fire-and-forget, to every enabled target subscribed to
        category: never raises. A failure here must never break the
        business action that triggered it - same guarantee as
        AuditService.log()."""
        try:
            if not SettingsService.get_apprise_notifications_enabled():
                return
            targets = NotificationTargetRepository.list_enabled_for_category(category)
            for target in targets:
                try:
                    AppriseNotificationService._send_to_target(target, title, body)
                except Exception:
                    logger.exception(
                        "Échec d'envoi Apprise vers la cible id=%s (catégorie=%s)",
                        target.id,
                        category,
                    )
        except Exception:
            logger.exception(
                "Échec du service de notifications externes (catégorie=%s)", category
            )

    @staticmethod
    def notify_to_targets(target_ids: list[int], title: str, body: str) -> None:
        """Fire-and-forget, to a specific user-selected list of target ids
        (see User.get_apprise_shift_target_ids()/get_apprise_oncall_target_ids())
        rather than every target subscribed to a category - never raises.
        Silently skips ids that no longer resolve to an enabled target
        (deleted/disabled since the user picked it), same resilience
        philosophy as notify()."""
        try:
            if not SettingsService.get_apprise_notifications_enabled():
                return
            targets = NotificationTargetRepository.get_by_ids(target_ids)
            for target in targets:
                if not target.enabled:
                    continue
                try:
                    AppriseNotificationService._send_to_target(target, title, body)
                except Exception:
                    logger.exception(
                        "Échec d'envoi Apprise vers la cible id=%s", target.id
                    )
        except Exception:
            logger.exception("Échec du service de notifications externes (cibles)")

    @staticmethod
    def send_test(target: NotificationTarget) -> tuple[bool, str | None]:
        """Admin 'Test' button path - does not swallow exceptions, the
        caller (route) surfaces the real success/failure to the admin."""
        apobj = apprise.Apprise()
        if not apobj.add(target.apprise_url):
            return False, _("URL Apprise invalide.")

        ok = apobj.notify(
            title=_("Test de notification - Leviia Schedule"),
            body=_(
                "Ceci est une notification de test envoyée depuis "
                "/admin/notification-targets."
            ),
        )
        if ok:
            return True, None
        return False, _("Échec de l'envoi (voir les logs pour le détail).")
