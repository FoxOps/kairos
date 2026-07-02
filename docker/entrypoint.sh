#!/bin/sh
set -e

# Configurer PYTHONPATH pour s'assurer que le module app est trouvable
export PYTHONPATH=/app:$PYTHONPATH

# Changer de répertoire vers /app
cd /app

# Afficher la configuration actuelle
echo "🔍 Configuration actuelle:"
echo "  FLASK_ENV: ${FLASK_ENV:-non défini}"
echo "  DATABASE_URL: ${DATABASE_URL:-non défini}"
echo ""

# Initialiser la base de données SQLite
if [ ! -f "/app/data/app.db" ]; then
    echo "🔧 Initialisation de la base de données SQLite..."
    python docker/init_database.py
    echo "✅ Base de données initialisée"
fi

# Choisir le serveur selon FLASK_ENV
# Note: Docker Compose charge les variables d'environnement, mais python-dotenv
# peut aussi les charger depuis .env. On vérifie explicitement FLASK_ENV.
if [ "$FLASK_ENV" = "production" ]; then
    echo "🌤️ Mode PRODUCTION détecté - Démarrage de Gunicorn"
    exec gunicorn --bind 0.0.0.0:5000 --workers 1 --threads 4 --timeout 120 run:app
else
    echo "🌤️ Mode DEVELOPPEMENT détecté - Démarrage de Flask"
    exec python run.py
fi
