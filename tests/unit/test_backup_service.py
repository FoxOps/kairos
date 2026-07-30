"""
Tests for app/services/backup_service.py (support layer for the admin
UI, on top of scripts/backup_database.py's pure functions).
"""

import os

import pytest

from app.services.backup_service import BackupService


def make_sqlite_file(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"SQLite format 3\x00" + b"\x00" * 100)


@pytest.fixture(autouse=True)
def _isolate_backup_env(tmp_path, monkeypatch):
    """Isolate each test in a temp directory and disable S3, so
    BackupConfig.__post_init__ (os.makedirs) or create_now() never touch
    the real repo / the real dev database."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BACKUP_S3_ENABLED", raising=False)
    monkeypatch.setenv("BACKUP_LOCAL_DIR", str(tmp_path / "backups"))


class TestGetConfig:
    def test_returns_config_from_env(self, monkeypatch):
        monkeypatch.setenv("BACKUP_ENABLED", "true")
        config = BackupService.get_config()
        assert config.enabled is True

    def test_falls_back_to_env_without_app_context(self, monkeypatch):
        """No Flask app context here (deliberately, matching the rest of
        this file) - get_config() must not crash, just skip the DB
        override (can't query Setting without a context)."""
        monkeypatch.setenv("BACKUP_RETENTION_DAYS", "45")
        config = BackupService.get_config()
        assert config.retention_days == 45

    def test_db_override_wins_with_app_context(self, test_app, monkeypatch):
        monkeypatch.setenv("BACKUP_RETENTION_DAYS", "45")
        monkeypatch.setenv("BACKUP_MAX_BACKUPS", "10")
        with test_app.app_context():
            from app.services import SettingsService

            SettingsService.set_backup_retention(retention_days=60, max_backups=20)

            config = BackupService.get_config()
            assert config.retention_days == 60
            assert config.max_backups == 20

    def test_env_fallback_inside_app_context_when_no_db_row(
        self, test_app, monkeypatch
    ):
        monkeypatch.setenv("BACKUP_RETENTION_DAYS", "45")
        with test_app.app_context():
            config = BackupService.get_config()
            assert config.retention_days == 45


class TestListAllBackups:
    def test_empty_when_no_backups(self):
        results = BackupService.list_all_backups()
        assert results["local"] == []
        assert results["s3"] == []

    def test_lists_created_backup(self, tmp_path, monkeypatch):
        db_path = tmp_path / "source" / "app.db"
        make_sqlite_file(db_path)
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
        monkeypatch.setenv("BACKUP_ENABLED", "true")

        create_results = BackupService.create_now()
        assert create_results["success"] is True

        results = BackupService.list_all_backups()
        assert len(results["local"]) == 1


class TestCreateNow:
    def test_creates_local_backup(self, tmp_path, monkeypatch):
        db_path = tmp_path / "source" / "app.db"
        make_sqlite_file(db_path)
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
        monkeypatch.setenv("BACKUP_ENABLED", "true")

        results = BackupService.create_now()

        assert results["success"] is True
        assert results["local"]["success"] is True

    def test_refuses_when_disabled(self, tmp_path, monkeypatch):
        db_path = tmp_path / "source" / "app.db"
        make_sqlite_file(db_path)
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
        monkeypatch.delenv("BACKUP_ENABLED", raising=False)

        results = BackupService.create_now()

        assert results["success"] is False
        assert "BACKUP_ENABLED" in results["errors"][0]

    def test_notifies_on_failure_when_db_not_found(self, monkeypatch):
        """Enabled, but detect_db_path() can't locate a database - a
        real create_backup() failure (not the disabled-guard above),
        hitting the AppriseNotificationService.notify "failure" branch
        instead of the "success" one. detect_db_path() is monkeypatched
        because the real repo checkout has its own instance/app.db,
        which detect_db_path() would otherwise find regardless of
        DATABASE_URL/cwd (it resolves paths from the script's own
        file location, not the isolated tmp_path)."""
        monkeypatch.setenv("BACKUP_ENABLED", "true")
        monkeypatch.setattr(
            "scripts.backup_database.detect_db_path", lambda config: None
        )

        results = BackupService.create_now()

        assert results["success"] is False
        assert results["errors"]


class TestCleanupNow:
    def test_returns_counts(self):
        results = BackupService.cleanup_now()
        assert results["local"]["count"] == 0
        assert results["s3"]["count"] == 0


class TestGetLocalBackupPath:
    def test_returns_none_for_missing_file(self):
        assert BackupService.get_local_backup_path("kairos_backup_x.sqlite.gz") is None

    def test_returns_none_for_wrong_prefix(self, tmp_path, monkeypatch):
        local_dir = tmp_path / "backups"
        local_dir.mkdir()
        (local_dir / "not_a_backup.txt").write_text("x")
        monkeypatch.setenv("BACKUP_LOCAL_DIR", str(local_dir))

        assert BackupService.get_local_backup_path("not_a_backup.txt") is None

    def test_returns_none_for_path_traversal(self, tmp_path, monkeypatch):
        local_dir = tmp_path / "backups"
        local_dir.mkdir()
        monkeypatch.setenv("BACKUP_LOCAL_DIR", str(local_dir))
        (tmp_path / "secret.txt").write_text("secret")

        traversal_name = "kairos_backup_x/../../secret.txt"
        assert BackupService.get_local_backup_path(traversal_name) is None

    def test_returns_path_for_existing_backup(self, tmp_path, monkeypatch):
        local_dir = tmp_path / "backups"
        local_dir.mkdir()
        backup_file = local_dir / "kairos_backup_1.sqlite.gz"
        backup_file.write_bytes(b"x")
        monkeypatch.setenv("BACKUP_LOCAL_DIR", str(local_dir))

        result = BackupService.get_local_backup_path("kairos_backup_1.sqlite.gz")
        assert result is not None
        assert os.path.samefile(result, backup_file)


class TestDownloadS3BackupToTemp:
    def test_returns_none_when_s3_disabled(self):
        assert BackupService.download_s3_backup_to_temp("some/key.gz") is None

    def test_returns_temp_path_on_success(self, monkeypatch):
        monkeypatch.setenv("BACKUP_S3_ENABLED", "true")
        monkeypatch.setenv("BACKUP_S3_BUCKET", "my-bucket")

        def fake_download_from_s3(bucket, key, file_path, config, logger):
            with open(file_path, "wb") as f:
                f.write(b"data")
            return True, "ok"

        monkeypatch.setattr(
            "app.services.backup_service.download_from_s3", fake_download_from_s3
        )

        result = BackupService.download_s3_backup_to_temp("some/key.gz")
        assert result is not None
        assert os.path.isfile(result)
        os.remove(result)

    def test_returns_none_and_cleans_up_on_failure(self, monkeypatch):
        monkeypatch.setenv("BACKUP_S3_ENABLED", "true")
        monkeypatch.setenv("BACKUP_S3_BUCKET", "my-bucket")

        def fake_download_from_s3(bucket, key, file_path, config, logger):
            return False, "download failed"

        monkeypatch.setattr(
            "app.services.backup_service.download_from_s3", fake_download_from_s3
        )

        result = BackupService.download_s3_backup_to_temp("some/key.gz")
        assert result is None
