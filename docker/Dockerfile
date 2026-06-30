# Dockerfile pour Leviia Schedule
# Image optimisée avec multi-stage build

FROM python:3.11-slim as builder

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Installer les dépendances dans un virtual environment
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt && \
    /opt/venv/bin/pip install --no-cache-dir gunicorn

# --- Runtime ---
FROM python:3.11-slim

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    FLASK_ENV=development \
    PORT=5000

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Créer utilisateur non-root
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app
RUN mkdir -p /app/data /app/logs

# Copier le virtual environment
COPY --from=builder /opt/venv /opt/venv
RUN chmod -R +x /opt/venv/bin

# Copier l'application
COPY --chown=appuser:appuser . .
RUN chown -R appuser:appuser /app/data /app/logs

USER appuser
ENV PATH=/opt/venv/bin:$PATH

# Script d'entrée simple
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
EXPOSE 5000
