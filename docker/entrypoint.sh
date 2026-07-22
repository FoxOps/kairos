#!/bin/sh
set -e

# Configurer PYTHONPATH
export PYTHONPATH=/app:$PYTHONPATH
cd /app

echo "🔍 Configuration actuelle:"
echo "  FLASK_ENV: ${FLASK_ENV:-non défini}"
echo "  DATABASE_URL: ${DATABASE_URL:-non défini}"
echo "  UID: $(id -u), GID: $(id -g)"
echo ""

# --- FIX: Forcer les permissions des dossiers montés ---
# chown nécessite d'être root (CAP_CHOWN), même pour remettre le même uid/gid.
# Si le conteneur tourne déjà en non-root (ex: "user: 1000:1000" dans
# docker-compose.yml), on ne peut pas chown : on vérifie juste l'accès en
# écriture et on échoue avec un message clair si ce n'est pas le cas.
mkdir -p /app/data /app/logs

if [ "$(id -u)" = "0" ]; then
    echo "🔧 Application des permissions pour /app/data et /app/logs..."
    chown -R 1000:1000 /app/data /app/logs || { echo "❌ Erreur: Impossible de changer le propriétaire"; exit 1; }
    chmod -R 755 /app/data /app/logs || { echo "❌ Erreur: Impossible de changer les permissions"; exit 1; }
    echo "✅ Permissions appliquées"
else
    for dir in /app/data /app/logs; do
        if [ ! -w "$dir" ]; then
            echo "❌ Erreur: $dir n'est pas accessible en écriture pour l'UID $(id -u)."
            echo "   Le conteneur tourne en non-root (user: $(id -u):$(id -g)) et ne peut pas chown."
            echo "   Corrigez les permissions du volume sur l'hôte, ex: sudo chown -R 1000:1000 <chemin-du-volume>"
            exit 1
        fi
    done
    echo "✅ /app/data et /app/logs déjà accessibles en écriture (UID $(id -u))"
fi

# --- Initialisation / mise à jour du schéma de la base de données ---
# Toujours exécuté, même si app.db existe déjà : docker/init_database.py
# appelle run.py::setup_database(), qui applique les migrations Alembic
# (migrations/versions/) via `alembic upgrade head` - idempotent, ne
# touche pas aux tables/données déjà à jour. Sur un déploiement d'avant
# l'adoption d'Alembic (tables déjà créées par l'ancien db.create_all(),
# pas de table alembic_version), setup_database() bascule automatiquement
# sur un stamp de la révision baseline avant d'appliquer les migrations
# suivantes - aucune commande manuelle requise. Sans cette étape, une
# nouvelle table ou contrainte ajoutée par une mise à jour de l'app ne
# serait jamais appliquée sur un déploiement existant.
if [ ! -f "/app/data/app.db" ]; then
    echo "🔧 Initialisation de la base de données SQLite..."
else
    echo "ℹ️ Base de données existante (app.db) - vérification du schéma..."
fi
python docker/init_database.py || { echo "❌ Erreur: Échec de l'initialisation/mise à jour de la base de données"; exit 1; }
echo "✅ Base de données prête"

# --- Tâches planifiées (notifications par email, sauvegardes, purge du
# planning) ---
# Notifications/sauvegardes restent pilotées par variables
# d'environnement (NOTIFICATIONS_ENABLED, BACKUP_ENABLED, voir
# .env.example) ; la purge du planning est activée par défaut
# (Setting schedule_retention_days=365, admin-éditable à
# /admin/settings, 0 = désactivée) - crond démarre donc désormais
# toujours. crond (busybox, déjà dans l'image Alpine) tourne en
# arrière-plan dans ce même conteneur ; le serveur web reste le process
# principal (PID 1, via exec plus bas). Planning : docker/crontabs/appuser
# (toutes les entrées y sont toujours présentes ; chaque script vérifie
# lui-même sa propre condition d'activation et ne fait rien sinon).
is_true() {
    case "$(echo "$1" | tr '[:upper:]' '[:lower:]')" in
        true|1|yes|y) return 0 ;;
        *) return 1 ;;
    esac
}

if is_true "${NOTIFICATIONS_ENABLED:-false}"; then
    echo "📧 Notifications par email activées"
else
    echo "📧 Notifications par email désactivées (NOTIFICATIONS_ENABLED)"
fi

if is_true "${BACKUP_ENABLED:-false}"; then
    echo "💾 Sauvegardes automatiques activées"
else
    echo "💾 Sauvegardes automatiques désactivées (BACKUP_ENABLED)"
fi

echo "🧹 Purge automatique du planning activée par défaut (Setting schedule_retention_days, /admin/settings)"
echo "⏱️ Démarrage de crond en arrière-plan"
crond -l 2 -c /app/docker/crontabs

# --- Démarrage du serveur ---
if [ "$FLASK_ENV" = "production" ]; then
    echo "🌤️ Mode PRODUCTION détecté - Démarrage de Gunicorn"
    exec gunicorn --bind 0.0.0.0:5000 --workers 1 --threads 4 --timeout 120 run:app
else
    echo "🌤️ Mode DEVELOPPEMENT détecté - Démarrage de Flask"
    exec python run.py
fi
