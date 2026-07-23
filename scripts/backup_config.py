"""
Kairos - Backup configuration
==============================================

This module holds the configuration for database backups.
Settings can be set via environment variables or edited directly.

Available environment variables:
- BACKUP_ENABLED: Enable/disable backups (true/false, default: false)
- BACKUP_LOCAL_ENABLED: Enable the local backup (true/false)
- BACKUP_S3_ENABLED: Enable the S3 backup (true/false)
- BACKUP_LOCAL_DIR: Local backup directory (default: backups/)
- BACKUP_S3_BUCKET: S3 bucket name
- BACKUP_S3_ENDPOINT: S3 endpoint (for S3-compatible services like MinIO)
- BACKUP_S3_REGION: S3 region
- BACKUP_S3_ACCESS_KEY: S3 access key
- BACKUP_S3_SECRET_KEY: S3 secret key
- BACKUP_S3_PREFIX: Prefix for files in the bucket
- BACKUP_RETENTION_DAYS: Number of days to keep backups
- BACKUP_COMPRESS: Compress backups (true/false)
- BACKUP_NOTIFY_ON_SUCCESS: Send an email on success (true/false)
- BACKUP_NOTIFY_ON_FAILURE: Send an email on failure (true/false)
- BACKUP_NOTIFICATION_EMAIL: Recipient email address for backup alerts
  (reuses the notifications SMTP configuration - see
  scripts/notification_config.py - so also subject to
  NOTIFICATIONS_ENABLED)
"""

import os
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class BackupConfig:
    """Full configuration for database backups."""

    # Overall enable flag (opt-in: no backup until explicitly enabled,
    # consistent with the email notifications pattern)
    enabled: bool = False

    # Local backup
    local_enabled: bool = True
    local_dir: str = "backups"

    # S3 backup
    s3_enabled: bool = False
    s3_bucket: str | None = None
    s3_endpoint: str | None = None  # None for AWS S3, URL for MinIO/etc
    s3_region: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_prefix: str = "kairos"
    s3_use_ssl: bool = True

    # Retention
    retention_days: int = 30
    max_backups: int = 30

    # Format and compression
    compress: bool = True

    # Timestamps
    include_timestamp: bool = True
    timestamp_format: str = "%Y%m%d_%H%M%S"

    # Filename
    backup_prefix: str = "kairos_backup"

    # Database
    db_path: str | None = None  # Path to the SQLite file
    db_uri: str | None = None  # Database URI

    # Email notifications (wired into app.utils.notifications - same
    # SMTP config as the shift/on-call reminders)
    notify_on_success: bool = False
    notify_on_failure: bool = True
    notification_email: str | None = None

    # Logging
    log_level: str = "INFO"
    log_file: str | None = None

    # Exclusions
    exclude_tables: list = field(default_factory=list)

    # Verification
    verify_backup: bool = True

    @classmethod
    def from_env(cls) -> "BackupConfig":
        """Loads the configuration from environment variables."""

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

        def get_str_default(env_var: str, default: str) -> str:
            value = os.environ.get(env_var)
            return value if value else default

        # Detect the database path
        db_uri = get_str("DATABASE_URL") or get_str("SQLALCHEMY_DATABASE_URI")
        db_path = None

        if db_uri and db_uri.startswith("sqlite:///"):
            # Extract the SQLite file path
            db_path = db_uri.replace("sqlite:///", "")
            if not os.path.isabs(db_path):
                # Path relative to the project root
                project_root = os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))
                )
                db_path = os.path.join(project_root, db_path)

        return cls(
            enabled=get_bool("BACKUP_ENABLED", False),
            local_enabled=get_bool("BACKUP_LOCAL_ENABLED", True),
            local_dir=get_str_default("BACKUP_LOCAL_DIR", "backups"),
            s3_enabled=get_bool("BACKUP_S3_ENABLED", False),
            s3_bucket=get_str("BACKUP_S3_BUCKET"),
            s3_endpoint=get_str("BACKUP_S3_ENDPOINT"),
            s3_region=get_str("BACKUP_S3_REGION"),
            s3_access_key=get_str("BACKUP_S3_ACCESS_KEY"),
            s3_secret_key=get_str("BACKUP_S3_SECRET_KEY"),
            s3_prefix=get_str_default("BACKUP_S3_PREFIX", "kairos"),
            s3_use_ssl=get_bool("BACKUP_S3_USE_SSL", True),
            retention_days=get_int("BACKUP_RETENTION_DAYS", 30),
            max_backups=get_int("BACKUP_MAX_BACKUPS", 30),
            compress=get_bool("BACKUP_COMPRESS", True),
            include_timestamp=get_bool("BACKUP_INCLUDE_TIMESTAMP", True),
            timestamp_format=get_str_default(
                "BACKUP_TIMESTAMP_FORMAT", "%Y%m%d_%H%M%S"
            ),
            backup_prefix=get_str_default("BACKUP_PREFIX", "kairos_backup"),
            db_path=db_path,
            db_uri=db_uri,
            notify_on_success=get_bool("BACKUP_NOTIFY_ON_SUCCESS", False),
            notify_on_failure=get_bool("BACKUP_NOTIFY_ON_FAILURE", True),
            notification_email=get_str("BACKUP_NOTIFICATION_EMAIL"),
            log_level=get_str_default("BACKUP_LOG_LEVEL", "INFO"),
            log_file=get_str("BACKUP_LOG_FILE"),
            verify_backup=get_bool("BACKUP_VERIFY", True),
        )

    def get_backup_filename(self, timestamp: datetime | None = None) -> str:
        """Generates the backup filename."""
        if timestamp is None:
            timestamp = datetime.now()

        timestamp_str = (
            timestamp.strftime(self.timestamp_format) if self.include_timestamp else ""
        )

        if timestamp_str:
            filename = f"{self.backup_prefix}_{timestamp_str}"
        else:
            filename = self.backup_prefix

        # Add the extension
        if self.db_path and self.db_path.endswith(".db"):
            filename += ".db"
        else:
            filename += ".sqlite"

        # Add the compression
        if self.compress:
            filename += ".gz"

        return filename

    def get_local_backup_path(self, timestamp: datetime | None = None) -> str:
        """Returns the full path for the local backup."""
        filename = self.get_backup_filename(timestamp)
        return os.path.join(self.local_dir, filename)

    def get_s3_key(self, timestamp: datetime | None = None) -> str:
        """Returns the S3 key for the backup."""
        filename = self.get_backup_filename(timestamp)
        if self.s3_prefix:
            return f"{self.s3_prefix}/{filename}"
        return filename


def get_config() -> BackupConfig:
    """Returns the backup configuration."""
    return BackupConfig.from_env()
