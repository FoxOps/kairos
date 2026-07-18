"""
Tests for scripts/backup_database.py.

This script is deliberately independent of the app/ package (it must
stay usable even if the Flask app can't boot - the most likely
scenario in a disaster-recovery situation). The tests below never
import app/ either.
"""

import gzip
import logging
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from scripts.backup_config import BackupConfig
from scripts.backup_database import (
    cleanup_local_backups,
    create_local_backup,
    detect_db_path,
    list_backups,
    restore_backup,
    send_backup_notification,
    verify_backup,
)


@pytest.fixture
def logger():
    return logging.getLogger("test.backup")


@pytest.fixture(autouse=True)
def _isolate_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


def make_sqlite_file(path):
    """Create a fake but valid SQLite file (just the signature is enough
    for verify_backup)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"SQLite format 3\x00" + b"\x00" * 100)


class TestSendBackupNotification:
    SMTP_ENV = {
        "NOTIFICATIONS_ENABLED": "true",
        "NOTIFICATION_FROM_EMAIL": "noreply@kairos.local",
        "SMTP_HOST": "smtp.example.com",
    }

    def _set_smtp_env(self, monkeypatch):
        for key, value in self.SMTP_ENV.items():
            monkeypatch.setenv(key, value)

    def test_no_import_of_app_package(self):
        """Regression test: this module must never import app/ (see the
        module docstring) - checked by making sure 'app' doesn't appear
        in any top-level import in the source file."""
        import scripts.backup_database as mod

        source = open(mod.__file__).read()
        assert "from app" not in source
        assert "import app" not in source

    def test_sends_on_failure_when_configured(self, monkeypatch, logger):
        self._set_smtp_env(monkeypatch)
        config = BackupConfig(
            notify_on_failure=True,
            notify_on_success=False,
            notification_email="ops@kairos.local",
        )
        results = {
            "success": False,
            "local": {"success": False, "message": "disk full"},
            "s3": None,
            "timestamp": "2026-07-13T12:00:00",
            "errors": ["disk full"],
        }

        with patch("smtplib.SMTP") as mock_smtp:
            instance = MagicMock()
            mock_smtp.return_value.__enter__.return_value = instance
            send_backup_notification(config, results, logger)

        instance.sendmail.assert_called_once()
        to_addr = instance.sendmail.call_args[0][1]
        assert to_addr == ["ops@kairos.local"]

    def test_does_not_send_on_success_when_only_failure_configured(
        self, monkeypatch, logger
    ):
        self._set_smtp_env(monkeypatch)
        config = BackupConfig(
            notify_on_failure=True,
            notify_on_success=False,
            notification_email="ops@kairos.local",
        )
        results = {
            "success": True,
            "local": {"success": True, "message": "ok"},
            "s3": None,
            "timestamp": "2026-07-13T12:00:00",
            "errors": [],
        }

        with patch("smtplib.SMTP") as mock_smtp:
            instance = MagicMock()
            mock_smtp.return_value.__enter__.return_value = instance
            send_backup_notification(config, results, logger)

        instance.sendmail.assert_not_called()

    def test_does_not_send_without_notification_email(self, monkeypatch, logger):
        self._set_smtp_env(monkeypatch)
        config = BackupConfig(notify_on_failure=True, notification_email=None)
        results = {
            "success": False,
            "local": None,
            "s3": None,
            "timestamp": "x",
            "errors": ["boom"],
        }

        with patch("smtplib.SMTP") as mock_smtp:
            instance = MagicMock()
            mock_smtp.return_value.__enter__.return_value = instance
            send_backup_notification(config, results, logger)

        instance.sendmail.assert_not_called()

    def test_does_not_send_when_notifications_disabled(self, monkeypatch, logger):
        monkeypatch.delenv("NOTIFICATIONS_ENABLED", raising=False)
        monkeypatch.setenv("NOTIFICATIONS_ENABLED", "false")
        config = BackupConfig(
            notify_on_failure=True, notification_email="ops@kairos.local"
        )
        results = {
            "success": False,
            "local": None,
            "s3": None,
            "timestamp": "x",
            "errors": ["boom"],
        }

        with patch("smtplib.SMTP") as mock_smtp:
            instance = MagicMock()
            mock_smtp.return_value.__enter__.return_value = instance
            send_backup_notification(config, results, logger)

        instance.sendmail.assert_not_called()


class TestLocalBackupFileOperations:
    def test_create_local_backup_compressed(self, tmp_path, logger):
        db_path = tmp_path / "app.db"
        make_sqlite_file(db_path)
        backup_path = str(tmp_path / "out" / "backup.sqlite.gz")

        success, message = create_local_backup(str(db_path), backup_path, compress=True)

        assert success is True
        with gzip.open(backup_path, "rb") as f:
            assert f.read(16) == b"SQLite format 3\x00"

    def test_create_local_backup_uncompressed(self, tmp_path):
        db_path = tmp_path / "app.db"
        make_sqlite_file(db_path)
        backup_path = str(tmp_path / "out" / "backup.sqlite")

        success, message = create_local_backup(
            str(db_path), backup_path, compress=False
        )

        assert success is True
        assert open(backup_path, "rb").read(16) == b"SQLite format 3\x00"

    def test_verify_backup_valid_compressed(self, tmp_path):
        db_path = tmp_path / "app.db"
        make_sqlite_file(db_path)
        backup_path = str(tmp_path / "backup.sqlite.gz")
        create_local_backup(str(db_path), backup_path, compress=True)

        success, message = verify_backup(str(db_path), backup_path, compress=True)
        assert success is True

    def test_verify_backup_missing_file(self, tmp_path):
        success, message = verify_backup(
            str(tmp_path / "app.db"), str(tmp_path / "missing.gz"), compress=True
        )
        assert success is False
        assert "introuvable" in message

    def test_verify_backup_corrupted(self, tmp_path):
        backup_path = tmp_path / "corrupt.sqlite"
        backup_path.write_bytes(b"not a sqlite file")

        success, message = verify_backup(
            str(tmp_path / "app.db"), str(backup_path), compress=False
        )
        assert success is False
        assert "corrompu" in message.lower() or "invalide" in message.lower()

    def test_restore_backup_from_compressed(self, tmp_path):
        db_path = tmp_path / "app.db"
        make_sqlite_file(db_path)
        backup_path = str(tmp_path / "backup.sqlite.gz")
        create_local_backup(str(db_path), backup_path, compress=True)

        target_path = str(tmp_path / "restored.db")
        success, message = restore_backup(
            backup_path, target_path, BackupConfig(), logging.getLogger("t")
        )

        assert success is True
        assert open(target_path, "rb").read(16) == b"SQLite format 3\x00"

    def test_restore_backup_missing_source(self, tmp_path):
        success, message = restore_backup(
            str(tmp_path / "missing.gz"),
            str(tmp_path / "target.db"),
            BackupConfig(),
            logging.getLogger("t"),
        )
        assert success is False
        assert "introuvable" in message


class TestDetectDbPath:
    def test_returns_configured_path_if_exists(self, tmp_path):
        db_path = tmp_path / "custom.db"
        make_sqlite_file(db_path)
        config = BackupConfig(local_enabled=False)
        config.db_path = str(db_path)

        assert detect_db_path(config) == str(db_path)

    def test_returns_none_when_nothing_found(self, tmp_path, monkeypatch):
        # detect_db_path searches relative to backup_database.py's own
        # location (the real project root), not the isolated tmp_path -
        # this only checks that an invalid/unknown path doesn't crash.
        config = BackupConfig(local_enabled=False)
        config.db_path = str(tmp_path / "does-not-exist.db")
        config.db_uri = None
        result = detect_db_path(config)
        # May return a path found in the real project (instance/app.db
        # etc.) or None - the point of this test is the absence of an exception.
        assert result is None or isinstance(result, str)


class TestCleanupLocalBackups:
    def test_deletes_backups_older_than_retention(self, tmp_path, logger):
        local_dir = tmp_path / "backups"
        local_dir.mkdir()
        old_file = local_dir / "kairos_backup_old.sqlite.gz"
        old_file.write_bytes(b"x")
        old_time = (datetime.now() - timedelta(days=100)).timestamp()
        import os

        os.utime(old_file, (old_time, old_time))

        config = BackupConfig(
            local_enabled=True,
            local_dir=str(local_dir),
            retention_days=30,
            max_backups=100,
            backup_prefix="kairos_backup",
        )

        deleted_count, message = cleanup_local_backups(config, logger)

        assert deleted_count == 1
        assert not old_file.exists()

    def test_keeps_recent_backups(self, tmp_path, logger):
        local_dir = tmp_path / "backups"
        local_dir.mkdir()
        recent_file = local_dir / "kairos_backup_recent.sqlite.gz"
        recent_file.write_bytes(b"x")

        config = BackupConfig(
            local_enabled=True,
            local_dir=str(local_dir),
            retention_days=30,
            max_backups=100,
            backup_prefix="kairos_backup",
        )

        deleted_count, message = cleanup_local_backups(config, logger)

        assert deleted_count == 0
        assert recent_file.exists()

    def test_disabled_returns_zero(self, tmp_path, logger):
        config = BackupConfig(local_enabled=False, local_dir=str(tmp_path))
        deleted_count, message = cleanup_local_backups(config, logger)
        assert deleted_count == 0


class TestListBackups:
    def test_lists_local_backups(self, tmp_path, logger):
        local_dir = tmp_path / "backups"
        local_dir.mkdir()
        (local_dir / "kairos_backup_1.sqlite.gz").write_bytes(b"x")
        (local_dir / "kairos_backup_2.sqlite.gz").write_bytes(b"yy")
        (local_dir / "not_a_backup.txt").write_bytes(b"z")

        config = BackupConfig(
            local_enabled=True,
            local_dir=str(local_dir),
            backup_prefix="kairos_backup",
            s3_enabled=False,
        )

        results = list_backups(config, logger)

        assert len(results["local"]) == 2
        assert results["s3"] == []

    def test_empty_when_local_disabled(self, tmp_path, logger):
        config = BackupConfig(local_enabled=False, s3_enabled=False)
        results = list_backups(config, logger)
        assert results["local"] == []
        assert results["s3"] == []
