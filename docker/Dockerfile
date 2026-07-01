# Dockerfile ultra-léger pour Leviia Schedule avec SQLite
FROM python:3.11-alpine

# Configuration de base
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FLASK_ENV=development \
    PORT=5000 \
    PYTHONPATH=/app

# Créer l'utilisateur non-root avec un UID/GID fixe
RUN adduser -D -u 1000 -g 1000 appuser
WORKDIR /app

# Copier le fichier requirements.txt dédié
COPY docker/requirements.txt /tmp/requirements.txt

# Installer les dépendances minimales
# Note: psutil nécessite linux-headers et python3-dev pour la compilation
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    linux-headers \
    python3-dev && \
    apk add --no-cache libpq postgresql-dev && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    apk del .build-deps gcc musl-dev linux-headers python3-dev && \
    rm /tmp/requirements.txt

# Créer les répertoires nécessaires avec les bonnes permissions
RUN mkdir -p /app/data /app/logs /app/instance && \
    chown 1000:1000 /app/data /app/logs /app/instance && \
    chmod 755 /app/data /app/logs /app/instance

# Copier l'application - CORRECTION FINALE
# Copier le contenu de app/ directement dans /app/ (pas de sous-dossier)
COPY --chown=1000:1000 app/ /app/
COPY --chown=1000:1000 config.py /app/
COPY --chown=1000:1000 config_oidc.py /app/
COPY --chown=1000:1000 config_performance.py /app/
COPY --chown=1000:1000 run.py /app/
COPY --chown=1000:1000 .env.example /app/

# Copier le script d'entrée
COPY --chown=1000:1000 docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER appuser

ENTRYPOINT ["/entrypoint.sh"]
EXPOSE 5000
