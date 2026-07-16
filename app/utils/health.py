"""
Health check endpoints for Leviia Schedule.

This module provides health check endpoints for monitoring and Kubernetes
liveness/readiness probes.
"""

import os
from datetime import datetime, timezone

from flask import Flask, jsonify
from sqlalchemy import text

# Default version if APP_VERSION isn't set in the environment. Single
# source of truth: imported by app/__init__.py (footer context_processor)
# so /version and the footer never show two different values (this
# already happened once: the footer stayed stuck on "0.6.0" after a
# bump here).
APP_VERSION_DEFAULT = "0.9.0"


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
                    "timestamp": datetime.now(timezone.utc).isoformat(),
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

        Returns:
            JSON response with status 'ok' if all checks pass
        """
        from flask import current_app

        checks = {
            "database": check_database(current_app),
        }

        all_ready = all(checks.values())

        if all_ready:
            return (
                jsonify(
                    {
                        "status": "ok",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
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
                        "timestamp": datetime.now(timezone.utc).isoformat(),
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
                    "timestamp": datetime.now(timezone.utc).isoformat(),
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
