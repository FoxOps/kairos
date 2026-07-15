"""
Tests pour app/services/backup_service.py (couche support pour l'UI
admin, au-dessus des fonctions pures de scripts/backup_database.py).
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


class TestCleanupNow:
    def test_returns_counts(self):
        results = BackupService.cleanup_now()
        assert results["local"]["count"] == 0
        assert results["s3"]["count"] == 0


class TestGetLocalBackupPath:
    def test_returns_none_for_missing_file(self):
        assert BackupService.get_local_backup_path("leviia_backup_x.sqlite.gz") is None

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

        traversal_name = "leviia_backup_x/../../secret.txt"
        assert BackupService.get_local_backup_path(traversal_name) is None

    def test_returns_path_for_existing_backup(self, tmp_path, monkeypatch):
        local_dir = tmp_path / "backups"
        local_dir.mkdir()
        backup_file = local_dir / "leviia_backup_1.sqlite.gz"
        backup_file.write_bytes(b"x")
        monkeypatch.setenv("BACKUP_LOCAL_DIR", str(local_dir))

        result = BackupService.get_local_backup_path("leviia_backup_1.sqlite.gz")
        assert result is not None
        assert os.path.samefile(result, backup_file)


class TestDownloadS3BackupToTemp:
    def test_returns_none_when_s3_disabled(self):
        assert BackupService.download_s3_backup_to_temp("some/key.gz") is None
