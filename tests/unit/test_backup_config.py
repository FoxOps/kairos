"""
Tests pour scripts/backup_config.py (chargement de la config sauvegardes
depuis les variables d'environnement).
"""

from datetime import datetime

import pytest

from scripts.backup_config import BackupConfig


@pytest.fixture(autouse=True)
def _isolate_cwd(tmp_path, monkeypatch):
    """BackupConfig.__post_init__ runs os.makedirs(local_dir) as soon as
    local_enabled=True (the default) - with local_dir="backups" (relative,
    also the default), that would create a real backups/ directory at the
    repo root on every instantiation. Isolates the CWD in a temp
    directory for every test in this module."""
    monkeypatch.chdir(tmp_path)


BACKUP_ENV_VARS = [
    "BACKUP_ENABLED",
    "BACKUP_LOCAL_ENABLED",
    "BACKUP_LOCAL_DIR",
    "BACKUP_S3_ENABLED",
    "BACKUP_S3_BUCKET",
    "BACKUP_S3_ENDPOINT",
    "BACKUP_S3_REGION",
    "BACKUP_S3_ACCESS_KEY",
    "BACKUP_S3_SECRET_KEY",
    "BACKUP_S3_PREFIX",
    "BACKUP_S3_USE_SSL",
    "BACKUP_RETENTION_DAYS",
    "BACKUP_MAX_BACKUPS",
    "BACKUP_COMPRESS",
    "BACKUP_INCLUDE_TIMESTAMP",
    "BACKUP_TIMESTAMP_FORMAT",
    "BACKUP_PREFIX",
    "DATABASE_URL",
    "SQLALCHEMY_DATABASE_URI",
    "BACKUP_NOTIFY_ON_SUCCESS",
    "BACKUP_NOTIFY_ON_FAILURE",
    "BACKUP_NOTIFICATION_EMAIL",
    "BACKUP_LOG_LEVEL",
    "BACKUP_LOG_FILE",
    "BACKUP_VERIFY",
]


def clear_backup_env(monkeypatch):
    for var in BACKUP_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


class TestBackupConfigDefaults:
    def test_disabled_by_default(self, monkeypatch):
        clear_backup_env(monkeypatch)
        config = BackupConfig.from_env()
        assert config.enabled is False

    def test_local_enabled_by_default(self, monkeypatch):
        clear_backup_env(monkeypatch)
        config = BackupConfig.from_env()
        assert config.local_enabled is True
        assert config.s3_enabled is False

    def test_no_dead_scaffolding_fields(self):
        """Regression test: encrypt/encryption_key/frequency were never
        read by backup_database.py - removed rather than documented as if
        they did something."""
        config = BackupConfig()
        assert not hasattr(config, "encrypt")
        assert not hasattr(config, "encryption_key")
        assert not hasattr(config, "frequency")


class TestBackupConfigFromEnv:
    def test_reads_core_variables(self, monkeypatch):
        clear_backup_env(monkeypatch)
        monkeypatch.setenv("BACKUP_ENABLED", "true")
        monkeypatch.setenv("BACKUP_S3_ENABLED", "true")
        monkeypatch.setenv("BACKUP_S3_BUCKET", "my-bucket")
        monkeypatch.setenv("BACKUP_S3_ENDPOINT", "http://minio:9000")
        monkeypatch.setenv("BACKUP_RETENTION_DAYS", "7")

        config = BackupConfig.from_env()

        assert config.enabled is True
        assert config.s3_enabled is True
        assert config.s3_bucket == "my-bucket"
        assert config.s3_endpoint == "http://minio:9000"
        assert config.retention_days == 7

    def test_reads_notification_variables(self, monkeypatch):
        clear_backup_env(monkeypatch)
        monkeypatch.setenv("BACKUP_NOTIFY_ON_SUCCESS", "true")
        monkeypatch.setenv("BACKUP_NOTIFY_ON_FAILURE", "false")
        monkeypatch.setenv("BACKUP_NOTIFICATION_EMAIL", "ops@kairos.local")

        config = BackupConfig.from_env()

        assert config.notify_on_success is True
        assert config.notify_on_failure is False
        assert config.notification_email == "ops@kairos.local"

    def test_detects_sqlite_db_path_from_database_url(self, monkeypatch, tmp_path):
        clear_backup_env(monkeypatch)
        monkeypatch.setenv("DATABASE_URL", "sqlite:///app.db")

        config = BackupConfig.from_env()

        assert config.db_uri == "sqlite:///app.db"
        assert config.db_path is not None
        assert config.db_path.endswith("app.db")


class TestBackupConfigFilenames:
    def test_get_backup_filename_with_compression(self):
        config = BackupConfig(compress=True, backup_prefix="test_backup")
        timestamp = datetime(2026, 7, 13, 12, 0, 0)
        filename = config.get_backup_filename(timestamp)
        assert filename == "test_backup_20260713_120000.sqlite.gz"

    def test_get_backup_filename_without_compression(self):
        config = BackupConfig(compress=False, backup_prefix="test_backup")
        timestamp = datetime(2026, 7, 13, 12, 0, 0)
        filename = config.get_backup_filename(timestamp)
        assert filename == "test_backup_20260713_120000.sqlite"

    def test_get_backup_filename_without_timestamp(self):
        config = BackupConfig(
            compress=False, include_timestamp=False, backup_prefix="test_backup"
        )
        filename = config.get_backup_filename()
        assert filename == "test_backup.sqlite"

    def test_get_backup_filename_preserves_db_extension(self):
        config = BackupConfig(compress=False, backup_prefix="test_backup")
        config.db_path = "/some/path/app.db"
        filename = config.get_backup_filename(datetime(2026, 7, 13, 12, 0, 0))
        assert filename.startswith("test_backup_20260713_120000.db")

    def test_get_local_backup_path(self, tmp_path):
        local_dir = str(tmp_path / "backups")
        config = BackupConfig(local_dir=local_dir, backup_prefix="test")
        path = config.get_local_backup_path(datetime(2026, 7, 13, 12, 0, 0))
        assert path.startswith(local_dir)

    def test_get_s3_key_with_prefix(self):
        config = BackupConfig(s3_prefix="kairos", backup_prefix="test")
        key = config.get_s3_key(datetime(2026, 7, 13, 12, 0, 0))
        assert key.startswith("kairos/")

    def test_get_s3_key_without_prefix(self):
        config = BackupConfig(s3_prefix="", backup_prefix="test")
        key = config.get_s3_key(datetime(2026, 7, 13, 12, 0, 0))
        assert not key.startswith("/")
