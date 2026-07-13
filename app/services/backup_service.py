"""
Backup service for Leviia Schedule.

Wraps the pure functions in scripts/backup_database.py (deliberately
framework-agnostic - see that module's docstring) so the admin UI can
create/list/download backups without duplicating logic. scripts/ never
depends on app/, so this direction (app -> scripts) is safe and doesn't
break that isolation.
"""

import logging
import os
import tempfile
from typing import Any

from scripts.backup_config import BackupConfig
from scripts.backup_database import (
    cleanup_local_backups,
    cleanup_s3_backups,
    create_backup,
    download_from_s3,
    list_backups,
    send_backup_notification,
)


class BackupService:
    """Logique métier pour la gestion des sauvegardes depuis l'admin."""

    @staticmethod
    def _logger() -> logging.Logger:
        return logging.getLogger("leviia.backup")

    @staticmethod
    def get_config() -> BackupConfig:
        return BackupConfig.from_env()

    @staticmethod
    def list_all_backups() -> dict[str, Any]:
        config = BackupService.get_config()
        return list_backups(config, BackupService._logger())

    @staticmethod
    def create_now() -> dict[str, Any]:
        """Crée une sauvegarde immédiate (local et/ou S3 selon la
        config) et envoie l'alerte email si configurée. Refuse si
        BACKUP_ENABLED=false - même garde-fou que le script cron, pour
        que la désactivation soit effective partout (pas seulement pour
        le planning automatique)."""
        config = BackupService.get_config()
        logger = BackupService._logger()

        if not config.enabled:
            logger.info("Sauvegarde manuelle refusée (BACKUP_ENABLED=false)")
            return {
                "success": False,
                "local": None,
                "s3": None,
                "timestamp": None,
                "errors": ["Les sauvegardes sont désactivées (BACKUP_ENABLED=false)"],
            }

        results = create_backup(config, logger)
        send_backup_notification(config, results, logger)
        return results

    @staticmethod
    def cleanup_now() -> dict[str, Any]:
        config = BackupService.get_config()
        logger = BackupService._logger()
        local_count, local_message = cleanup_local_backups(config, logger)
        s3_count, s3_message = cleanup_s3_backups(config, logger)
        return {
            "local": {"count": local_count, "message": local_message},
            "s3": {"count": s3_count, "message": s3_message},
        }

    @staticmethod
    def get_local_backup_path(filename: str) -> str | None:
        """Chemin absolu d'une sauvegarde locale à partir de son nom de
        fichier, avec protection contre la traversée de chemin. Retourne
        None si le fichier n'existe pas, sort du dossier de sauvegarde,
        ou ne correspond pas au préfixe attendu."""
        config = BackupService.get_config()
        if not config.local_dir or not filename.startswith(config.backup_prefix):
            return None

        local_dir = os.path.abspath(config.local_dir)
        candidate = os.path.abspath(os.path.join(local_dir, filename))
        if not candidate.startswith(local_dir + os.sep):
            return None
        if not os.path.isfile(candidate):
            return None
        return candidate

    @staticmethod
    def download_s3_backup_to_temp(key: str) -> str | None:
        """Télécharge une sauvegarde S3 vers un fichier temporaire et
        retourne son chemin (à supprimer par l'appelant après envoi),
        ou None en cas d'échec."""
        config = BackupService.get_config()
        if not config.s3_enabled or not config.s3_bucket:
            return None

        logger = BackupService._logger()
        suffix = os.path.splitext(key)[1] or ".bin"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
            tmp_path = tmp_file.name

        success, message = download_from_s3(
            config.s3_bucket, key, tmp_path, config, logger
        )
        if not success:
            logger.error(message)
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return None
        return tmp_path
