#!/usr/bin/env python3
"""
Kairos - Automatic database backup
===============================================================

This script backs up the Kairos database:
- Local backup (file)
- S3 or S3-compatible storage (AWS S3, MinIO, etc.)

Usage:
    python scripts/backup_database.py [--local] [--s3] [--verify] [--cleanup]

Options:
    --local      Perform a local backup (enabled by default)
    --s3        Perform an S3 backup (disabled by default)
    --verify    Verify backup integrity
    --cleanup   Clean up old backups
    --config    Path to a JSON config file (optional)
    --help      Show help

Environment variables:
    See scripts/backup_config.py for the full list.

Examples:
    # Local backup only
    python scripts/backup_database.py --local

    # Local + S3 backup
    python scripts/backup_database.py --local --s3

    # Backup with cleanup of old backups
    python scripts/backup_database.py --local --cleanup

    # Full backup (local + S3 + verify + cleanup)
    python scripts/backup_database.py --local --s3 --verify --cleanup
"""

import argparse
import gzip
import hashlib
import json
import logging
import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta
from typing import Any

# Add the parent directory to the path to import the configuration
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError

    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False
    boto3 = None

from scripts.backup_config import BackupConfig, get_config

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================


def setup_logging(
    log_level: str = "INFO", log_file: str | None = None
) -> logging.Logger:
    """Configure logging for the backup script."""
    logger = logging.getLogger("kairos.backup")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# ============================================================================
# LOCAL BACKUP FUNCTIONS
# ============================================================================


