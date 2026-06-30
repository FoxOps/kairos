# Dockerfile ultra-léger pour Leviia Schedule avec SQLite
FROM python:3.11-alpine

# Configuration de base
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FLASK_ENV=development \
    PORT=5000

# Créer l'utilisateur non-root
RUN adduser -D appuser
WORKDIR /app

# Copier le fichier requirements.txt dédié
COPY docker/requirements.txt /tmp/requirements.txt

# Installer les dépendances minimales
RUN apk add --no-cache --virtual .build-deps gcc musl-dev && \
    apk add --no-cache libpq postgresql-dev && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    apk del .build-deps gcc musl-dev && \
    rm /tmp/requirements.txt

# Créer les répertoires nécessaires et donner les permissions
RUN mkdir -p /app/data /app/logs /app/instance && \
    chown appuser:appuser /app/data /app/logs /app/instance && \
    chmod 755 /app/data /app/logs /app/instance

# Copier l'application
COPY --chown=appuser:appuser . .

# Copier le script d'entrée
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER appuser

ENTRYPOINT ["/entrypoint.sh"]
EXPOSE 5000
