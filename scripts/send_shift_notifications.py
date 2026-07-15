#!/usr/bin/env python3
"""
Leviia Schedule - Envoi des rappels de shifts par email
=========================================================

Envoie un email récapitulatif à chaque utilisateur ayant au moins un
shift la semaine prochaine (lundi-vendredi). Un seul email par semaine
et par utilisateur - voir app/services/notification_service.py pour la
logique et NotificationLog pour la garde-fou anti-doublon.

À exécuter chaque dimanche (24h avant le début des shifts du lundi) via
cron - voir scripts/cron_example.sh pour un exemple d'entrée crontab.
Ne fait rien si NOTIFICATIONS_ENABLED n'est pas activé.

Utilisation:
    python scripts/send_shift_notifications.py

Variables d'environnement: voir scripts/notification_config.py.
"""

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402
from app.services import NotificationService  # noqa: E402
from scripts.notification_config import NotificationConfig  # noqa: E402

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> int:
    config = NotificationConfig.from_env()

    with app.app_context():
        from app.services import SettingsService

        # SettingsService.get_notifications_enabled() checks the
        # DB-stored Setting first (admin-editable at /admin/settings)
        # and falls back to the NOTIFICATIONS_ENABLED env var when no
        # override exists - see app/services/settings_service.py.
        # SMTP completeness (from_email/smtp_host) stays env-only, those
        # are secrets/deployment config, not migrated.
        if not (
            SettingsService.get_notifications_enabled()
            and config.from_email
            and config.smtp_host
        ):
            logger.info(
                "Notifications désactivées ou configuration SMTP incomplète "
                "(NOTIFICATIONS_ENABLED/NOTIFICATION_FROM_EMAIL/SMTP_HOST) - rien à faire."
            )
            return 0

        smtp_config = {
            "smtp_host": config.smtp_host,
            "smtp_port": config.smtp_port,
            "from_email": config.from_email,
            "smtp_username": config.smtp_username,
            "smtp_password": config.smtp_password,
            "smtp_use_tls": config.smtp_use_tls,
            "smtp_timeout": config.smtp_timeout,
        }

        result = NotificationService.send_weekly_shift_notifications(
            smtp_config, app_base_url=config.app_base_url
        )

    logger.info("Emails envoyés : %d (%s)", len(result.sent), ", ".join(result.sent))
    if result.skipped_already_sent:
        logger.info(
            "Déjà envoyés cette semaine, ignorés : %d",
            len(result.skipped_already_sent),
        )
    if result.failed:
        for email, error in result.failed:
            logger.error("Échec d'envoi pour %s : %s", email, error)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
