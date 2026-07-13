"""
Leviia Schedule - Configuration de sauvegarde
==============================================

Ce module contient la configuration pour les sauvegardes de la base de données.
Les paramètres peuvent être définis via des variables d'environnement ou modifiés directement.

Variables d'environnement disponibles:
- BACKUP_ENABLED: Activer/désactiver les sauvegardes (true/false, défaut: false)
- BACKUP_LOCAL_ENABLED: Activer la sauvegarde locale (true/false)
- BACKUP_S3_ENABLED: Activer la sauvegarde S3 (true/false)
- BACKUP_LOCAL_DIR: Dossier de sauvegarde local (par défaut: backups/)
- BACKUP_S3_BUCKET: Nom du bucket S3
- BACKUP_S3_ENDPOINT: Endpoint S3 (pour S3-compatible comme MinIO)
- BACKUP_S3_REGION: Région S3
- BACKUP_S3_ACCESS_KEY: Clé d'accès S3
- BACKUP_S3_SECRET_KEY: Clé secrète S3
- BACKUP_S3_PREFIX: Préfixe pour les fichiers dans le bucket
- BACKUP_RETENTION_DAYS: Nombre de jours à conserver les sauvegardes
- BACKUP_COMPRESS: Compresser les sauvegardes (true/false)
- BACKUP_NOTIFY_ON_SUCCESS: Envoyer un email en cas de succès (true/false)
- BACKUP_NOTIFY_ON_FAILURE: Envoyer un email en cas d'échec (true/false)
- BACKUP_NOTIFICATION_EMAIL: Adresse email destinataire des alertes de
  sauvegarde (réutilise la configuration SMTP des notifications - voir
  scripts/notification_config.py - donc aussi soumis à
  NOTIFICATIONS_ENABLED)
"""

import os
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class BackupConfig:
    """Configuration complète pour les sauvegardes de la base de données."""

    # Activation générale (opt-in : pas de sauvegarde tant que ce n'est
    # pas explicitement activé, cohérent avec le pattern des
    # notifications par email)
    enabled: bool = False

    # Sauvegarde locale
    local_enabled: bool = True
    local_dir: str = "backups"

    # Sauvegarde S3
    s3_enabled: bool = False
    s3_bucket: str | None = None
    s3_endpoint: str | None = None  # None pour AWS S3, URL pour MinIO/etc
    s3_region: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_prefix: str = "leviia-schedule"
    s3_use_ssl: bool = True

    # Rétention
    retention_days: int = 30
    max_backups: int = 30

    # Format et compression
    compress: bool = True

    # Timestamps
    include_timestamp: bool = True
    timestamp_format: str = "%Y%m%d_%H%M%S"

    # Nom du fichier
    backup_prefix: str = "leviia_backup"

    # Base de données
    db_path: str | None = None  # Chemin vers le fichier SQLite
    db_uri: str | None = None  # URI de la base de données

    # Notifications par email (branchées sur app.utils.notifications -
    # même config SMTP que les rappels de shifts/astreinte)
    notify_on_success: bool = False
    notify_on_failure: bool = True
    notification_email: str | None = None

    # Logging
    log_level: str = "INFO"
    log_file: str | None = None

    # Exclusions
    exclude_tables: list = field(default_factory=list)

    # Vérification
    verify_backup: bool = True

    def __post_init__(self):
        """Initialisation après création de l'objet."""
        # Créer le dossier local s'il n'existe pas
        if self.local_enabled and self.local_dir:
            os.makedirs(self.local_dir, exist_ok=True)

    @classmethod
    def from_env(cls) -> "BackupConfig":
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

        def get_str_default(env_var: str, default: str) -> str:
            value = os.environ.get(env_var)
            return value if value else default

        # Détecter le chemin de la base de données
        db_uri = get_str("DATABASE_URL") or get_str("SQLALCHEMY_DATABASE_URI")
        db_path = None

        if db_uri and db_uri.startswith("sqlite:///"):
            # Extraire le chemin du fichier SQLite
            db_path = db_uri.replace("sqlite:///", "")
            if not os.path.isabs(db_path):
                # Chemin relatif à la racine du projet
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
            s3_prefix=get_str_default("BACKUP_S3_PREFIX", "leviia-schedule"),
            s3_use_ssl=get_bool("BACKUP_S3_USE_SSL", True),
            retention_days=get_int("BACKUP_RETENTION_DAYS", 30),
            max_backups=get_int("BACKUP_MAX_BACKUPS", 30),
            compress=get_bool("BACKUP_COMPRESS", True),
            include_timestamp=get_bool("BACKUP_INCLUDE_TIMESTAMP", True),
            timestamp_format=get_str_default(
                "BACKUP_TIMESTAMP_FORMAT", "%Y%m%d_%H%M%S"
            ),
            backup_prefix=get_str_default("BACKUP_PREFIX", "leviia_backup"),
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
        """Génère le nom du fichier de sauvegarde."""
        if timestamp is None:
            timestamp = datetime.now()

        timestamp_str = (
            timestamp.strftime(self.timestamp_format) if self.include_timestamp else ""
        )

        if timestamp_str:
            filename = f"{self.backup_prefix}_{timestamp_str}"
        else:
            filename = self.backup_prefix

        # Ajouter l'extension
        if self.db_path and self.db_path.endswith(".db"):
            filename += ".db"
        else:
            filename += ".sqlite"

        # Ajouter la compression
        if self.compress:
            filename += ".gz"

        return filename

    def get_local_backup_path(self, timestamp: datetime | None = None) -> str:
        """Retourne le chemin complet pour la sauvegarde locale."""
        filename = self.get_backup_filename(timestamp)
        return os.path.join(self.local_dir, filename)

    def get_s3_key(self, timestamp: datetime | None = None) -> str:
        """Retourne la clé S3 pour la sauvegarde."""
        filename = self.get_backup_filename(timestamp)
        if self.s3_prefix:
            return f"{self.s3_prefix}/{filename}"
        return filename


def get_config() -> BackupConfig:
    """Retourne la configuration de sauvegarde."""
    return BackupConfig.from_env()
