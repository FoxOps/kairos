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
# Toujours exécuté, même si app.db existe déjà : db.create_all() ne crée
# que les tables manquantes (idempotent, ne touche pas aux tables/données
# existantes) - c'est le seul mécanisme de migration de schéma de ce
# projet (pas d'Alembic/Flask-Migrate, voir CLAUDE.md "Layered
# architecture"). Sans ça, une nouvelle table ajoutée par une mise à jour
# de l'app (ex: swap_request) ne serait jamais créée sur un déploiement
# existant, et resterait "no such table" au premier accès.
if [ ! -f "/app/data/app.db" ]; then
    echo "🔧 Initialisation de la base de données SQLite..."
else
    echo "ℹ️ Base de données existante (app.db) - vérification du schéma..."
fi
python docker/init_database.py || { echo "❌ Erreur: Échec de l'initialisation/mise à jour de la base de données"; exit 1; }
echo "✅ Base de données prête"

# --- Tâches planifiées (notifications par email, sauvegardes) ---
# Purement piloté par variables d'environnement (NOTIFICATIONS_ENABLED,
# BACKUP_ENABLED, voir .env.example) - pas de service Docker séparé à
# gérer. crond (busybox, déjà dans l'image Alpine) tourne en
# arrière-plan dans ce même conteneur ; le serveur web reste le process
# principal (PID 1, via exec plus bas). Planning : docker/crontabs/appuser
# (toutes les entrées y sont toujours présentes ; chaque script se
# no-op silencieusement si sa propre variable *_ENABLED est à false -
# crond n'a donc besoin de démarrer que si au moins une tâche est active).
is_true() {
    case "$(echo "$1" | tr '[:upper:]' '[:lower:]')" in
        true|1|yes|y) return 0 ;;
        *) return 1 ;;
    esac
}

any_scheduled_task=false

if is_true "${NOTIFICATIONS_ENABLED:-false}"; then
    echo "📧 Notifications par email activées"
    any_scheduled_task=true
else
    echo "📧 Notifications par email désactivées (NOTIFICATIONS_ENABLED)"
fi

if is_true "${BACKUP_ENABLED:-false}"; then
    echo "💾 Sauvegardes automatiques activées"
    any_scheduled_task=true
else
    echo "💾 Sauvegardes automatiques désactivées (BACKUP_ENABLED)"
fi

if [ "$any_scheduled_task" = "true" ]; then
    echo "⏱️ Démarrage de crond en arrière-plan"
    crond -l 2 -c /app/docker/crontabs
else
    echo "⏱️ Aucune tâche planifiée active - crond non démarré"
fi

# --- Démarrage du serveur ---
if [ "$FLASK_ENV" = "production" ]; then
    echo "🌤️ Mode PRODUCTION détecté - Démarrage de Gunicorn"
    exec gunicorn --bind 0.0.0.0:5000 --workers 1 --threads 4 --timeout 120 run:app
else
    echo "🌤️ Mode DEVELOPPEMENT détecté - Démarrage de Flask"
    exec python run.py
fi
