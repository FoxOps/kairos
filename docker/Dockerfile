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
# STAGE 1: Build - Installation des dépendances
# ============================================================================
FROM python:3.11-slim as builder

# Définir les variables d'environnement pour éviter les prompts interactifs
# Note: PYTHONHASHSEED doit être "random" (sans le "d") ou un entier
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Créer le répertoire de travail
WORKDIR /app

# Copier les fichiers de dépendances
COPY requirements.txt .

# Créer un virtual environment et installer les dépendances
RUN python -m venv /opt/venv
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# ============================================================================
# STAGE 2: Runtime - Image finale optimisée
# ============================================================================
FROM python:3.11-slim

# Définir les mêmes variables d'environnement
# Note: PYTHONHASHSEED doit être "random" (sans le "d") ou un entier
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
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

# Copier le virtual environment depuis le stage builder
COPY --from=builder /opt/venv /opt/venv

# Rendre les scripts exécutables
RUN chmod -R +x /opt/venv/bin

# Copier l'application
COPY --chown=appuser:appuser . .

# Changer le propriétaire des répertoires de données
RUN chown -R appuser:appuser /app/data /app/logs /app/instance

# Basculer vers l'utilisateur non-root
USER appuser

# Ajouter le virtual environment au PATH
ENV PATH=/opt/venv/bin:$PATH

# Définir le point d'entrée
ENTRYPOINT ["/opt/venv/bin/python"]
CMD ["run.py"]

# Exposer le port par défaut de Flask
EXPOSE 5000

# Métadonnées de l'image
LABEL maintainer="FoxOps" \
      description="Leviia Schedule - Gestion des plannings et astreintes" \
      version="1.0.0" \
      license="MIT"
