#!/bin/bash
# Script to prepare the Docker environment

set -e

# Move into docker/ regardless of the caller's working directory: the
# rest of the script is written with paths relative to docker/ (data/,
# logs/, .env), to match docker-compose.yml's own relative volumes
# (resolved relative to its own location, so docker/data and docker/logs).
cd "$(dirname "$0")"

echo "🔧 Préparation de l'environnement Docker pour Kairos"

# Create the required directories
mkdir -p data logs

# Set permissions for user 1000:1000 (the user inside the container)
echo "📁 Configuration des permissions pour l'utilisateur 1000:1000"
sudo chown -R 1000:1000 data logs
sudo chmod -R 755 data logs

# Create a .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Création du fichier .env"
    cp .env.example .env

    # Generate a secret key
    SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "changez-moi")
    ADMIN_PASSWORD=$(python -c "import secrets; print(secrets.token_urlsafe(16))" 2>/dev/null || echo "admin123")

    # Replace the default values
    sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
    sed -i "s/^DEFAULT_ADMIN_PASSWORD=.*/DEFAULT_ADMIN_PASSWORD=$ADMIN_PASSWORD/" .env

    echo "✅ Fichier .env créé avec des valeurs sécurisées"
else
    echo "ℹ️  Fichier .env existe déjà"
fi

echo ""
echo "✅ Environnement prêt !"
echo ""
echo "Pour démarrer (depuis docker/) :"
echo "  docker compose build"
echo "  docker compose up -d"
