#!/bin/bash

# ============================================================================
# Kairos - Exemple de script pour Cron
# ============================================================================
#
# Ce script est un exemple pour automatiser les sauvegardes avec Cron.
#
# INSTRUCTIONS:
# 1. Copiez ce fichier: cp scripts/cron_example.sh /usr/local/bin/kairos-backup
# 2. Rendez-le exécutable: chmod +x /usr/local/bin/kairos-backup
# 3. Configurez les variables d'environnement ci-dessous
# 4. Ajoutez une entrée à votre crontab: crontab -e
#    Exemple pour une sauvegarde quotidienne à 2h:
#    0 2 * * * /usr/local/bin/kairos-backup
#
# ============================================================================

# ============================================================================
# CONFIGURATION
# ============================================================================

# Chemin vers le projet Kairos
PROJECT_DIR="/chemin/vers/kairos"

# Chemin vers l'interpréteur Python (utilisez l'environnement virtuel si disponible)
PYTHON_BIN="/chemin/vers/kairos/venv/bin/python"

# Chemin vers le script de sauvegarde
BACKUP_SCRIPT="${PROJECT_DIR}/scripts/backup_database.py"

# Fichier de log
LOG_FILE="/var/log/kairos-backup.log"

# ============================================================================
# VARIABLES D'ENVIRONNEMENT POUR LA SAUVEGARDE
# ============================================================================

# Activation
export BACKUP_ENABLED=true

# Sauvegarde locale
export BACKUP_LOCAL_ENABLED=true
export BACKUP_LOCAL_DIR="${PROJECT_DIR}/backups"

# Sauvegarde S3 (désactivée par défaut, activez si nécessaire)
export BACKUP_S3_ENABLED=false
export BACKUP_S3_BUCKET="votre-bucket-s3"
export BACKUP_S3_ENDPOINT=""  # Laissez vide pour AWS S3, ou spécifiez pour MinIO/etc
export BACKUP_S3_REGION="eu-west-1"
export BACKUP_S3_ACCESS_KEY="votre-access-key"
export BACKUP_S3_SECRET_KEY="votre-secret-key"
export BACKUP_S3_PREFIX="kairos"
export BACKUP_S3_USE_SSL=true

# Rétention
export BACKUP_RETENTION_DAYS=30
export BACKUP_MAX_BACKUPS=30

# Options
export BACKUP_COMPRESS=true
export BACKUP_VERIFY=true
export BACKUP_LOG_LEVEL=INFO

# ============================================================================
# EXÉCUTION
# ============================================================================

# Créer le dossier de log si nécessaire
mkdir -p "$(dirname "${LOG_FILE}")"

# Exécuter la sauvegarde
cd "${PROJECT_DIR}"

"${PYTHON_BIN}" "${BACKUP_SCRIPT}" --local --s3 --verify --cleanup >> "${LOG_FILE}" 2>&1

# Vérifier le code de sortie
if [ $? -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Sauvegarde terminée avec succès" >> "${LOG_FILE}"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERREUR: La sauvegarde a échoué" >> "${LOG_FILE}"
    # Envoyer une notification (optionnel)
    # mail -s "Erreur de sauvegarde Kairos" admin@example.com < "${LOG_FILE}"
fi

# ============================================================================
# EXEMPLES DE CRONTAB
# ============================================================================
#
# Sauvegarde quotidienne à 2h:
# 0 2 * * * /usr/local/bin/kairos-backup
#
# Sauvegarde hebdomadaire le dimanche à 3h:
# 0 3 * * 0 /usr/local/bin/kairos-backup
#
# Sauvegarde mensuelle le 1er à 4h:
# 0 4 1 * * /usr/local/bin/kairos-backup
#
# Sauvegarde toutes les 6 heures:
# 0 */6 * * * /usr/local/bin/kairos-backup
#
# ============================================================================
# NOTIFICATIONS PAR EMAIL (rappels de shifts et d'astreintes)
# ============================================================================
#
# Variables d'environnement : voir scripts/notification_config.py et la
# section CONFIGURATION DES NOTIFICATIONS PAR EMAIL de .env.example
# (NOTIFICATIONS_ENABLED, NOTIFICATION_FROM_EMAIL, SMTP_HOST, etc.). Ne
# font rien si NOTIFICATIONS_ENABLED n'est pas activé.
#
# Rappel des shifts : envoyé le dimanche, 24h avant le début des shifts
# du lundi. Un seul email par semaine et par utilisateur.
# 0 9 * * 0 cd /chemin/vers/kairos && /chemin/vers/venv/bin/python scripts/send_shift_notifications.py >> /var/log/kairos-notifications.log 2>&1
#
# Rappel d'astreinte : envoyé le jeudi, 24h avant le début de l'astreinte
# du vendredi 21h.
# 0 9 * * 4 cd /chemin/vers/kairos && /chemin/vers/venv/bin/python scripts/send_oncall_notifications.py >> /var/log/kairos-notifications.log 2>&1
#
# ============================================================================
