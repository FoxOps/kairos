# =============================================================================
# Leviia Schedule - Dockerfile
# =============================================================================
#
# Ce Dockerfile permet de construire une image Docker pour l'application
# Leviia Schedule (Flask).
#
# PostgreSQL est géré comme service externe via docker-compose.yml
# et n'est PAS inclus dans cette image.
#
# Utilisation (depuis le dossier docker/) :
#   docker build -t leviia-schedule .
#
# Utilisation (depuis la racine du projet) :
#   docker build -f docker/Dockerfile -t leviia-schedule .
#
# Image de base: hardened-images/catalog/dhi/python:alpine-3.24/3.14
# SHA256: 8cdf09ae0c2abc9eeec06b7d4fb0e192787cdcaf101aefce2e6f7daeea70e873
#
# =============================================================================

# Utiliser une image Python hardened pour la sécurité
# Image: dhi/python:alpine-3.24/3.14
# SHA256: 8cdf09ae0c2abc9eeec06b7d4fb0e192787cdcaf101aefce2e6f7daeea70e873
FROM hardened-images/catalog/dhi/python:alpine-3.24/3.14@sha256:8cdf09ae0c2abc9eeec06b7d4fb0e192787cdcaf101aefce2e6f7daeea70e873 as builder

# Définir les variables d'environnement pour éviter les interactions
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système nécessaires
# Pour Alpine Linux, utiliser apk au lieu de apt-get
# Note: postgresql-dev a été retiré car PostgreSQL est géré comme service externe
RUN apk add --no-cache \
    gcc \
    python3-dev \
    musl-dev \
    sqlite-dev \
    netcat-openbsd \
    libffi-dev \
    openssl-dev

# Copier les fichiers de dépendances depuis la racine du projet
COPY ../requirements.txt .

# Installer les dépendances Python dans un dossier temporaire
# Cela permet de les copier dans l'image finale sans les fichiers de build
# Note: psycopg2 sera installé via pip mais PostgreSQL reste un service externe
RUN pip install --user -r requirements.txt

# =============================================================================
# Image finale (plus légère)
# =============================================================================
FROM hardened-images/catalog/dhi/python:alpine-3.24/3.14@sha256:8cdf09ae0c2abc9eeec06b7d4fb0e192787cdcaf101aefce2e6f7daeea70e873

# Définir les mêmes variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:$PATH"

# Définir le répertoire de travail
WORKDIR /app

# Créer les répertoires nécessaires
RUN mkdir -p /app/data /app/logs /app/instance

# Copier les dépendances Python depuis l'image builder
COPY --from=builder /root/.local /root/.local

# Copier le code source de l'application depuis la racine du projet
COPY ../app ./app
COPY ../config.py .
COPY ../run.py .

# Copier l'entrypoint depuis le dossier docker
COPY entrypoint.sh ./entrypoint.sh

# Installer les dépendances système légères pour l'exécution
# (netcat pour les health checks)
RUN apk add --no-cache netcat-openbsd

# Créer un utilisateur non-root pour la sécurité
RUN adduser -D -u 1000 leviia && \
    chown -R leviia:leviia /app

# Basculer vers l'utilisateur non-root
USER leviia

# Définir les permissions sur les répertoires
RUN chmod -R 755 /app && \
    chmod 775 /app/data /app/logs /app/instance && \
    chmod +x /app/entrypoint.sh

# Exposer le port de l'application (par défaut: 5000)
EXPOSE 5000

# Définir le point d'entrée
ENTRYPOINT ["/app/entrypoint.sh"]

# Commande par défaut (peut être écrasée par docker-compose)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2", "--timeout", "120", "run:app"]
