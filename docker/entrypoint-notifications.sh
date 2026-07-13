#!/bin/sh
set -e

# Point d'entrée du service leviia-notifications (docker-compose.yml) :
# un conteneur séparé du serveur web, dédié à l'exécution des rappels
# hebdomadaires par email (shifts/astreinte). N'initialise pas la base de
# données - le service leviia-schedule le fait déjà au démarrage, et les
# deux services partagent le même volume /app/data.

export PYTHONPATH=/app:$PYTHONPATH
cd /app

mkdir -p /app/logs

echo "Fuseau horaire : $(date)"
echo "NOTIFICATIONS_ENABLED: ${NOTIFICATIONS_ENABLED:-non défini}"
echo "Démarrage de crond (planification : voir docker/crontabs/appuser)..."

# -f : premier plan (requis pour rester le processus principal du conteneur)
# -l 2 : niveau de log (2 = jobs exécutés + erreurs, sans le bruit debug)
# -c : dossier contenant un fichier crontab par utilisateur (nommé "appuser"
# ici) - évite de dépendre de /var/spool/cron/crontabs, propriété de root.
exec crond -f -l 2 -c /app/docker/crontabs
