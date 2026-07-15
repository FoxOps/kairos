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
    """Business logic for managing backups from the admin UI."""

    @staticmethod
    def _logger() -> logging.Logger:
        return logging.getLogger("leviia.backup")

    @staticmethod
    def get_config() -> BackupConfig:
        """Env config, with retention_days/max_backups overridden by any
        DB-stored Setting (admin-editable at /admin/settings). This only
        affects admin-UI-triggered actions (create_now/cleanup_now/
        list_all_backups below) - the standalone cron-invoked
        scripts/backup_database.py stays 100% env-var-driven by design,
        preserving its "never imports app.*" isolation guarantee (see
        tests/unit/test_backup_database.py). Silently skips the
        DB override (env-only) when called outside a Flask app context -
        this method predates the Settings feature and some callers
        (tests, scripts) still invoke it without one."""
        config = BackupConfig.from_env()

        try:
            from app.services.settings_service import SettingsService

            retention_days = SettingsService.get_backup_retention_days()
            if retention_days is not None:
                config.retention_days = retention_days

            max_backups = SettingsService.get_backup_max_backups()
            if max_backups is not None:
                config.max_backups = max_backups
        except RuntimeError:
            pass

        return config

    @staticmethod
    def list_all_backups() -> dict[str, Any]:
        config = BackupService.get_config()
        return list_backups(config, BackupService._logger())

    @staticmethod
    def create_now() -> dict[str, Any]:
        """Create an immediate backup (local and/or S3 depending on
        config) and send the email alert if configured. Refuses if
        BACKUP_ENABLED=false - same guard as the cron script, so the
        disable flag is effective everywhere (not just for the automatic
        schedule)."""
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
        """Absolute path of a local backup from its file name, with
        path-traversal protection. Returns None if the file doesn't
        exist, escapes the backup directory, or doesn't match the
        expected prefix."""
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
        """Download an S3 backup to a temp file and return its path (to
        be removed by the caller after sending), or None on failure."""
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
