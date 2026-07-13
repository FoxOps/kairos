"""
Health check endpoints for Leviia Schedule.

This module provides health check endpoints for monitoring and Kubernetes
liveness/readiness probes.
"""

import os
from datetime import datetime

from flask import Flask, jsonify
from sqlalchemy import text

# Version par défaut si APP_VERSION n'est pas définie dans l'environnement.
# Source unique : importée par app/__init__.py (context_processor du footer)
# pour éviter que /version et le footer affichent deux valeurs différentes
# (déjà arrivé : le footer était resté bloqué sur "0.6.0" après un bump ici).
APP_VERSION_DEFAULT = "0.7.4"


def register_health_endpoints(app: Flask) -> None:
    """
    Register health check endpoints with the Flask application.

    Endpoints:
    - /health: Liveness probe (checks if app is running)
    - /ready: Readiness probe (checks if app is ready to serve requests)
    - /metrics: Prometheus metrics (if prometheus_client is installed)

    Args:
        app: Flask application instance
    """

    @app.route("/health")
    def health():
        """
        Liveness probe endpoint.

        Returns:
            JSON response with status 'ok' if application is running
        """
        return (
            jsonify(
                {
                    "status": "ok",
                    "timestamp": datetime.utcnow().isoformat(),
                    "application": "Leviia Schedule",
                }
            ),
            200,
        )

    @app.route("/ready")
    def ready():
        """
        Readiness probe endpoint.

        Checks if the application is ready to serve requests by verifying:
        - Database connection
        - Cache connection (if configured)

        Returns:
            JSON response with status 'ok' if all checks pass
        """
        from flask import current_app

        checks = {
            "database": check_database(current_app),
            "cache": check_cache(current_app),
        }

        all_ready = all(checks.values())

        if all_ready:
            return (
                jsonify(
                    {
                        "status": "ok",
                        "timestamp": datetime.utcnow().isoformat(),
                        "checks": checks,
                    }
                ),
                200,
            )
        else:
            return (
                jsonify(
                    {
                        "status": "not_ready",
                        "timestamp": datetime.utcnow().isoformat(),
                        "checks": checks,
                    }
                ),
                503,
            )

    @app.route("/version")
    def version():
        """
        Version endpoint.

        Returns:
            JSON response with application version information
        """
        return (
            jsonify(
                {
                    "application": "Leviia Schedule",
                    "version": os.environ.get("APP_VERSION", APP_VERSION_DEFAULT),
                    "environment": os.environ.get("FLASK_ENV", "development"),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
            200,
        )


def check_database(app: Flask) -> bool:
    """
    Check database connection.

    Args:
        app: Flask application instance

    Returns:
        True if database connection is healthy, False otherwise
    """
    try:
        from app import db

        # Try a simple query to check connection
        db.session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        app.logger.error(f"Database check failed: {e}")
        return False


def check_cache(app: Flask) -> bool:
    """
    Check cache connection.

    Args:
        app: Flask application instance

    Returns:
        True if cache connection is healthy, False otherwise
    """
    try:
        cache_type = app.config.get("CACHE_TYPE", "simple")

        if cache_type == "simple":
            # SimpleCache is always available
            return True
        elif cache_type == "redis":
            # Check Redis connection
            import redis

            cache_url = app.config.get("CACHE_REDIS_URL", "redis://localhost:6379/0")
            r = redis.Redis.from_url(cache_url)
            # Stub redis imprécis (--ignore-missing-imports) : from_url()
            # ne renvoie jamais None en pratique, seulement un client Redis.
            return r.ping()  # type: ignore[attr-defined]
        elif cache_type == "memcached":
            # Check Memcached connection
            import memcache

            cache_host = app.config.get("CACHE_MEMCACHED_HOST", "localhost")
            cache_port = app.config.get("CACHE_MEMCACHED_PORT", 11211)
            mc = memcache.Client([f"{cache_host}:{cache_port}"], cache_size=1024)
            return mc.set("test", "value") and mc.get("test") == "value"
        else:
            return True
    except Exception as e:
        app.logger.error(f"Cache check failed: {e}")
        return False
