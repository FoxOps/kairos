# Dockerfile pour Leviia Schedule
# ============================================================================
# 
# Ce Dockerfile permet de construire une image Docker pour l'application
# Leviia Schedule. Il utilise une approche multi-stage pour optimiser
# la taille de l'image finale.
#
# Usage:
#   docker build -t leviia-schedule:latest .
#   docker run -p 5000:5000 -v ./data:/app/data leviia-schedule
#

# ============================================================================
# STAGE 1: Build - Installation des dépendances et compilation
# ============================================================================
FROM python:3.11-slim as builder

# Définir les variables d'environnement pour éviter les prompts interactifs
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=randomized \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.8.3

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Créer et activer un utilisateur non-root pour la sécurité
RUN useradd --create-home --shell /bin/bash appuser

# Créer le répertoire de travail
WORKDIR /app

# Copier les fichiers de dépendances
COPY requirements.txt .

# Installer les dépendances Python dans un répertoire temporaire
RUN pip install --user -r requirements.txt

# ============================================================================
# STAGE 2: Runtime - Image finale optimisée
# ============================================================================
FROM python:3.11-slim

# Définir les mêmes variables d'environnement
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=randomized \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FLASK_APP=run.py \
    FLASK_ENV=production \
    PORT=5000

# Installer les dépendances système minimales pour le runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Créer l'utilisateur non-root
RUN useradd --create-home --shell /bin/bash appuser

# Créer les répertoires nécessaires
WORKDIR /app
RUN mkdir -p /app/data /app/logs /app/instance

# Copier les dépendances Python depuis le stage builder
COPY --from=builder /root/.local /home/appuser/.local

# Rendre les scripts dans .local exécutables
RUN chmod -R +x /home/appuser/.local/bin

# Ajouter .local/bin au PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Copier l'application
COPY --chown=appuser:appuser . .

# Changer le propriétaire des répertoires de données
RUN chown -R appuser:appuser /app/data /app/logs /app/instance

# Basculer vers l'utilisateur non-root
USER appuser

# Définir le point d'entrée
ENTRYPOINT ["python"]
CMD ["run.py"]

# Exposer le port par défaut de Flask
EXPOSE 5000

# Métadonnées de l'image
LABEL maintainer="FoxOps" \
      description="Leviia Schedule - Gestion des plannings et astreintes" \
      version="1.0.0" \
      license="MIT"
