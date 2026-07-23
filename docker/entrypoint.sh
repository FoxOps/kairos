#!/bin/sh
set -e

# Configure PYTHONPATH
export PYTHONPATH=/app:$PYTHONPATH
cd /app

echo "🔍 Configuration actuelle:"
echo "  FLASK_ENV: ${FLASK_ENV:-non défini}"
echo "  DATABASE_URL: ${DATABASE_URL:-non défini}"
echo "  UID: $(id -u), GID: $(id -g)"
echo ""

# --- FIX: force permissions on the mounted directories ---
# chown requires being root (CAP_CHOWN), even to reset the same uid/gid.
# If the container is already running non-root (e.g. "user: 1000:1000" in
# docker-compose.yml), we can't chown: just check write access and fail
# with a clear message if it's not there.
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

# --- Database schema initialization / migration ---
# Always run, even if app.db already exists: docker/init_database.py calls
# run.py::setup_database(), which applies the Alembic migrations
# (migrations/versions/) via `alembic upgrade head` - idempotent, doesn't
# touch tables/data that are already up to date. On a deployment predating
# Alembic adoption (tables already created by the old db.create_all(), no
# alembic_version table), setup_database() automatically falls back to
# stamping the baseline revision before applying the following
# migrations - no manual command required. Without this step, a new table
# or constraint added by an app update would never be applied on an
# existing deployment.
if [ ! -f "/app/data/app.db" ]; then
    echo "🔧 Initialisation de la base de données SQLite..."
else
    echo "ℹ️ Base de données existante (app.db) - vérification du schéma..."
fi
python docker/init_database.py || { echo "❌ Erreur: Échec de l'initialisation/mise à jour de la base de données"; exit 1; }
echo "✅ Base de données prête"

# --- Scheduled tasks (email notifications, backups, schedule purge) ---
# Notifications/backups remain driven by environment variables
# (NOTIFICATIONS_ENABLED, BACKUP_ENABLED, see .env.example); schedule
# purge is enabled by default (Setting schedule_retention_days=365,
# admin-editable at /admin/settings, 0 = disabled) - crond therefore now
# always starts. crond (busybox, already in the Alpine image) runs in the
# background in this same container; the web server stays the main
# process (PID 1, via exec further below). Schedule:
# docker/crontabs/appuser (every entry is always present there; each
# script checks its own enable condition itself and no-ops otherwise).
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

# --- Start the server ---
if [ "$FLASK_ENV" = "production" ]; then
    echo "🌤️ Mode PRODUCTION détecté - Démarrage de Gunicorn"
    exec gunicorn --bind 0.0.0.0:5000 --workers 1 --threads 4 --timeout 120 run:app
else
    echo "🌤️ Mode DEVELOPPEMENT détecté - Démarrage de Flask"
    exec python run.py
fi
