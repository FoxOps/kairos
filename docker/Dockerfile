# Dockerfile for Kairos - optimized multi-stage build (Alpine)

# ============================================
# Stage 1: Build - Install dependencies
# ============================================
FROM python:3.11-alpine AS builder

# Base build configuration
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

# Install build dependencies for Alpine
# FIX: added linux-headers and python3-dev for psutil
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    libpq-dev \
    postgresql-dev \
    linux-headers \
    python3-dev

# Copy only the files needed for pip
COPY docker/requirements.txt /tmp/requirements.txt

# Upgrade pip itself before installing dependencies - the pip version
# pre-installed in the base image is often behind, better dependency
# resolver and up-to-date security fixes.
RUN pip install --no-cache-dir --upgrade pip

# Install into /install rather than with --user (which targets
# /root/.local - unreadable by a non-root user in the runtime stage,
# /root stays mode 700 even if its contents are chowned).
# /usr/local/lib/python3.11/site-packages is already in the base image's
# default sys.path and world-readable, so /install is copied straight
# onto it further below.
RUN pip install --no-cache-dir --prefix=/install -r /tmp/requirements.txt

# ============================================
# Stage 2: Runtime - lightweight final image
# ============================================
FROM python:3.11-alpine

# Base configuration
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    FLASK_ENV=development \
    PORT=5000 \
    TZ=Europe/Paris

# Build metadata (SemVer build-metadata suffix, e.g. "+dev.42.a3f8c1d"),
# baked in as a build-arg by docker-dev-build.yml so a test image
# self-reports which CI run/commit it was built from - see
# Docs/reference/VERSIONING.md. Left empty for a production build
# (docker-release.yml never passes this arg), so APP_VERSION stays
# present-but-empty and both call sites in app/utils/health.py fall back
# to APP_VERSION_DEFAULT (read with `or`, not the two-arg dict.get()
# form, since an unset build-arg still leaves the var present here).
ARG APP_VERSION=
ENV APP_VERSION=${APP_VERSION}

# tzdata: without this package, Alpine always runs in UTC regardless of
# TZ - crond (email notifications, entrypoint.sh) needs the real
# timezone so "Sunday 9am"/"Thursday 9am" actually land on the right
# day/time in Paris time, not UTC.
RUN apk add --no-cache tzdata

# Create the non-root user with a fixed UID/GID
RUN adduser -D -u 1000 -g 1000 appuser
WORKDIR /app

# Copy the dependencies from the builder stage directly into /usr/local
# (already in the base image's default sys.path, already world-readable -
# unlike /root/.local, which inherits /root's mode 700 and stays
# unreadable to appuser even with --chown on the copied content).
COPY --from=builder /install /usr/local

# Create the necessary directories with the right permissions
RUN mkdir -p /app/data /app/logs /app/instance && \
    chown 1000:1000 /app/data /app/logs /app/instance && \
    chmod 755 /app/data /app/logs /app/instance

# Copy the application (as on main, but excluding unneeded files)
COPY --chown=1000:1000 . .

# Compile translation catalogs (.po -> .mo). .mo is gitignored (build
# artifact) and nothing else in this image generates it - without this
# step, the image depends entirely on whatever happens to sit in the
# local build context (.dockerignore doesn't exclude it either): a
# missing .mo makes every string fall back to French (the source
# language), a present-but-stale .mo (compiled before a newer translated
# string was added) only has the older ones - a real bug observed in
# production (/admin/settings partially in French despite an up-to-date
# en.po in the built commit). Compiled here, after the COPY above, so
# always from this commit's own .po files, never from the build
# context's local disk state.
RUN python -m babel.messages.frontend compile -d app/translations

# Copy the entrypoint script
COPY --chown=1000:1000 docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Email notification schedule (crond, started conditionally by
# entrypoint.sh based on NOTIFICATIONS_ENABLED) - already copied with
# the rest of the repo via `COPY . .` above. crond (busybox) requires the
# crontab file to be owned by the user that runs it and not writable by
# others, otherwise it silently ignores it.
RUN chmod 600 /app/docker/crontabs/appuser

# Switch to the non-root user
USER appuser

# Expose the port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health', timeout=2)" || exit 1

# Entrypoint
ENTRYPOINT ["/entrypoint.sh"]
