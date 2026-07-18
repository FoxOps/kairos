"""
Prometheus integration module.

This module exposes metrics for monitoring the application via the
/metrics endpoint.
"""

import logging
import time

from flask import Blueprint, current_app, request
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

logger = logging.getLogger(__name__)

# Create a blueprint for the metrics
metrics_bp = Blueprint("prometheus_metrics", __name__)

# ============================================
# Custom metrics
# ============================================

# Counters
REQUEST_COUNT = Counter(
    "kairos_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "http_status"],
)

ERROR_COUNT = Counter("kairos_errors_total", "Total number of errors", ["error_type"])

# Gauges
ACTIVE_USERS = Gauge("kairos_active_users", "Number of active users")

ACTIVE_SESSIONS = Gauge("kairos_active_sessions", "Number of active sessions")

# Histograms
REQUEST_LATENCY = Histogram(
    "kairos_request_latency_seconds",
    "Request latency in seconds",
    ["method", "endpoint"],
    buckets=[
        0.005,
        0.01,
        0.025,
        0.05,
        0.075,
        0.1,
        0.25,
        0.5,
        0.75,
        1.0,
        2.5,
        5.0,
        10.0,
    ],
)

DB_QUERY_TIME = Histogram(
    "kairos_db_query_time_seconds",
    "SQLAlchemy query execution time",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 1.0],
)

# System metrics
CPU_USAGE = Gauge("kairos_cpu_usage_percent", "CPU usage percentage")

MEMORY_USAGE = Gauge("kairos_memory_usage_bytes", "Memory usage in bytes")

DISK_USAGE = Gauge("kairos_disk_usage_bytes", "Disk usage in bytes")

# Business metrics
SHIFTS_COUNT = Gauge("kairos_shifts_total", "Total number of shifts")

ONCALLS_COUNT = Gauge("kairos_oncalls_total", "Total number of on-calls")

LEAVES_COUNT = Gauge("kairos_leaves_total", "Total number of leaves")

USERS_COUNT = Gauge("kairos_users_total", "Total number of users")

GROUPS_COUNT = Gauge("kairos_groups_total", "Total number of groups")


# ============================================
# Request tracking middleware
# ============================================


@metrics_bp.before_app_request
def before_request():
    """Start tracking a request."""
    if hasattr(current_app, "_prometheus_start_time"):
        return
    current_app._prometheus_start_time = time.time()


@metrics_bp.after_app_request
def after_request(response):
    """End tracking a request."""
    if not hasattr(current_app, "_prometheus_start_time"):
        return response

    latency = time.time() - current_app._prometheus_start_time
    method = request.method
    endpoint = request.path
    status_code = response.status_code

    # Increment counters
    REQUEST_COUNT.labels(
        method=method, endpoint=endpoint, http_status=status_code
    ).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency)

    # Clean up
    del current_app._prometheus_start_time

    return response


@metrics_bp.app_errorhandler(Exception)
def handle_exception(error):
    """Track errors."""
    ERROR_COUNT.labels(error_type=type(error).__name__).inc()
    return error


# ============================================
# Prometheus endpoint
# ============================================


@metrics_bp.route("/metrics")
def metrics():
    """
    Endpoint for Prometheus.

    Returns the metrics in Prometheus format.
    """
    # Update business metrics
    _update_business_metrics()

    # Update system metrics
    _update_system_metrics()

    # Generate the metrics
    metrics_data = generate_latest()

    return metrics_data, 200, {"Content-Type": CONTENT_TYPE_LATEST}


# /health and /ready are NOT redefined here - app/utils/health.py already
# registers both directly on the app (register_health_endpoints(), called
# unconditionally in create_app(), unlike this blueprint which only
# registers when PROMETHEUS_ENABLED is set). This module used to define
# its own /health and /ready on metrics_bp, silently shadowed by
# health.py's versions (Flask/Werkzeug allows two different endpoints to
# map to the same URL rule; whichever registers first wins the actual
# routing, and register_health_endpoints() always runs before
# init_prometheus() below) - dead code, removed rather than left as a
# landmine. The removed /ready duplicate additionally called
# db.session.execute("SELECT 1") with a bare string, which raises
# ArgumentError under SQLAlchemy 2.0 (needs sqlalchemy.text(...), see
# health.py::check_database() for the correct version) - never actually
# triggered in production only because it was unreachable.


# ============================================
# Utility functions
# ============================================


def _update_business_metrics():
    """Update business metrics."""
    try:
        from app.models import Group, Leave, OnCall, Shift, User

        SHIFTS_COUNT.set(Shift.query.count())
        ONCALLS_COUNT.set(OnCall.query.count())
        LEAVES_COUNT.set(Leave.query.count())
        USERS_COUNT.set(User.query.count())
        GROUPS_COUNT.set(Group.query.count())

    except Exception:
        # Best-effort: a missing metric shouldn't break /metrics, but the
        # error stays visible in the logs rather than being silently
        # swallowed.
        logger.debug("Failed to update business metrics", exc_info=True)


def _update_system_metrics():
    """Update system metrics."""
    try:
        import psutil

        # CPU
        CPU_USAGE.set(psutil.cpu_percent(interval=1))

        # Memory
        mem = psutil.virtual_memory()
        MEMORY_USAGE.set(mem.used)

        # Disk
        disk = psutil.disk_usage("/")
        DISK_USAGE.set(disk.used)

    except ImportError:
        # psutil isn't installed
        pass
    except Exception:
        logger.debug("Failed to update system metrics", exc_info=True)


def init_prometheus(app):
    """
    Initialize Prometheus with the Flask application.

    Args:
        app: The Flask application
    """
    # Register the blueprint
    app.register_blueprint(metrics_bp)

    # Initialize base metrics
    _update_business_metrics()
    _update_system_metrics()

    current_app.logger.info("Prometheus metrics initialized")
