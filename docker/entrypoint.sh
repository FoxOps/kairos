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

# --- Initialisation de la base de données ---
if [ ! -f "/app/data/app.db" ]; then
    echo "🔧 Initialisation de la base de données SQLite..."
    python docker/init_database.py || { echo "❌ Erreur: Échec de l'initialisation de la base de données"; exit 1; }
    echo "✅ Base de données initialisée"
else
    echo "ℹ️ Base de données déjà existante (app.db)"
fi

# --- Notifications par email (rappels shifts/astreinte) ---
# Purement piloté par variable d'environnement (NOTIFICATIONS_ENABLED,
# voir .env.example) - pas de service Docker séparé à gérer. crond
# (busybox, déjà dans l'image Alpine) tourne en arrière-plan dans ce
# même conteneur ; le serveur web reste le process principal (PID 1,
# via exec plus bas). Planning : docker/crontabs/appuser.
case "$(echo "${NOTIFICATIONS_ENABLED:-false}" | tr '[:upper:]' '[:lower:]')" in
    true|1|yes|y)
        echo "📧 Notifications par email activées - démarrage de crond en arrière-plan"
        crond -l 2 -c /app/docker/crontabs
        ;;
    *)
        echo "📧 Notifications par email désactivées (NOTIFICATIONS_ENABLED)"
        ;;
esac

# --- Démarrage du serveur ---
if [ "$FLASK_ENV" = "production" ]; then
    echo "🌤️ Mode PRODUCTION détecté - Démarrage de Gunicorn"
    exec gunicorn --bind 0.0.0.0:5000 --workers 1 --threads 4 --timeout 120 run:app
else
    echo "🌤️ Mode DEVELOPPEMENT détecté - Démarrage de Flask"
    exec python run.py
fi
