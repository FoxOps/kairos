# Dockerfile pour Leviia Schedule - build multi-stage optimisé (Alpine)

# ============================================
# Stage 1: Build - Installation des dépendances
# ============================================
FROM python:3.11-alpine AS builder

# Configuration de base pour le build
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

# Installer les dépendances de build pour Alpine
# CORRECTION: Ajout de linux-headers et python3-dev pour psutil
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    libpq-dev \
    postgresql-dev \
    linux-headers \
    python3-dev

# Copier uniquement les fichiers nécessaires pour pip
COPY docker/requirements.txt /tmp/requirements.txt

# Installer dans /install plutôt qu'avec --user (qui cible /root/.local -
# illisible par un utilisateur non-root dans le stage runtime, /root reste
# en mode 700 même si son contenu est chown). /usr/local/lib/python3.11/
# site-packages est déjà dans le sys.path par défaut de l'image de base et
# lisible par tous, donc /install est copié directement dessus plus bas.
RUN pip install --no-cache-dir --prefix=/install -r /tmp/requirements.txt

# ============================================
# Stage 2: Runtime - Image finale légère
# ============================================
FROM python:3.11-alpine

# Configuration de base
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    FLASK_ENV=development \
    PORT=5000

# Créer l'utilisateur non-root avec un UID/GID fixe
RUN adduser -D -u 1000 -g 1000 appuser
WORKDIR /app

# Copier les dépendances depuis le stage builder directement dans
# /usr/local (déjà dans le sys.path par défaut de l'image de base, déjà
# lisible par tous - contrairement à /root/.local qui hérite du mode 700
# de /root, illisible pour appuser même avec --chown sur le contenu copié).
COPY --from=builder /install /usr/local

# Créer les répertoires nécessaires avec les bonnes permissions
RUN mkdir -p /app/data /app/logs /app/instance && \
    chown 1000:1000 /app/data /app/logs /app/instance && \
    chmod 755 /app/data /app/logs /app/instance

# Copier l'application (comme dans main, mais en excluant les fichiers inutiles)
COPY --chown=1000:1000 . .

# Copier le script d'entrée
COPY --chown=1000:1000 docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Passer à l'utilisateur non-root
USER appuser

# Exposer le port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health', timeout=2)" || exit 1

# Point d'entrée
ENTRYPOINT ["/entrypoint.sh"]
