"""
Leviia Schedule - Configuration des notifications par email
=============================================================

Ce module contient la configuration pour l'envoi des notifications par
email (rappels de shifts et d'astreintes). Suit le même pattern que
scripts/backup_config.py (dataclass chargée depuis les variables
d'environnement, utilisée par les scripts autonomes déclenchés via cron -
pas de scheduler intégré à l'application Flask).

Variables d'environnement disponibles:
- NOTIFICATIONS_ENABLED: Activer/désactiver l'envoi des notifications (true/false)
- NOTIFICATION_FROM_EMAIL: Adresse email de l'expéditeur
- SMTP_HOST: Serveur SMTP
- SMTP_PORT: Port SMTP (par défaut: 587)
- SMTP_USERNAME: Nom d'utilisateur SMTP
- SMTP_PASSWORD: Mot de passe SMTP
- SMTP_USE_TLS: Utiliser TLS/STARTTLS (true/false)
- SMTP_TIMEOUT: Délai d'attente de connexion SMTP en secondes (par défaut: 10)
- NOTIFICATION_APP_BASE_URL: URL de base de l'application, pour le lien
  "voir le planning" dans les emails (optionnel, pas de lien si absent)
"""

import os
from dataclasses import dataclass


@dataclass
class NotificationConfig:
    """Configuration complète pour l'envoi des notifications par email."""

    enabled: bool = False

    from_email: str | None = None

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    smtp_timeout: int = 10

    app_base_url: str | None = None

    @classmethod
    def from_env(cls) -> "NotificationConfig":
        """Charge la configuration depuis les variables d'environnement."""

        def get_bool(env_var: str, default: bool = False) -> bool:
            value = os.environ.get(env_var, "").lower()
            return value in ("true", "1", "yes", "y") if value else default

        def get_int(env_var: str, default: int = 0) -> int:
            try:
                return int(os.environ.get(env_var, default))
            except ValueError:
                return default

        def get_str(env_var: str, default: str | None = None) -> str | None:
            value = os.environ.get(env_var)
            return value if value else default

        return cls(
            enabled=get_bool("NOTIFICATIONS_ENABLED", False),
            from_email=get_str("NOTIFICATION_FROM_EMAIL"),
            smtp_host=get_str("SMTP_HOST"),
            smtp_port=get_int("SMTP_PORT", 587),
            smtp_username=get_str("SMTP_USERNAME"),
            smtp_password=get_str("SMTP_PASSWORD"),
            smtp_use_tls=get_bool("SMTP_USE_TLS", True),
            smtp_timeout=get_int("SMTP_TIMEOUT", 10),
            app_base_url=get_str("NOTIFICATION_APP_BASE_URL"),
        )

    def is_configured(self) -> bool:
        """True si assez d'informations sont réunies pour tenter un envoi."""
        return bool(self.enabled and self.from_email and self.smtp_host)


# Instance globale de configuration
config = NotificationConfig.from_env()
