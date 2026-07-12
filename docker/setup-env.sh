#!/bin/bash
# Script pour préparer l'environnement Docker

set -e

# Se placer dans docker/ quel que soit le répertoire d'appel : le reste du
# script est écrit en chemins relatifs à docker/ (data/, logs/, .env), pour
# matcher les volumes relatifs de docker-compose.yml (résolus par rapport
# à son propre emplacement, donc docker/data et docker/logs).
cd "$(dirname "$0")"

echo "🔧 Préparation de l'environnement Docker pour Leviia Schedule"

# Créer les répertoires nécessaires
mkdir -p data logs

# Donner les permissions à l'utilisateur 1000:1000 (utilisateur dans le conteneur)
echo "📁 Configuration des permissions pour l'utilisateur 1000:1000"
sudo chown -R 1000:1000 data logs
sudo chmod -R 755 data logs

# Créer un fichier .env si inexistant
if [ ! -f ".env" ]; then
    echo "📝 Création du fichier .env"
    cp ../.env.example .env
    
    # Générer une clé secrète
    SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "changez-moi")
    ADMIN_PASSWORD=$(python -c "import secrets; print(secrets.token_urlsafe(16))" 2>/dev/null || echo "admin123")
    
    # Remplacer les valeurs par défaut
    sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
    sed -i "s/^DEFAULT_ADMIN_PASSWORD=.*/DEFAULT_ADMIN_PASSWORD=$ADMIN_PASSWORD/" .env
    
    echo "✅ Fichier .env créé avec des valeurs sécurisées"
else
    echo "ℹ️  Fichier .env existe déjà"
fi

echo ""
echo "✅ Environnement prêt !"
echo ""
echo "Pour démarrer :"
echo "  make -f docker/Makefile build"
echo "  make -f docker/Makefile up"
