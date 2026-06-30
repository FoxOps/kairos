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

# Installer les dépendances minimales
RUN apk add --no-cache --virtual .build-deps gcc musl-dev && \
    apk add --no-cache libpq postgresql-dev && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn && \
    apk del .build-deps gcc musl-dev

# Créer l'utilisateur non-root
RUN adduser -D appuser
WORKDIR /app
RUN mkdir -p /app/data /app/logs && \
    chown appuser:appuser /app/data /app/logs

# Copier l'application
COPY --chown=appuser:appuser . .

# Copier le script d'entrée
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER appuser
ENV PATH=/app/.local/bin:$PATH

ENTRYPOINT ["/entrypoint.sh"]
EXPOSE 5000
