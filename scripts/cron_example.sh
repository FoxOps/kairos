#!/bin/bash

# ============================================================================
# Kairos - Example Cron script
# ============================================================================
#
# This script is an example for automating backups with Cron.
#
# INSTRUCTIONS:
# 1. Copy this file: cp scripts/cron_example.sh /usr/local/bin/kairos-backup
# 2. Make it executable: chmod +x /usr/local/bin/kairos-backup
# 3. Configure the environment variables below
# 4. Add an entry to your crontab: crontab -e
#    Example for a daily backup at 2am:
#    0 2 * * * /usr/local/bin/kairos-backup
#
# ============================================================================

# ============================================================================
# CONFIGURATION
# ============================================================================

# Path to the Kairos project
PROJECT_DIR="/path/to/kairos"

# Path to the Python interpreter (use the virtual environment if available)
PYTHON_BIN="/path/to/kairos/venv/bin/python"

# Path to the backup script
BACKUP_SCRIPT="${PROJECT_DIR}/scripts/backup_database.py"

# Log file
LOG_FILE="/var/log/kairos-backup.log"

# ============================================================================
# BACKUP ENVIRONMENT VARIABLES
# ============================================================================

# Enable
export BACKUP_ENABLED=true

# Local backup
export BACKUP_LOCAL_ENABLED=true
export BACKUP_LOCAL_DIR="${PROJECT_DIR}/backups"

# S3 backup (disabled by default, enable if needed)
export BACKUP_S3_ENABLED=false
export BACKUP_S3_BUCKET="your-s3-bucket"
export BACKUP_S3_ENDPOINT=""  # Leave empty for AWS S3, or set for MinIO/etc
export BACKUP_S3_REGION="eu-west-1"
export BACKUP_S3_ACCESS_KEY="your-access-key"
export BACKUP_S3_SECRET_KEY="your-secret-key"
export BACKUP_S3_PREFIX="kairos"
export BACKUP_S3_USE_SSL=true

# Retention
export BACKUP_RETENTION_DAYS=30
export BACKUP_MAX_BACKUPS=30

# Options
export BACKUP_COMPRESS=true
export BACKUP_VERIFY=true
export BACKUP_LOG_LEVEL=INFO

# ============================================================================
# EXECUTION
# ============================================================================

# Create the log directory if needed
mkdir -p "$(dirname "${LOG_FILE}")"

# Run the backup
cd "${PROJECT_DIR}"

"${PYTHON_BIN}" "${BACKUP_SCRIPT}" --local --s3 --verify --cleanup >> "${LOG_FILE}" 2>&1

# Check the exit code
if [ $? -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Sauvegarde terminée avec succès" >> "${LOG_FILE}"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERREUR: La sauvegarde a échoué" >> "${LOG_FILE}"
    # Send a notification (optional)
    # mail -s "Erreur de sauvegarde Kairos" admin@example.com < "${LOG_FILE}"
fi

# ============================================================================
# CRONTAB EXAMPLES
# ============================================================================
#
# Daily backup at 2am:
# 0 2 * * * /usr/local/bin/kairos-backup
#
# Weekly backup on Sunday at 3am:
# 0 3 * * 0 /usr/local/bin/kairos-backup
#
# Monthly backup on the 1st at 4am:
# 0 4 1 * * /usr/local/bin/kairos-backup
#
# Backup every 6 hours:
# 0 */6 * * * /usr/local/bin/kairos-backup
#
# ============================================================================
# EMAIL NOTIFICATIONS (shift and on-call reminders)
# ============================================================================
#
# Environment variables: see scripts/notification_config.py and the EMAIL
# NOTIFICATION CONFIGURATION section of .env.example
# (NOTIFICATIONS_ENABLED, NOTIFICATION_FROM_EMAIL, SMTP_HOST, etc.). No-op
# if NOTIFICATIONS_ENABLED isn't set.
#
# Shift reminder: sent on Sunday, 24h before Monday's shifts start. One
# email per week per user.
# 0 9 * * 0 cd /path/to/kairos && /path/to/venv/bin/python scripts/send_shift_notifications.py >> /var/log/kairos-notifications.log 2>&1
#
# On-call reminder: sent on Thursday, 24h before Friday 9pm on-call starts.
# 0 9 * * 4 cd /path/to/kairos && /path/to/venv/bin/python scripts/send_oncall_notifications.py >> /var/log/kairos-notifications.log 2>&1
#
# ============================================================================
