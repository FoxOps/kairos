#!/bin/bash

# ============================================================================
# Leviia Schedule - Exemple de script pour Cron
# ============================================================================
#
# Ce script est un exemple pour automatiser les sauvegardes avec Cron.
#
# INSTRUCTIONS:
# 1. Copiez ce fichier: cp scripts/cron_example.sh /usr/local/bin/leviia-backup
# 2. Rendez-le exécutable: chmod +x /usr/local/bin/leviia-backup
# 3. Configurez les variables d'environnement ci-dessous
# 4. Ajoutez une entrée à votre crontab: crontab -e
#    Exemple pour une sauvegarde quotidienne à 2h:
#    0 2 * * * /usr/local/bin/leviia-backup
#
# ============================================================================

# ============================================================================
# CONFIGURATION
# ============================================================================

# Chemin vers le projet Leviia Schedule
PROJECT_DIR="/chemin/vers/leviia-schedule"

# Chemin vers l'interpréteur Python (utilisez l'environnement virtuel si disponible)
PYTHON_BIN="/chemin/vers/leviia-schedule/venv/bin/python"

# Chemin vers le script de sauvegarde
BACKUP_SCRIPT="${PROJECT_DIR}/scripts/backup_database.py"

# Fichier de log
LOG_FILE="/var/log/leviia-backup.log"

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
export BACKUP_S3_PREFIX="leviia-schedule"
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
    # mail -s "Erreur de sauvegarde Leviia" admin@example.com < "${LOG_FILE}"
fi

# ============================================================================
# EXEMPLES DE CRONTAB
# ============================================================================
#
# Sauvegarde quotidienne à 2h:
# 0 2 * * * /usr/local/bin/leviia-backup
#
# Sauvegarde hebdomadaire le dimanche à 3h:
# 0 3 * * 0 /usr/local/bin/leviia-backup
#
# Sauvegarde mensuelle le 1er à 4h:
# 0 4 1 * * /usr/local/bin/leviia-backup
#
# Sauvegarde toutes les 6 heures:
# 0 */6 * * * /usr/local/bin/leviia-backup
#
# ============================================================================