def detect_db_path(config: BackupConfig) -> str | None:
    """Automatically detects the SQLite database path."""
    # Check if a path is already configured
    if config.db_path and os.path.exists(config.db_path):
        return config.db_path

    # Look in common locations
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Common locations for SQLite
    possible_paths = [
        os.path.join(project_root, "instance", "app.db"),
        os.path.join(project_root, "app.db"),
        os.path.join(project_root, "data", "app.db"),
        os.path.join(project_root, "database", "app.db"),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path

    # Check the database URI
    if config.db_uri and config.db_uri.startswith("sqlite:///"):
        db_path = config.db_uri.replace("sqlite:///", "")
        if not os.path.isabs(db_path):
            db_path = os.path.join(project_root, db_path)
        if os.path.exists(db_path):
            return db_path

    return None


def create_local_backup(
    db_path: str, backup_path: str, compress: bool = True
) -> tuple[bool, str]:
    """
    Creates a local backup of the SQLite database.

    Args:
        db_path: Path to the source SQLite file
        backup_path: Path to the backup file
        compress: If True, compresses the backup

    Returns:
        Tuple (success, message)
    """
    try:
        # Create the destination directory if needed
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)

        if compress:
            # Backup with compression
            with open(db_path, "rb") as f_in:
                with gzip.open(backup_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
        else:
            # Backup without compression
            shutil.copy2(db_path, backup_path)

        return True, f"Sauvegarde locale créée: {backup_path}"

    except Exception as e:
        return False, f"Erreur lors de la sauvegarde locale: {str(e)}"


def verify_backup(
    db_path: str, backup_path: str, compress: bool = False
) -> tuple[bool, str]:
    """
    Verifies the integrity of a backup.

    Args:
        db_path: Path to the original SQLite file
        backup_path: Path to the backup file
        compress: If True, the backup is compressed

    Returns:
        Tuple (success, message)
    """
    try:
        # Check the file exists
        if not os.path.exists(backup_path):
            return False, f"Fichier de sauvegarde introuvable: {backup_path}"

        # Check the size
        backup_size = os.path.getsize(backup_path)
        if backup_size == 0:
            return False, "Fichier de sauvegarde vide"

        # For compressed backups, check they can be decompressed
        if compress and backup_path.endswith(".gz"):
            with gzip.open(backup_path, "rb") as f:
                try:
                    # Read the start of the file to check it
                    header = f.read(16)
                    # Check the SQLite signature
                    if header != b"SQLite format 3\x00":
                        return False, "Fichier corrompu: signature SQLite invalide"
                except Exception as e:
                    return False, f"Erreur de décompression: {str(e)}"
        else:
            # Check the SQLite signature directly
            with open(backup_path, "rb") as f:
                header = f.read(16)
                if header != b"SQLite format 3\x00":
                    return False, "Fichier corrompu: signature SQLite invalide"

        # Compute the hash for verification
        if compress:
            with gzip.open(backup_path, "rb") as f:
                backup_hash = hashlib.sha256(f.read()).hexdigest()
        else:
            with open(backup_path, "rb") as f:
                backup_hash = hashlib.sha256(f.read()).hexdigest()

        return True, f"Vérification réussie (SHA256: {backup_hash[:16]}...)"

    except Exception as e:
        return False, f"Erreur de vérification: {str(e)}"


# ============================================================================
# S3 BACKUP FUNCTIONS
# ============================================================================


def get_s3_client(config: BackupConfig):
    """
    Creates an S3 client with the given configuration.

    Args:
        config: Backup configuration

    Returns:
        S3 client or None on error
    """
    if not S3_AVAILABLE:
        return None

    try:
        # S3 configuration
        s3_config = {
            "endpoint_url": config.s3_endpoint,
            "region_name": config.s3_region,
            "aws_access_key_id": config.s3_access_key,
            "aws_secret_access_key": config.s3_secret_key,
            "use_ssl": config.s3_use_ssl,
        }

        # Clean up None values
        s3_config = {k: v for k, v in s3_config.items() if v is not None}

        # Create the client
        if config.s3_endpoint:
            # S3-compatible (MinIO, etc.)
            client = boto3.client("s3", **s3_config)
        else:
            # AWS S3
            client = boto3.client("s3", **s3_config)

        return client

    except Exception:
        return None


def upload_to_s3(
    file_path: str, bucket: str, key: str, config: BackupConfig, logger: logging.Logger
) -> tuple[bool, str]:
    """
    Uploads a file to S3.

    Args:
        file_path: Local path of the file to upload
        bucket: S3 bucket name
        key: S3 key (path within the bucket)
        config: Backup configuration
        logger: Logger for messages

    Returns:
        Tuple (success, message)
    """
    if not S3_AVAILABLE:
        return (
            False,
            "La bibliothèque boto3 n'est pas installée. Installez-la avec: pip install boto3",
        )

    try:
        # Check the file exists
        if not os.path.exists(file_path):
            return False, f"Fichier introuvable: {file_path}"

        # Create the S3 client
        s3_client = get_s3_client(config)
        if s3_client is None:
            return False, "Impossible de créer le client S3. Vérifiez vos identifiants."

        # Check the bucket exists
        try:
            s3_client.head_bucket(Bucket=bucket)
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False, f"Bucket introuvable: {bucket}"
            elif e.response["Error"]["Code"] == "403":
                return (
                    False,
                    f"Accès refusé au bucket: {bucket}. Vérifiez vos permissions.",
                )
            else:
                return False, f"Erreur S3: {str(e)}"

        # Upload the file
        logger.info(f"Upload vers S3: {bucket}/{key}")

        # Upload options
        extra_args = {}

        # Set the content type
        if key.endswith(".gz"):
            extra_args["ContentType"] = "application/gzip"
            extra_args["ContentEncoding"] = "gzip"
        else:
            extra_args["ContentType"] = "application/octet-stream"

        s3_client.upload_file(file_path, bucket, key, ExtraArgs=extra_args)

        # Check the file was uploaded
        response = s3_client.head_object(Bucket=bucket, Key=key)
        file_size = response["ContentLength"]

        return True, f"Upload S3 réussi: {bucket}/{key} ({file_size} octets)"

    except NoCredentialsError:
        return (
            False,
            "Identifiants S3 manquants. Configurez BACKUP_S3_ACCESS_KEY et BACKUP_S3_SECRET_KEY",
        )
    except ClientError as e:
        return (
            False,
            f"Erreur S3: {e.response['Error']['Code']} - {e.response['Error']['Message']}",
        )
    except Exception as e:
        return False, f"Erreur lors de l'upload S3: {str(e)}"


def download_from_s3(
    bucket: str, key: str, file_path: str, config: BackupConfig, logger: logging.Logger
) -> tuple[bool, str]:
    """
    Downloads a file from S3.

    Args:
        bucket: S3 bucket name
        key: S3 key
        file_path: Local path to save the file to
        config: Backup configuration
        logger: Logger for messages

    Returns:
        Tuple (success, message)
    """
    if not S3_AVAILABLE:
        return False, "La bibliothèque boto3 n'est pas installée"

    try:
        s3_client = get_s3_client(config)
        if s3_client is None:
            return False, "Impossible de créer le client S3"

        # Create the destination directory
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Download the file
        s3_client.download_file(bucket, key, file_path)

        return True, f"Téléchargement S3 réussi: {bucket}/{key} -> {file_path}"

    except Exception as e:
        return False, f"Erreur lors du téléchargement S3: {str(e)}"


# ============================================================================
# CLEANUP FUNCTIONS
# ============================================================================


def cleanup_local_backups(
    config: BackupConfig, logger: logging.Logger
) -> tuple[int, str]:
    """
    Cleans up old local backups.

    Args:
        config: Backup configuration
        logger: Logger for messages

    Returns:
        Tuple (number of files deleted, message)
    """
    if not config.local_enabled or not config.local_dir:
        return 0, "Nettoyage local désactivé"

    try:
        deleted_count = 0
        local_dir = config.local_dir

        if not os.path.exists(local_dir):
            return 0, f"Dossier introuvable: {local_dir}"

        # List all backup files
        backup_files: list[dict[str, Any]] = []
        for filename in os.listdir(local_dir):
            if filename.startswith(config.backup_prefix):
                filepath = os.path.join(local_dir, filename)
                if os.path.isfile(filepath):
                    backup_files.append(
                        {
                            "path": filepath,
                            "filename": filename,
                            "mtime": os.path.getmtime(filepath),
                            "size": os.path.getsize(filepath),
                        }
                    )

        # Sort by modification date (oldest first)
        backup_files.sort(key=lambda x: x["mtime"])

        # Compute the cutoff date
        cutoff_date = datetime.now() - timedelta(days=config.retention_days)
        cutoff_timestamp = cutoff_date.timestamp()

        # Delete files that are too old
        for backup in backup_files:
            if backup["mtime"] < cutoff_timestamp:
                try:
                    os.remove(backup["path"])
                    logger.info(
                        f"Suppression: {backup['filename']} ({datetime.fromtimestamp(backup['mtime']).strftime('%Y-%m-%d')})"
                    )
                    deleted_count += 1
                except Exception as e:
                    logger.error(
                        f"Erreur lors de la suppression de {backup['filename']}: {str(e)}"
                    )

            # Cap the total number of backups
            elif len(backup_files) - deleted_count > config.max_backups:
                try:
                    os.remove(backup["path"])
                    logger.info(f"Suppression (limite atteinte): {backup['filename']}")
                    deleted_count += 1
                except Exception as e:
                    logger.error(
                        f"Erreur lors de la suppression de {backup['filename']}: {str(e)}"
                    )

        return deleted_count, f"Nettoyage terminé: {deleted_count} fichiers supprimés"

    except Exception as e:
        return 0, f"Erreur lors du nettoyage: {str(e)}"


def cleanup_s3_backups(config: BackupConfig, logger: logging.Logger) -> tuple[int, str]:
    """
    Cleans up old S3 backups.

    Args:
        config: Backup configuration
        logger: Logger for messages

    Returns:
        Tuple (number of files deleted, message)
    """
    if not config.s3_enabled or not config.s3_bucket:
        return 0, "Nettoyage S3 désactivé"

    if not S3_AVAILABLE:
        return 0, "boto3 non disponible"

    try:
        s3_client = get_s3_client(config)
        if s3_client is None:
            return 0, "Impossible de créer le client S3"

        deleted_count = 0
        prefix = config.s3_prefix or ""

        # List all objects in the bucket with the prefix
        paginator = s3_client.get_paginator("list_objects_v2")

        for page in paginator.paginate(Bucket=config.s3_bucket, Prefix=prefix):
            if "Contents" not in page:
                continue

            for obj in page["Contents"]:
                key = obj["Key"]
                last_modified = obj["LastModified"]

                # Compute the age in days
                age = (datetime.now(last_modified.tzinfo) - last_modified).days

                # Delete if too old
                if age > config.retention_days:
                    try:
                        s3_client.delete_object(Bucket=config.s3_bucket, Key=key)
                        logger.info(f"Suppression S3: {key} ({age} jours)")
                        deleted_count += 1
                    except Exception as e:
                        logger.error(
                            f"Erreur lors de la suppression S3 de {key}: {str(e)}"
                        )

        return deleted_count, f"Nettoyage S3 terminé: {deleted_count} objets supprimés"

    except Exception as e:
        return 0, f"Erreur lors du nettoyage S3: {str(e)}"


# ============================================================================
# NOTIFICATION FUNCTIONS
# ============================================================================


def send_backup_notification(
    config: BackupConfig, results: dict[str, Any], logger: logging.Logger
) -> None:
    """
    Sends a backup alert email if configured (success and/or failure
    depending on config.notify_on_success/notify_on_failure), reusing the
    email-notification SMTP configuration (see scripts/notification_config.py
    - same environment variables, so also subject to NOTIFICATIONS_ENABLED).

    Self-contained SMTP implementation rather than importing
    app.utils.notifications: this script must remain usable even if the
    Flask app fails to start (precisely the most likely disaster-recovery
    scenario) - importing the app package would trigger app/__init__.py
    (DB connection, Flask extensions, etc.), breaking this deliberate
    isolation.
    """
    should_notify = (results["success"] and config.notify_on_success) or (
        not results["success"] and config.notify_on_failure
    )
    if not should_notify or not config.notification_email:
        return

    from scripts.notification_config import NotificationConfig

    notification_config = NotificationConfig.from_env()
    if not notification_config.is_configured():
        logger.debug(
            "Notification de sauvegarde ignorée (NOTIFICATIONS_ENABLED "
            "désactivé ou configuration SMTP incomplète)."
        )
        return

    assert notification_config.from_email and notification_config.smtp_host

    status_label = "réussie" if results["success"] else "échouée"
    subject = f"[Kairos] Sauvegarde {status_label} - {results['timestamp']}"

    lines = [f"Sauvegarde {status_label} le {results['timestamp']}.", ""]
    if results.get("local"):
        lines.append(f"Local : {results['local']['message']}")
    if results.get("s3"):
        lines.append(f"S3 : {results['s3']['message']}")
    if results.get("errors"):
        lines.append("")
        lines.append("Erreurs :")
        lines.extend(f"- {error}" for error in results["errors"])
    text_body = "\n".join(lines)
    escaped = text_body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html_body = f"<pre>{escaped}</pre>"

    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = notification_config.from_email
    message["To"] = config.notification_email
    message.attach(MIMEText(text_body, "plain"))
    message.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(
            notification_config.smtp_host,
            notification_config.smtp_port,
            timeout=notification_config.smtp_timeout,
        ) as server:
            if notification_config.smtp_use_tls:
                server.starttls()
            if notification_config.smtp_username and notification_config.smtp_password:
                server.login(
                    notification_config.smtp_username,
                    notification_config.smtp_password,
                )
            server.sendmail(
                notification_config.from_email,
                [config.notification_email],
                message.as_string(),
            )
        logger.info(f"Email de notification envoyé à {config.notification_email}")
    except Exception as e:
        logger.error(f"Échec de l'envoi de l'email de notification : {e}")


# ============================================================================
# MAIN FUNCTIONS
# ============================================================================


def create_backup(config: BackupConfig, logger: logging.Logger) -> dict[str, Any]:
    """
    Creates a full backup (local and/or S3).

    Args:
        config: Backup configuration
        logger: Logger for messages

    Returns:
        Dictionary with the results
    """
    results: dict[str, Any] = {
        "success": False,
        "local": None,
        "s3": None,
        "timestamp": datetime.now().isoformat(),
        "errors": [],
    }

    # Detect the database path
    db_path = detect_db_path(config)
    if db_path is None:
        error_msg = "Impossible de trouver la base de données. Vérifiez DATABASE_URL ou placez app.db dans instance/"
        logger.error(error_msg)
        results["errors"].append(error_msg)
        return results

    logger.info(f"Base de données détectée: {db_path}")
    config.db_path = db_path

    timestamp = datetime.now()

    # Local backup
    if config.local_enabled:
        backup_path = config.get_local_backup_path(timestamp)
        logger.info(f"Création de la sauvegarde locale: {backup_path}")

        success, message = create_local_backup(db_path, backup_path, config.compress)
        results["local"] = {"success": success, "path": backup_path, "message": message}

        if success:
            logger.info(message)

            # Verification
            if config.verify_backup:
                verify_success, verify_message = verify_backup(
                    db_path, backup_path, config.compress
                )
                results["local"]["verified"] = verify_success
                results["local"]["verify_message"] = verify_message
                if verify_success:
                    logger.info(verify_message)
                else:
                    logger.warning(verify_message)
        else:
            logger.error(message)
            results["errors"].append(message)

    # S3 backup
    if config.s3_enabled and config.s3_bucket:
        backup_path = config.get_local_backup_path(timestamp)
        s3_key = config.get_s3_key(timestamp)

        # If the local backup succeeded, upload it to S3
        if results["local"] and results["local"]["success"]:
            logger.info(f"Upload vers S3: {config.s3_bucket}/{s3_key}")
            success, message = upload_to_s3(
                backup_path, config.s3_bucket, s3_key, config, logger
            )
            results["s3"] = {
                "success": success,
                "bucket": config.s3_bucket,
                "key": s3_key,
                "message": message,
            }

            if success:
                logger.info(message)
            else:
                logger.error(message)
                results["errors"].append(message)
        else:
            # Create a temporary backup for S3
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
                tmp_backup_path = tmp_file.name

            try:
                success, message = create_local_backup(
                    db_path, tmp_backup_path, config.compress
                )
                if success:
                    logger.info(f"Sauvegarde temporaire créée: {tmp_backup_path}")
                    upload_success, upload_message = upload_to_s3(
                        tmp_backup_path, config.s3_bucket, s3_key, config, logger
                    )
                    results["s3"] = {
                        "success": upload_success,
                        "bucket": config.s3_bucket,
                        "key": s3_key,
                        "message": upload_message,
                    }

                    if upload_success:
                        logger.info(upload_message)
                    else:
                        logger.error(upload_message)
                        results["errors"].append(upload_message)
                else:
                    results["errors"].append(message)
            finally:
                # Clean up the temporary file
                if os.path.exists(tmp_backup_path):
                    os.remove(tmp_backup_path)

    # Determine overall success
    results["success"] = (
        not config.local_enabled or (results["local"] and results["local"]["success"])
    ) and (not config.s3_enabled or (results["s3"] and results["s3"]["success"]))

    return results


def restore_backup(
    backup_path: str, target_path: str, config: BackupConfig, logger: logging.Logger
) -> tuple[bool, str]:
    """
    Restores a backup.

    Args:
        backup_path: Path to the backup file
        target_path: Path to the target database
        config: Backup configuration
        logger: Logger for messages

    Returns:
        Tuple (success, message)
    """
    try:
        # Check the backup file exists
        if not os.path.exists(backup_path):
            return False, f"Fichier de sauvegarde introuvable: {backup_path}"

        # Create the destination directory if needed
        os.makedirs(os.path.dirname(target_path), exist_ok=True)

        # Check whether the backup is compressed
        if backup_path.endswith(".gz"):
            logger.info(f"Décompression de {backup_path}")
            with gzip.open(backup_path, "rb") as f_in:
                with open(target_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
        else:
            logger.info(f"Copie de {backup_path} vers {target_path}")
            shutil.copy2(backup_path, target_path)

        # Check the file was restored
        if os.path.exists(target_path):
            file_size = os.path.getsize(target_path)
            return True, f"Restauration réussie: {target_path} ({file_size} octets)"
        else:
            return False, "La restauration a échoué: fichier cible introuvable"

    except Exception as e:
        return False, f"Erreur lors de la restauration: {str(e)}"


def list_backups(config: BackupConfig, logger: logging.Logger) -> dict[str, Any]:
    """
    Lists all available backups.

    Args:
        config: Backup configuration
        logger: Logger for messages

    Returns:
        Dictionary with the lists of backups
    """
    results: dict[str, Any] = {"local": [], "s3": []}

    # Local backups
    if config.local_enabled and config.local_dir:
        local_dir = config.local_dir
        if os.path.exists(local_dir):
            for filename in sorted(os.listdir(local_dir), reverse=True):
                if filename.startswith(config.backup_prefix):
                    filepath = os.path.join(local_dir, filename)
                    if os.path.isfile(filepath):
                        results["local"].append(
                            {
                                "filename": filename,
                                "path": filepath,
                                "size": os.path.getsize(filepath),
                                "modified": datetime.fromtimestamp(
                                    os.path.getmtime(filepath)
                                ).isoformat(),
                            }
                        )

    # S3 backups
    if config.s3_enabled and config.s3_bucket and S3_AVAILABLE:
        try:
            s3_client = get_s3_client(config)
            if s3_client:
                prefix = config.s3_prefix or ""
                paginator = s3_client.get_paginator("list_objects_v2")

                for page in paginator.paginate(Bucket=config.s3_bucket, Prefix=prefix):
                    if "Contents" in page:
                        for obj in page["Contents"]:
                            key = obj["Key"]
                            if key.startswith(prefix) and config.backup_prefix in key:
                                results["s3"].append(
                                    {
                                        "key": key,
                                        "bucket": config.s3_bucket,
                                        "size": obj["Size"],
                                        "modified": obj["LastModified"].isoformat(),
                                    }
                                )
        except Exception as e:
            logger.warning(f"Impossible de lister les sauvegardes S3: {str(e)}")

    return results


# ============================================================================
# MAIN FUNCTION
# ============================================================================


def main():
    """Script main function."""
    parser = argparse.ArgumentParser(
        description="Sauvegarde automatique de la base de données Kairos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python scripts/backup_database.py --local
  python scripts/backup_database.py --local --s3
  python scripts/backup_database.py --local --cleanup
  python scripts/backup_database.py --local --s3 --verify --cleanup

Variables d'environnement:
  BACKUP_ENABLED, BACKUP_LOCAL_ENABLED, BACKUP_S3_ENABLED
  BACKUP_LOCAL_DIR, BACKUP_S3_BUCKET, BACKUP_S3_ENDPOINT
  BACKUP_S3_ACCESS_KEY, BACKUP_S3_SECRET_KEY, BACKUP_RETENTION_DAYS
  Voir scripts/backup_config.py pour la liste complète.
        """,
    )

    parser.add_argument(
        "--local",
        action="store_true",
        default=True,
        help="Effectuer une sauvegarde locale",
    )
    parser.add_argument(
        "--s3", action="store_true", default=False, help="Effectuer une sauvegarde S3"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        default=False,
        help="Vérifier l'intégrité de la sauvegarde",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        default=False,
        help="Nettoyer les anciennes sauvegardes",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        default=False,
        help="Lister toutes les sauvegardes",
    )
    parser.add_argument(
        "--restore",
        type=str,
        default=None,
        metavar="BACKUP_FILE",
        help="Restaurer une sauvegarde (chemin local ou clé S3)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        metavar="CONFIG_FILE",
        help="Chemin vers un fichier de configuration JSON",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Niveau de logging",
    )
    parser.add_argument(
        "--log-file", type=str, default=None, metavar="LOG_FILE", help="Fichier de log"
    )

    args = parser.parse_args()

    # Load the configuration
    if args.config:
        # Load from a JSON file
        try:
            with open(args.config) as f:
                config_data = json.load(f)
            config = BackupConfig(**config_data)
        except Exception as e:
            print(
                f"Erreur de chargement de la configuration: {str(e)}", file=sys.stderr
            )
            sys.exit(1)
    else:
        # Load from environment variables
        config = get_config()

        # Override with command-line arguments
        config.local_enabled = args.local
        config.s3_enabled = args.s3
        config.verify_backup = args.verify

    # Configure logging
    log_level = args.log_level or config.log_level
    log_file = args.log_file or config.log_file
    logger = setup_logging(log_level, log_file)

    logger.info("=" * 60)
    logger.info("Kairos - Sauvegarde de la base de données")
    logger.info("=" * 60)

    # Check whether backups are enabled
    if not config.enabled:
        logger.info("Les sauvegardes sont désactivées (BACKUP_ENABLED=false)")
        sys.exit(0)

    # List backups
    if args.list:
        backups = list_backups(config, logger)
        print("\n" + "=" * 60)
        print("SAUVEGARDES LOCALES:")
        print("=" * 60)
        for backup in backups["local"]:
            print(
                f"  {backup['filename']} ({backup['size']} octets, {backup['modified']})"
            )

        print("\n" + "=" * 60)
        print("SAUVEGARDES S3:")
        print("=" * 60)
        for backup in backups["s3"]:
            print(f"  {backup['key']} ({backup['size']} octets, {backup['modified']})")
        sys.exit(0)

    # Restore a backup
    if args.restore:
        if args.restore.startswith("s3://"):
            # Restore from S3
            parts = args.restore[5:].split("/")
            if len(parts) >= 2:
                bucket = parts[0]
                key = "/".join(parts[1:])

                # Download to a temporary file
                with tempfile.NamedTemporaryFile(
                    suffix=".db", delete=False
                ) as tmp_file:
                    tmp_path = tmp_file.name

                try:
                    # Download from S3
                    db_path = detect_db_path(config)
                    if db_path is None:
                        logger.error("Impossible de trouver la base de données cible")
                        sys.exit(1)

                    # Download the file
                    success, message = download_from_s3(
                        bucket, key, tmp_path, config, logger
                    )

                    if success:
                        # Restore
                        restore_success, restore_message = restore_backup(
                            tmp_path, db_path, config, logger
                        )

                        if restore_success:
                            logger.info(restore_message)
                            logger.info("Restauration terminée avec succès!")
                        else:
                            logger.error(restore_message)
                            sys.exit(1)
                    else:
                        logger.error(message)
                        sys.exit(1)
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
        else:
            # Restore from a local file
            db_path = detect_db_path(config)
            if db_path is None:
                logger.error("Impossible de trouver la base de données cible")
                sys.exit(1)

            success, message = restore_backup(args.restore, db_path, config, logger)

            if success:
                logger.info(message)
                logger.info("Restauration terminée avec succès!")
            else:
                logger.error(message)
                sys.exit(1)

        sys.exit(0)

    # Perform the backup
    logger.info("Début de la sauvegarde...")
    logger.info(f"Configuration: local={config.local_enabled}, s3={config.s3_enabled}")

    results = create_backup(config, logger)

    send_backup_notification(config, results, logger)

    # Cleanup
    if args.cleanup:
        logger.info("\nNettoyage des anciennes sauvegardes...")

        if config.local_enabled:
            deleted, message = cleanup_local_backups(config, logger)
            logger.info(message)

        if config.s3_enabled:
            deleted, message = cleanup_s3_backups(config, logger)
            logger.info(message)

    # Show the results
    print("\n" + "=" * 60)
    print("RÉSULTATS DE LA SAUVEGARDE:")
    print("=" * 60)

    if results["local"]:
        status = "✓" if results["local"]["success"] else "✗"
        print(f"{status} Sauvegarde locale: {results['local']['message']}")
        if results["local"].get("verified"):
            print(f"  Vérification: {results['local']['verify_message']}")

    if results["s3"]:
        status = "✓" if results["s3"]["success"] else "✗"
        print(f"{status} Sauvegarde S3: {results['s3']['message']}")

    if results["errors"]:
        print("\n" + "=" * 60)
        print("ERREURS:")
        print("=" * 60)
        for error in results["errors"]:
            print(f"  ✗ {error}")

    if results["success"]:
        logger.info("Sauvegarde terminée avec succès!")
        sys.exit(0)
    else:
        logger.error("La sauvegarde a échoué!")
        sys.exit(1)


if __name__ == "__main__":
    main()
